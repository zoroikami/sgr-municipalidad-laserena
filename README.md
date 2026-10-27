# SGR · Municipalidad de La Serena

Sistema académico de gestión de resultados. Backend migrado a **Django 5.2 LTS**, modelos y migraciones Django, SQLite, sesiones, administración y API JSON. La interfaz existente conserva HTML, CSS y JavaScript, SweetAlert2 y exportación con SheetJS.

## Ejecución local (macOS / Linux)

Requiere Python 3.10 o superior. En este equipo el proyecto está en el Escritorio.

### Iniciar el proyecto ya instalado

```bash
cd ~/Desktop/sgr-municipalidad-laserena
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Mantener esa terminal abierta mientras se usa la aplicación. Para detenerla, presionar **Ctrl+C**. Si el puerto 8000 está ocupado, usar `python manage.py runserver 127.0.0.1:8001` y abrir el puerto 8001 en el navegador.

- Aplicación: [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
- Administración: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).
- Estado de la API: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

### Instalar por primera vez en otro equipo

Abrir la terminal en la raíz del repositorio, donde están `manage.py` y `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Crear el `.env` privado desde la plantilla y generar una clave propia. Este bloque conserva el archivo si ya existe:

```bash
python - <<'PYENV'
import os
import secrets
from pathlib import Path

path = Path('.env')
if path.exists():
    print('Se conserva el .env existente.')
else:
    template = Path('.env.example').read_text()
    content = template.replace('DJANGO_SECRET_KEY=\n',
                               'DJANGO_SECRET_KEY=' + secrets.token_urlsafe(64) + '\n')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(content)
    print('.env privado creado.')
PYENV
```

El `.env` contiene la configuración privada y queda excluido de Git junto con sus variantes. La plantilla `.env.example` se puede publicar y no contiene secretos. No sobrescribir un `.env` configurado con la plantilla.

Crear las tablas, la primera cuenta y ejecutar Django:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

`createsuperuser` solicita usuario, correo y contraseña en la terminal. La contraseña no se muestra mientras se escribe. Este paso se realiza una sola vez por cuenta; el superusuario puede entrar tanto a la aplicación como a `/admin/`.

En el equipo actual el entorno virtual, el `.env` y las tablas ya están preparados. Si todavía no creaste una cuenta, detener el servidor con **Ctrl+C**, ejecutar `python manage.py createsuperuser` y volver a iniciarlo.

**La base nueva `db.sqlite3` comienza vacía.** No se importan usuarios, contraseñas, registros ni semillas anteriores. La base antigua `database/sgr_laserena.db` se conserva separada y Django no la abre. Los datos antiguos del almacenamiento del navegador tampoco se recuperan.

Ejecutar la aplicación con Django: abrir `index.html` directamente o usar un servidor de archivos estáticos no proporciona autenticación ni acceso a la API.

## Primera configuración

1. Crear un superusuario con el comando anterior.
2. Entrar a `/admin/` y crear una delegación con código `DEL01` y dirección.
3. Crear los roles necesarios: `ROL01` administrador, `ROL02` coordinador, `ROL03` delegado, `ROL04` operador, `ROL05` consultor. Usar `total` como permisos solamente para administradores.
4. Asignar delegación al superusuario y crear usuarios con nombre, RUT, correo, rol y delegación.
5. Crear tipos, subatenciones y metas desde la aplicación o administración.

No se generan cuentas automáticamente. La interfaz conserva la clave inicial `LaSerena2026*` para los usuarios nuevos; deben cambiarla mediante recuperación. Para elegir una contraseña al crear una cuenta, usar la administración Django.

## API e implementación

- `GET /api/health`: estado público y cookie CSRF.
- `POST /api/auth/login`: acceso por `usuario` (correo, nombre, username o RUT) y `password`.
- `GET /api/profile`: sesión actual. `DELETE /api/profile`: salir.
- `PUT /api/profile`: guardar o quitar la foto del usuario autenticado, con sesión y CSRF de Django. La foto se conserva en el modelo `Usuario`; `migrate` agrega el campo también en instalaciones existentes.
- `POST /api/auth/recuperar-codigo`, `validar-codigo`, `cambiar-password`: recuperación en tres pasos, código de diez minutos y tres intentos. La validación concede permiso de cambio únicamente a esa sesión.
- `/api/delegaciones`, `/roles`, `/usuarios`, `/items-metas`, `/tipos-atencion`, `/sub-atenciones`: GET, POST, PUT y DELETE (estas últimas con `/{id}`). Todas bajo prefijo `/api`.
- `/api/atenciones`: listado y registro; `/api/stats`: conteos.

Las operaciones requieren sesión de Django y las escrituras incluyen `X-CSRFToken`. Las claves se guardan con hash de Django. Los permisos se validan también en el servidor; usuarios territoriales consultan usuarios y atenciones de su delegación. La API conserva códigos y nombres de relaciones para la interfaz, mientras los modelos usan claves foráneas protegidas.

Estructura: `sgr/` configuración, rutas y WSGI/ASGI; `gestion/` modelos, vistas, administración, migraciones y pruebas; `evaluacion2/` interfaz; `assets/` recursos públicos. `server.py` permite los antiguos comandos `--init-db` y `--port` usando Django. Los informes y prototipos históricos quedan como documentación de las entregas anteriores.

## Correo

En desarrollo, el código se imprime en la terminal del servidor. Para correo real configurar `.env`:

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=cuenta@dominio.cl
SMTP_PASS=contraseña-de-aplicación
SMTP_FROM=cuenta@dominio.cl
```

## Verificación

```bash
python manage.py test gestion
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
node --test tests/test_django_profile_data.cjs tests/test_rut.cjs tests/test_profile_ui.cjs tests/test_photo_cropper.cjs
```

Los antiguos tests HTTP de `tests/` documentan el servidor reemplazado. La suite Django vigente está en `gestion/` y corre aislada de las bases locales; las pruebas JavaScript del comando anterior cubren perfil, recorte, RUT y la conexión del perfil con Django.

## Producción

Configurar `DJANGO_DEBUG=false`, clave secreta aleatoria, hosts y orígenes CSRF HTTPS en `.env`. Ejecutar migraciones y `collectstatic`, servir `sgr.wsgi:application` con Gunicorn detrás de un proxy HTTPS. El script `deploy_ec2.sh` prepara la copia actual y arranca Gunicorn como usuario actual; no clona ramas antiguas ni instala un servicio root. Para mantenerlo en ejecución configurar un supervisor como systemd.

La configuración de proxy, certificado y `SECURE_PROXY_SSL_HEADER` debe corresponder al proxy real. No habilitar confianza en cabeceras de clientes sin un proxy que las reemplace. No se ha desplegado en AWS durante esta migración.
