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

**AWS verificado el 10 de noviembre de 2026:** [abrir SGR](https://sgr-184-195-57-121.sslip.io). Instancia existente `i-0a5533ede6cc60b7e`, región `us-east-1`, IP `184.195.57.121`. Commit de la aplicación desplegada: `8f189c8807c1d0051ab7dc6eb1c0a751c5d4369a` (merge del [PR #13](https://github.com/zoroikami/sgr-municipalidad-laserena/pull/13)); se comprueba en [/api/health/](https://sgr-184-195-57-121.sslip.io/api/health/).

HTTPS utiliza un certificado público de Let's Encrypt y renovación diaria mediante `sgr-tls-renew.timer`. Se verificaron las siete cuentas, permisos, WSS entre delegaciones, Croppr y recuperación con token de un uso. MySQL 8.4.13, Redis, fotos y estáticos se ejecutan en contenedores con volúmenes persistentes y `DEBUG=False`. **Gmail SMTP está configurado en AWS** con STARTTLS por el puerto 587: autenticación y checks de producción aprobados; Gmail aceptó un mensaje de prueba al destinatario autorizado. La recepción en la bandeja del destinatario debe confirmarse allí. Las credenciales se conservan únicamente en la configuración privada del host. No se exponen MySQL, Redis ni Mailpit a Internet. La dirección usa la Elastic IP `184.195.57.121` (`eipalloc-08967e7da51b66e2c`), asociada a esta instancia. Se conserva al detener e iniciar mientras no se libere la dirección ni el laboratorio elimine el recurso. La reserva de IPv4 pública tiene cargo de AWS. El enlace dinámico anterior dejó de utilizarse.

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

Preparación local (Bash; en PowerShell activa con `.venv\Scripts\Activate.ps1`):

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements-dev.txt
python scripts/configure_local.py
docker compose up -d mysql redis mailpit
python manage.py migrate
python manage.py seed_demo
python manage.py check
python manage.py verify_environment --demo
daphne -b 127.0.0.1 -p 8001 config.asgi:application
```

Si MySQL todavía está inicializándose, esperar a que `docker compose ps` indique `healthy` antes de migrar. `scripts/configure_local.py` genera secretos aleatorios y no sobrescribe un `.env` existente. Para un entorno distinto, usar [.env.example](.env.example) como referencia y configurar sus valores privados.

El entorno local utiliza MySQL 8.4 en `127.0.0.1:3307`, Redis 7.4 en `127.0.0.1:6380` y Mailpit en los puertos locales 1025/8025. Los volúmenes conservan MySQL al detener contenedores. No ejecutar `docker compose down -v` sobre datos que se quieran conservar. MySQL es el motor predeterminado. SQLite solo se habilita explícitamente con `USE_SQLITE=true` y `DJANGO_DEBUG=true` para una revisión rápida; producción lo rechaza.

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

Los roles municipales originales están restaurados: **Superadministrador, Coordinador, Delegado Municipal, Operador / Funcionario y Consultor**. Se conserva **Cliente** para el portal ciudadano. La migración `cuentas.0004` transforma Administrador → Delegado Municipal, Editor → Operador / Funcionario y Lector → Consultor, conservando cuentas y contraseñas.

Superadministrador y Coordinador pueden elegir una delegación activa o Todas las delegaciones desde la cabecera. La selección se conserva por sesión y se aplica a inicio, consultas, formularios, catálogos, Excel y actualizaciones en tiempo real. Las cuentas locales conservan su delegación asignada. El cambio de ámbito limpia filtros de listados anteriores; no cambia el perfil ni los permisos de la cuenta.

| Rol | Funciones y ámbito |
| --- | --- |
| Superadministrador | Todos los módulos, cuentas, roles y consola técnica. Puede asignar roles comunales y privilegios técnicos. |
| Coordinador | Delegaciones, metas, catálogos y atenciones en ámbito comunal. Sin gestión de cuentas, roles ni Django Admin. |
| Delegado Municipal | Metas, atenciones y cuentas de su delegación. Solo asigna roles locales. |
| Operador / Funcionario | Registro y edición de atenciones de su delegación, sin archivado. |
| Consultor | Consulta y exportación de módulos municipales de su delegación. |
| Cliente | Solo lectura de sus propias atenciones. En Roles únicamente se ofrece Consultar atenciones; no admite permisos de escritura ni consulta de otros módulos. |

Ninguna cuenta municipal de revisión tiene acceso a Django Admin. Para crear un superusuario técnico adicional, utilizar `python manage.py createsuperuser`. El nombre del grupo Superadministrador por sí solo no concede privilegios técnicos.

Para habilitar el acceso global del sistema municipal, crea la cuenta técnica después de aplicar las migraciones con `python manage.py createsuperuser --username superadmin`. Introduce una contraseña privada cuando Django la solicite. El superadministrador ve todas las delegaciones, elige la delegación al crear un registro y conserva la delegación original al editar. Su ámbito global se aplica a los listados, Excel y la actualización en tiempo real. Las cuentas municipales de prueba conservan sus restricciones.

La [preevaluación III](https://github.com/zoroikami/sgr-municipalidad-laserena/tree/c61d311bd513c9ea59334ff29c172342649c5cd3) se conserva en Git con su configuración y migraciones SQLite. Para instalar esta entrega, ejecuta las migraciones de `config.settings` sobre una base MySQL nueva y conserva un respaldo independiente si tienes datos de la preevaluación. Las pruebas históricas del servidor retirado se conservan en `tests/legacy/`; sus dependencias están en revisiones anteriores de Git.

El modelo implementado está documentado en [diagramas/modelos_django.md](diagramas/modelos_django.md), con [fuente Mermaid](diagramas/modelos_django.mmd). Los diagramas MySQL anteriores corresponden a la primera entrega, no a estas migraciones.

### Reglas aplicadas en servidor

- Consultas, detalle, edición, archivado, relaciones, exportación y fragmentos de tabla limitados por delegación.
- Clientes filtrados además por `cliente=request.user`; no acceden a funciones administrativas ni a fotos ajenas.
- Permisos de Django por acción. Operador sin eliminación/archivado ni mantenimiento de metas o catálogos; Consultor sin escrituras. Cuenta sin permiso recibe 403; objeto ajeno o inexistente recibe 404.
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

Se crean seis cuentas activas de revisión y cuatro responsables ficticios inactivos, sin contraseña utilizable, para las otras delegaciones. Ejecutar de nuevo no duplica registros, no reinicia contraseñas y no sobrescribe ediciones o fotos existentes. Los códigos usan los formatos originales `DEL01`, `IT001`, `TA001`, `SA001` y `ATN-2026-0001`, con correlativos globales por sección y anuales en atenciones. La migración conserva el identificador previo como referencia interna y clave estable de semillas; incluye archivados al asignar números y mantiene los IDs y relaciones existentes.

### Cuentas, responsabilidades y recorridos

A = Centro (`DEL01`); B = Las Compañías (`DEL02`). Todos los correos iniciales son ficticios `@example.test` y llegan al buzón local Mailpit. Para una revisión con correo externo, configurar el correo de la cuenta mediante su perfil o proporcionar `DEMO_EMAIL_ADMIN_A` antes de la primera carga. La contraseña nunca se publica en esta tabla.

| Alias | Rol / ámbito | Responsabilidad y acciones permitidas | Restricciones | Recorrido y resultado esperado |
| --- | --- | --- | --- | --- |
| `admin_a` | Delegado Municipal A | Gestionar atenciones, metas y cuentas de A; consultar/exportar, crear/editar/archivar | Sin B, mantenimiento de catálogos, permisos globales, privilegios técnicos ni Django Admin | Login → ambos CRUD → crear/editar → cancelar SweetAlert sin cambios → confirmar archivado → registro excluido de listado/Excel |
| `editor_a` | Operador / Funcionario A | Registrar y actualizar atenciones de Centro | Sin metas, catálogos, archivado/eliminación, usuarios ni B | Login → editar atención → guardar → consultor A cambia sin F5 → intentar POST de archivado y recibir 403 |
| `lector_a` | Consultor A | Consultar detalle y exportar datos de A | Sin escrituras ni B | Login → buscar/filtrar/ordenar/paginar → abrir detalle → regresar conserva estado → intento de creación devuelve 403 |
| `lector_b` | Consultor B | Consultar y exportar datos de Las Compañías | Sin escrituras ni A | Abrir listado en otro perfil → operador A guarda → no recibe evento ni datos de A; URL ajena devuelve 404 |
| `cliente_1` | Cliente / propietario 1 en A | Consultar sus 30 atenciones, detalle y perfil/foto propios | Sin administración, datos ni foto del Cliente 2 | Login → Mis atenciones → detalle propio → Croppr/guardar/recargar → persiste recorte → detalle del Cliente 2 devuelve 404 |
| `cliente_2` | Cliente / propietario 2 en A | Consultar otras 30 atenciones, detalle y perfil/foto propios | Sin administración, datos ni foto del Cliente 1 | Login en sesión independiente → datos distintos → detalle del Cliente 1 devuelve 404 → perfil solo modifica su cuenta |

## WebSocket aplicado al CRUD

Ruta: `/ws/atenciones/`. Servidor: `daphne config.asgi:application`. Capa: `channels_redis.core.RedisChannelLayer`.

Recorrido del evento:

1. Editor guarda un ModelForm válido dentro de una transacción.
2. `transaction.on_commit` notifica al grupo calculado por el servidor desde su delegación y al grupo de soporte global. Las cuentas limitadas nunca se unen al grupo global.
3. El lector autenticado del mismo ámbito recibe una notificación mínima, sin registros ni datos personales.
4. El navegador solicita `/gestion/atenciones/tabla/`, una vista HTTP protegida que reaplica ámbito, filtros, orden y página.
5. Se reemplaza únicamente la tabla/paginación; no hay F5, recarga de la página ni polling.

Las conexiones anónimas, de clientes y de orígenes no permitidos se rechazan. B no se une al grupo de A. Antes de enviar cada evento se revisan nuevamente permisos, delegación y vigencia de la sesión; logout o cambio de contraseña invalidan la recepción. La interfaz informa desconexión o fallo de actualización y conserva los datos visibles sin afirmar que están actualizados.

Redis permite varios procesos ASGI; no se utiliza una capa en memoria que limite la demostración a un solo proceso.

## Recuperación y contraseña

Login por usuario o correo, logout exclusivamente POST con CSRF, vistas privadas protegidas, contraseña actual para cambiarla y validadores Django (mínimo 10 caracteres, similitud, claves comunes y solo numéricas).

La recuperación usa enlace y token Django de una hora. Solicitarlo muestra la misma respuesta para correos registrados y desconocidos. El correo contiene una URL del host que sirve la aplicación; en AWS deben configurarse los hosts/orígenes públicos y el SMTP real o buzón de pruebas accesible. Un enlace usado o inválido no permite otro cambio. No basta con imprimir enlaces en consola.

Las cuentas sembradas conservan direcciones `@example.test`. Para recuperar una cuenta mediante correo real, registrar primero su dirección válida en el perfil o en la gestión de usuarios; configurar el remitente SMTP no reemplaza los correos de las cuentas.

Localmente Mailpit recibe correo SMTP real del proceso Django y permite abrirlo en su buzón web. En producción, configurar `EMAIL_HOST`, `EMAIL_PORT`, usuario/contraseña privados, TLS y remitente. La credencial SMTP incrustada de la versión anterior se retiró del código activo; como permanece en el historial, debe reemplazarse en el proveedor antes de reutilizar esa cuenta de correo.

## Verificación

Primero conceder a la cuenta local permiso sobre **su base aislada de pruebas**:

```bash
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "GRANT ALL PRIVILEGES ON test_sgr_django.* TO '\''sgr'\''@'\''%'\'';"'
pytest tests_django
python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=false COOKIE_SECURE=true SECURE_SSL_REDIRECT=true python manage.py check --deploy --fail-level WARNING
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
python tests_browser/check_design.py
python tests_browser/check_paneles.py
python tests_browser/check_usability.py
python tests_browser/check_delegation_roles.py
python tests_browser/check_client_readonly.py
```

`check_delegation_roles.py` requiere también `.private/superadmin.json`, generado por `python manage.py provision_superadmin`. Comprueba cambios de delegación, roles históricos, restricciones locales y alineación de la casilla Cuenta activa a cuatro anchos, sin guardar cambios de negocio.

`check_client_readonly.py` verifica que Roles solo ofrece Consultar para Cliente y que dos clientes de la misma delegación no pueden abrir las atenciones del otro. La migración `cuentas.0005` asigna únicamente `gestion.view_atencion` al grupo Cliente, sin cambiar cuentas ni contraseñas. Revocar ese permiso desde Roles impide consultar el portal.

El recorrido `check_flows.py` usa seis sesiones independientes, comprueba cambios WebSocket solo en A, filtros, cancelación de SweetAlert, errores dentro del modal, navegación, portal, foto, correo SMTP, token de un uso y cambio/logout. Modifica y restaura un nombre ficticio, guarda una foto de prueba en Cliente 1 y restaura su contraseña privada. Ejecutarlo sobre datos de demostración. Las capturas locales se escriben en `output/browser/`, excluido de Git.

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

La base SQLite anterior no se importa automáticamente. Conserva una copia independiente antes de cualquier migración de datos revisada. Los scripts del servidor antiguo ya no forman parte de la instalación actual.

## Git y entrega académica

Los [PR #12](https://github.com/zoroikami/sgr-municipalidad-laserena/pull/12) y [PR #13](https://github.com/zoroikami/sgr-municipalidad-laserena/pull/13) se integraron a `main` el 10 de noviembre de 2026. El propietario autorizó el despliegue; esto no sustituye la revisión académica de un compañero. Las pruebas actuales son `tests_django` y las pruebas compartidas de RUT; las del servidor retirado están en `tests/legacy/`.

GitHub Actions no pudo iniciar los últimos trabajos por un bloqueo de facturación de la cuenta. Los resultados locales no se presentan como resultados de CI. La revisión de un agente tampoco sustituye la revisión de un compañero.

Cada integrante debe aportar al menos un PR funcional con su autoría y revisión reales. Este trabajo no crea aportes ni revisiones ficticias y no reescribe el historial previo.

La entrega en la plataforma consiste en el enlace del repositorio y los nombres completos de todos los integrantes. No se exige un informe adicional. Los antecedentes de primera/segunda entrega disponibles se agrupan en `docs/antecedentes/` y en el historial de Git; no representan el estado operativo actual de Django.


### Superadministrador y cuentas de revisión

`python manage.py provision_superadmin` crea una cuenta adicional `superadmin` con contraseña aleatoria guardada únicamente en `.private/superadmin.json`. Accede a todas las delegaciones, CRUD, exportaciones, usuarios, roles, portal ciudadano y consola técnica. Repetir el comando conserva su contraseña y nunca eleva una cuenta municipal existente. El portal de un cliente sigue limitado a sus propias atenciones.

`python manage.py seed_demo --update-names` asigna los nombres solicitados a las cuentas de demostración existentes sin cambiar sus contraseñas ni permisos:

| Usuario | Nombre | Rol / ámbito |
| --- | --- | --- |
| admin_a | Keoni Vergara | Delegado Municipal / Centro |
| editor_a | Harold Concha | Operador / Funcionario / Centro |
| lector_a | Marcos Ortiz | Consultor / Centro |
| lector_b | Claudio Romo | Consultor / Las Compañías |
| cliente_1 | Javier Ahumada | Cliente / registros propios |
| cliente_2 | Jorge Cortes | Cliente / registros propios |

Las cuentas conservan sus alias para mantener los recorridos de evaluación reproducibles. Los nombres de estas cuentas no constituyen evidencia de autoría académica.

La renovación TLS usa `deploy/renew_tls.sh DOMINIO`, ejecutado por un temporizador del host. Nginx sirve exclusivamente el desafío ACME por HTTP y redirige las demás rutas a HTTPS. Los certificados y la cuenta ACME permanecen fuera de Git.

### Comprobación de dependencias

`python manage.py verify_environment --demo` comprueba MySQL, las zonas horarias de los filtros, envío/recepción en Redis y conexión SMTP real. Rechaza SQLite y capas de canales/correo en memoria o archivos. `--production` añade `DEBUG=False` y los checks de seguridad. No imprime secretos ni envía mensajes a terceros; el recorrido de navegador acredita el correo entregado al buzón de pruebas y el token.

Para usar servicios nativos, conserva la misma configuración y ajusta solo los puertos privados en `.env`. La validación del 10 de noviembre se ejecutó en Windows con MySQL 8.4.7, Redis 7.4.11 (port de redis-windows para MSYS2) y Mailpit 1.27.10. Los binarios se mantuvieron fuera del repositorio. La imagen de despliegue sigue utilizando Redis oficial para Linux.

Conserva las credenciales de revisión fuera del repositorio. En la revisión grupal utiliza las seis cuentas limitadas; el superusuario técnico adicional no sustituye al administrador A. Para preparar la defensa, recorre las diez comprobaciones de la pauta: AWS/commit, ambos CRUD, validaciones, consultas/Excel, permisos, aislamiento, WebSocket, correo/Croppr/clientes, Git y navegación/errores.
