# SGR · Municipalidad de La Serena

Sistema de Gestión de Resultados para registrar atenciones ciudadanas y consultar metas por delegación municipal. El personal trabaja sobre su delegación; cada cliente consulta exclusivamente sus atenciones, incluso cuando comparte delegación con otro cliente.

Implementación de la Evaluación Sumativa III de Programación Back End, TI3041, INACAP La Serena. El código anterior de Proyecto Integrado se conserva como antecedente; el servidor vigente es **Django**, no `server.py`.

## Ejecutar en este equipo

Con el entorno ya preparado:

```bash
source .venv/bin/activate
docker compose up -d mysql redis mailpit
daphne -b 127.0.0.1 -p 8001 config.asgi:application
```

Aplicación: [http://127.0.0.1:8001](http://127.0.0.1:8001). Buzón SMTP local: [http://127.0.0.1:8025](http://127.0.0.1:8025).

Las seis credenciales de prueba se guardan exclusivamente en `.private/cuentas-demo.json`, con permisos `600` y fuera de Git. Entregarlas al docente por un medio privado. No existen accesos automáticos ni botones para cambiar de cuenta.

**Estado de AWS:** todavía no se ha identificado una instancia ni una dirección pública para esta migración. No se acredita despliegue AWS con las pruebas locales. Se requiere registrar aquí la URL verificada, recurso EC2 y commit de `main` desplegado después de la integración y la revisión real.

## Instalación desde cero

Requisitos: Python 3.11+, `uv`, Docker con Compose y las bibliotecas de compilación de mysqlclient. Versiones Python fijadas en [requirements.txt](requirements.txt); dependencias de pruebas en [requirements-dev.txt](requirements-dev.txt).

En Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3-dev build-essential default-libmysqlclient-dev pkg-config
```

En macOS:

```bash
brew install mysql-client pkgconf
export PKG_CONFIG_PATH="$(brew --prefix mysql-client)/lib/pkgconfig"
```

Preparación local:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements-dev.txt
python scripts/configure_local.py
docker compose up -d mysql redis mailpit
python manage.py migrate
python manage.py seed_demo
python manage.py check
daphne -b 127.0.0.1 -p 8001 config.asgi:application
```

Si MySQL todavía está inicializándose, esperar a que `docker compose ps` indique `healthy` antes de migrar. `scripts/configure_local.py` genera secretos aleatorios y no sobrescribe un `.env` existente. Para un entorno distinto, usar [.env.example](.env.example) como referencia y configurar sus valores privados.

El entorno local utiliza MySQL 8.4 en `127.0.0.1:3307`, Redis 7.4 en `127.0.0.1:6380` y Mailpit en los puertos locales 1025/8025. Los volúmenes conservan MySQL al detener contenedores. No ejecutar `docker compose down -v` sobre datos que se quieran conservar. No hay fallback a SQLite.

`DEBUG=true` solo se utiliza para desarrollo local y permite servir los estáticos con ASGI. Producción usa `DEBUG=false`, Nginx y `collectstatic`. Las fotos no tienen URL pública bajo MEDIA: se entregan mediante una vista autenticada que comprueba su propietario.

## Arquitectura y módulos

- `config/`: settings por entorno, rutas, ASGI, consola técnica y errores HTTP.
- `cuentas/`: autenticación Django, perfil, foto privada, cambio/recuperación de contraseña, grupos y administración acotada de cuentas.
- `gestion/`: modelos de negocio, ModelForms, consultas autorizadas, CRUD, exportaciones, portal, Channels y semillas.
- `templates/`: herencia de `base.html`, formularios en modal Bootstrap, tablas y errores 400/403/404/500.
- `static/`: Bootstrap 5.3.3, SweetAlert2 11.14.5, Croppr 2.3.1 y código municipal, todos locales y con licencias.
- `tests_django/`: integración sobre MySQL y Redis reales; `tests_browser/`: recorridos de Chromium.
- `deploy/`: Nginx HTTPS/WebSocket y Compose de producción; `Dockerfile` ejecuta Daphne como usuario `sgr`, sin root.

Los dos CRUD evaluados son **Ítems y Metas** y **Atenciones ciudadanas**. Incluyen crear, listar, detalle, editar, archivar con `deleted_at`, búsqueda por varios campos, filtro de negocio, orden permitido, páginas 5/15/30 y exportación `.xlsx` de todos los resultados filtrados.

También están disponibles los catálogos de tipos/subatenciones, la consulta y edición de la delegación propia y la gestión acotada de usuarios. El administrador A crea o edita cuentas únicamente en A y asigna los cuatro roles predefinidos; puede desactivarlas. La creación de delegaciones y el mantenimiento global de roles pertenecen al soporte técnico, mediante `/admin/` o su pantalla de permisos. Ninguna cuenta de revisión tiene acceso a Django Admin. Para crear un superusuario técnico adicional, utilizar `python manage.py createsuperuser`; no reemplaza al administrador A.

La [preevaluación III](https://github.com/zoroikami/sgr-municipalidad-laserena/tree/c61d311bd513c9ea59334ff29c172342649c5cd3) se conserva en Git con su configuración y migraciones SQLite. Para instalar esta entrega, ejecuta las migraciones de `config.settings` sobre una base MySQL nueva y conserva un respaldo independiente si tienes datos de la preevaluación. El prototipo anterior y sus pruebas históricas se mantienen juntos.

El modelo implementado está documentado en [diagramas/modelos_django.md](diagramas/modelos_django.md), con [fuente Mermaid](diagramas/modelos_django.mmd). Los diagramas MySQL anteriores corresponden a la primera entrega, no a estas migraciones.

### Reglas aplicadas en servidor

- Consultas, detalle, edición, archivado, relaciones, exportación y fragmentos de tabla limitados por delegación.
- Clientes filtrados además por `cliente=request.user`; no acceden a funciones administrativas ni a fotos ajenas.
- Permisos de Django por acción. Editor sin eliminación/archivado; lector sin escrituras. Cuenta sin permiso recibe 403; objeto ajeno o inexistente recibe 404.
- ModelForms con campos explícitos: el navegador no decide delegación, responsable, código, folio, privilegios ni cantidad de meta.
- Nombres duplicados por delegación rechazados; cantidades no negativas; nuevas metas con cantidad automática 100; las existentes conservan su cantidad.
- Tipo y subatención activos de la misma delegación y relación tipo/subatención coherente; cliente vinculado de la misma delegación con rol Cliente.
- RUT normalizado y validado por módulo 11. ORM y CSRF, escape de templates y ordenamiento mediante lista explícita.
- JPEG/PNG hasta 2 MiB completamente decodificados con Pillow. Croppr genera el recorte real antes del guardado multipart; cancelar conserva la foto anterior.

Al editar se conserva `created_at`; el orden inicial es creación descendente e id descendente. Búsqueda, filtros, orden, tamaño y página se conservan **en sesión, por módulo**. Una consulta nueva vuelve a página 1; una página que ya no existe se ajusta a una válida. El Excel reutiliza la consulta autorizada completa, excluye archivados y credenciales y trata el contenido del usuario como texto, no como fórmulas.

## Datos de revisión

Carga reproducible e idempotente:

```bash
python manage.py seed_demo
```

| Modelo de negocio | Registros | Distribución |
| --- | ---: | --- |
| Delegacion | 6 | Delegaciones municipales |
| ItemMeta | 360 | 60 por delegación |
| TipoAtencion | 30 | 5 por delegación |
| SubAtencion | 90 | 15 por delegación |
| Atencion | 1.800 | 300 por delegación |
| **Total** | **2.286** | Ambos CRUD tienen más de 50 registros y más de una página de 30 en A y B |

Los clientes 1 y 2 tienen 30 atenciones distintas cada uno dentro de las 300 de Centro. Las semillas incluyen nombres ficticios, fechas de creación variadas, distintos estados, unidades y servicios. No se cuentan usuarios, perfiles, grupos, permisos, sesiones ni secuencias en los 2.286 registros.

Se crean seis cuentas activas de revisión y cuatro responsables ficticios inactivos, sin contraseña utilizable, para las otras delegaciones. Ejecutar de nuevo no duplica registros, no reinicia contraseñas y no sobrescribe ediciones o fotos existentes. Los códigos de las semillas llevan `DEMO` para no colisionar con los códigos automáticos de operaciones nuevas.

### Cuentas, responsabilidades y recorridos

A = Centro (`DEL01`); B = Las Compañías (`DEL02`). Todos los correos iniciales son ficticios `@example.test` y llegan al buzón local Mailpit. Para una revisión con correo externo, configurar el correo de la cuenta mediante su perfil o proporcionar `DEMO_EMAIL_ADMIN_A` antes de la primera carga. La contraseña nunca se publica en esta tabla.

| Alias | Rol / ámbito | Responsabilidad y acciones permitidas | Restricciones | Recorrido y resultado esperado |
| --- | --- | --- | --- | --- |
| `admin_a` | Administrador A | Gestionar atenciones, metas, catálogos y cuentas de A; consultar/exportar, crear/editar/archivar | Sin B, permisos globales, privilegios técnicos ni Django Admin | Login → ambos CRUD → crear/editar → cancelar SweetAlert sin cambios → confirmar archivado → registro excluido de listado/Excel |
| `editor_a` | Editor A | Registrar y actualizar atención y metas de Centro | Sin archivado/eliminación, usuarios ni B | Login → editar atención → guardar → lector A cambia sin F5 → intentar POST de archivado y recibir 403 |
| `lector_a` | Lector A | Consultar detalle y exportar datos de A | Sin escrituras ni B | Login → buscar/filtrar/ordenar/paginar → abrir detalle → regresar conserva estado → intento de creación devuelve 403 |
| `lector_b` | Lector B | Consultar y exportar datos de Las Compañías | Sin escrituras ni A | Abrir listado en otro perfil → editor A guarda → no recibe evento ni datos de A; URL ajena devuelve 404 |
| `cliente_1` | Cliente / propietario 1 en A | Consultar sus 30 atenciones, detalle y perfil/foto propios | Sin administración, datos ni foto del Cliente 2 | Login → Mis atenciones → detalle propio → Croppr/guardar/recargar → persiste recorte → detalle del Cliente 2 devuelve 404 |
| `cliente_2` | Cliente / propietario 2 en A | Consultar otras 30 atenciones, detalle y perfil/foto propios | Sin administración, datos ni foto del Cliente 1 | Login en sesión independiente → datos distintos → detalle del Cliente 1 devuelve 404 → perfil solo modifica su cuenta |

## WebSocket aplicado al CRUD

Ruta: `/ws/atenciones/`. Servidor: `daphne config.asgi:application`. Capa: `channels_redis.core.RedisChannelLayer`.

Recorrido del evento:

1. Editor guarda un ModelForm válido dentro de una transacción.
2. `transaction.on_commit` notifica al grupo calculado por el servidor desde su delegación.
3. El lector autenticado del mismo ámbito recibe una notificación mínima, sin registros ni datos personales.
4. El navegador solicita `/gestion/atenciones/tabla/`, una vista HTTP protegida que reaplica ámbito, filtros, orden y página.
5. Se reemplaza únicamente la tabla/paginación; no hay F5, recarga de la página ni polling.

Las conexiones anónimas, de clientes y de orígenes no permitidos se rechazan. B no se une al grupo de A. Antes de enviar cada evento se revisan nuevamente permisos, delegación y vigencia de la sesión; logout o cambio de contraseña invalidan la recepción. La interfaz informa desconexión o fallo de actualización y conserva los datos visibles sin afirmar que están actualizados.

Redis permite varios procesos ASGI; no se utiliza una capa en memoria que limite la demostración a un solo proceso.

## Recuperación y contraseña

Login por usuario o correo, logout exclusivamente POST con CSRF, vistas privadas protegidas, contraseña actual para cambiarla y validadores Django (mínimo 10 caracteres, similitud, claves comunes y solo numéricas).

La recuperación usa enlace y token Django de una hora. Solicitarlo muestra la misma respuesta para correos registrados y desconocidos. El correo contiene una URL del host que sirve la aplicación; en AWS deben configurarse los hosts/orígenes públicos y el SMTP real o buzón de pruebas accesible. Un enlace usado o inválido no permite otro cambio. No basta con imprimir enlaces en consola.

Localmente Mailpit recibe correo SMTP real del proceso Django y permite abrirlo en su buzón web. En producción, configurar `EMAIL_HOST`, `EMAIL_PORT`, usuario/contraseña privados, TLS y remitente. La credencial SMTP incrustada de la versión anterior se retiró del código activo; como permanece en el historial, debe reemplazarse en el proveedor antes de reutilizar esa cuenta de correo.

## Verificación

Primero conceder a la cuenta local permiso sobre **su base aislada de pruebas**:

```bash
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "GRANT ALL PRIVILEGES ON test_sgr_django.* TO '\''sgr'\''@'\''%'\'';"'
pytest tests_django
python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=false python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.cjs
```

Los tests Django usan MySQL real y Redis. No ejecutar varias suites pytest simultáneamente contra la misma base de pruebas. La configuración rápida de hashes se limita a `config/test_settings.py`; la aplicación usa los hashes seguros de Django.

Con ASGI y Mailpit funcionando, las semillas cargadas y las credenciales privadas disponibles:

```bash
playwright install chromium
python tests_browser/check_crop.py
python tests_browser/check_flows.py
```

El segundo recorrido usa seis sesiones independientes, comprueba cambios WebSocket solo en A, filtros, cancelación de SweetAlert, errores dentro del modal, navegación, portal, foto, correo SMTP, token de un uso y cambio/logout. Modifica y restaura un nombre ficticio, guarda una foto de prueba en Cliente 1 y restaura su contraseña privada. Ejecutarlo sobre datos de demostración. Las capturas locales se escriben en `output/browser/`, excluido de Git.

Las pruebas controladas de 400/500 viven exclusivamente en `tests_django/error_urls.py` con `DEBUG=False`; no hay rutas de producción para forzar fallos. Ver [docs/evaluacion3/EVALUACION_3_ESTADO.md](docs/evaluacion3/EVALUACION_3_ESTADO.md) para resultados y límites verificados.

## AWS: preparación y puesta en marcha

La configuración preparada utiliza EC2, MySQL persistente en volumen, Redis, Daphne sin root y Nginx con HTTPS y Upgrade WebSocket. No crea recursos AWS ni contrata servicios.

Después de identificar la instancia, integrar el PR revisado a `main` y disponer de Docker/Compose:

1. Clonar o actualizar el repositorio en la instancia con el commit de `main` elegido.
2. Preparar `.env` privado a partir de `.env.example`, con secretos nuevos, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` público, `CSRF_TRUSTED_ORIGINS=https://dominio`, cookies seguras y SMTP externo. No usar las credenciales de desarrollo.
3. Colocar certificados válidos en `deploy/tls/fullchain.pem` y `deploy/tls/privkey.pem`, fuera de Git. Restringir la clave privada y permitir acceso de solo lectura al proceso Nginx.
4. Permitir HTTP/HTTPS en el recurso AWS; MySQL, Redis y Mailpit no deben exponerse públicamente. El script no detiene automáticamente un servicio anterior que ocupe 80/443.
5. Ejecutar desde el checkout limpio de `main`:

```bash
./deploy_ec2.sh https://dominio-publico-de-la-instancia
```

El script comprueba configuración de producción, respalda MySQL en `.private/backups/`, migra, carga semillas idempotentes, recopila estáticos e inicia servicios. Escribe credenciales nuevas únicamente en el archivo privado del host; las inyecta en un volumen temporal, no en la imagen. `APP_COMMIT` se establece desde Git y aparece en `/api/health/`.

6. Comprobar desde otro equipo la URL, certificados, archivos, fotos privadas, correo, 2.286 semillas, seis cuentas y WebSocket con A/B. Registrar URL pública y recurso en este README. Mostrar `git rev-parse HEAD` y `/api/health/` durante la revisión.

`deploy/compose.production.yaml` complementa `compose.yaml`; sus rutas se resuelven desde la raíz:

```bash
docker compose -f compose.yaml -f deploy/compose.production.yaml ps
```

La base SQLite anterior no se modifica ni se importa automáticamente: el nuevo esquema tiene ámbitos y validaciones distintos. `python scripts/backup_legacy.py` crea una copia privada coherente para una migración de datos revisada. No ejecutar el script SQL destructivo de la primera entrega sobre esta base.

## Git y entrega académica

Desarrollo en `feature/SGR-evaluacion3-django`; integrar mediante Pull Request revisado por otro integrante, sin commits ni push directos a `main`. La CI declarada en `.github/workflows/django.yml` ejecuta las pruebas con MySQL/Redis y conserva las pruebas históricas. La revisión de un agente no sustituye la revisión de un compañero requerida por la pauta.

Cada integrante debe aportar al menos un PR funcional con su autoría y revisión reales. Este trabajo no crea aportes ni revisiones ficticias y no reescribe el historial previo.

La entrega en la plataforma consiste en el enlace del repositorio y los nombres completos de todos los integrantes. No se exige un informe adicional. Los antecedentes de primera/segunda entrega permanecen en `diagramas/`, `especificaciones/`, `gestion_agil/`, `mockup/` y los documentos históricos; no representan el estado operativo actual de Django.
