# Evaluación III Django Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Aplicar al SGR la evaluación TI3041 aprobada en `docs/EVALUACION_3_PROPUESTA.md`.

**Architecture:** Django MVT, apps `cuentas` y `gestion`, MySQL, Channels con Redis y ASGI. Consultas y permisos siempre en servidor; templates heredados municipales y actualizaciones parciales de tablas.

**Tech Stack:** Python 3.11+, Django 5.2 LTS, mysqlclient, Channels, Daphne, Redis, Pillow, openpyxl, Bootstrap, SweetAlert2 y Croppr.

## Global Constraints

- Ámbitos A=Centro DEL01 y B=Las Compañías DEL02; administrador A no superusuario.
- Dos CRUD evaluados: ItemMeta y Atencion. Ambos usan deleted_at; created_at no cambia al editar.
- Páginas 5, 15 y 30; orden inicial -created_at,-id; sesión independiente por módulo.
- JPEG/PNG hasta 2 MiB, contenido comprobado; perfil propio y recorte final con Croppr.
- 2.286 registros de negocio idempotentes: 6 delegaciones, 360 metas, 30 tipos, 90 subatenciones y 1.800 atenciones.
- Seis cuentas: Administrador A, Editor A, Lector A, Lector B, Cliente 1 y Cliente 2; contraseñas privadas.
- Estado visible en español de Chile, logo y colores municipales existentes; foco y navegación por teclado.
- Sin credenciales de producción en código, sin cambios en SQLite existente, sin despliegues destructivos ni gastos nuevos.
- Trabajo en feature/SGR-evaluacion3-django. No merge/push directo a main ni autorías o revisiones inventadas.

## Contratos compartidos

`User` será `django.contrib.auth.models.User`; `user.perfil` será `cuentas.models.Perfil` con campos `delegacion` (FK gestion.Delegacion), `rut`, `foto` (ImageField). Grupos exactos: `Administrador`, `Editor`, `Lector`, `Cliente`.

`gestion.models` expondrá Delegacion, TipoAtencion, SubAtencion, ItemMeta, Atencion, Secuencia. Campos de negocio en español; `created_at`, `updated_at`, `deleted_at` en inglés. Todas las entidades salvo Delegacion tienen FK `delegacion`. Atencion tiene `tipo`, `subatencion`, `cliente` (User opcional) y `responsable` (User); catálogo usa `nombre`, `codigo`, `descripcion`, `estado` (Activo/Inactivo); Atencion usa estado Ingresada/En proceso/Resuelta. ItemMeta añade `unidad_medida` y `meta_cantidad` automático 100. Delegacion tiene `direccion`, `comuna`, `estado` y `codigo`.

Rutas `gestion`: `inicio`, `listado` (modulo), `tabla` (modulo), `crear` (modulo), `editar` (modulo, pk), `detalle` (modulo, pk), `archivar` (modulo, pk), `exportar` (modulo), `portal`, `portal_detalle` (pk), `subatenciones`. Módulos: `metas`, `atenciones`, `tipos`, `subatenciones`, `delegaciones`. Gestión de usuarios/roles en `cuentas`.

Rutas `cuentas`: `login`, `logout`, `perfil`, `foto` (pk), `password_change`, `password_change_done`, `password_reset`, `password_reset_done`, `password_reset_confirm` (uidb64, token), `password_reset_complete`, `usuarios`, `usuario_crear`, `usuario_editar` (pk), `roles`.

Templates base: bloques `title`, `content`, `extra_css`, `extra_js`. Contexto global `is_cliente`, `role_label`. CRUD contexto: `modulo`, `titulo`, `page_obj`, `state` (q, estado, orden, tamano, pagina), `columns` (label/key), `rows` (obj, cells), `can_add`, `can_change`, `can_delete`, `filter_choices`, `order_choices`, `page_sizes`, `pagination` (number/url/current), `export_url`. Formularios: `form`, `obj`, `modulo`, `titulo`, `return_url`. Detalle: `obj`, `details` (label/value), `return_url`, permisos. Fragmento tabla `gestion/_tabla.html` incluye resultados y paginación.

## Task 1: Entorno y dominio

Owner: agente principal. Files: `manage.py`, `config/`, `gestion/models.py`, `gestion/apps.py`, `requirements*.txt`, `compose.yaml`, `.env.example`, `.gitignore`, `pytest.ini`, `tests_django/`.

- [x] Crear configuración que exige secretos y MySQL por entorno, Redis, CSRF, middleware y ASGI. No fallback SQLite.
- [x] Iniciar MySQL/Redis locales mediante Docker, sin publicar puertos a interfaces externas.
- [x] Escribir primero pruebas que rechacen relaciones de distintas delegaciones, cantidades inválidas y códigos duplicados.
- [x] Implementar modelos, constraints y secuencias bloqueadas por transacción. Ejecutar migraciones y pruebas.

Validación: `.venv/bin/python manage.py check`; `.venv/bin/pytest tests_django/test_domain.py`.

## Task 2: Cuentas y perfil

Owner: un subagente, archivos `cuentas/`, `templates/cuentas/`, `static/sgr/perfil.js`, `static/vendor/croppr*`, `tests_django/test_accounts.py`. No editar modelos de gestión ni configuración global.

- [x] Pruebas primero de login/logout, edición propia sin escalación, perfil ajeno, imagen inválida/grande, clave actual y reset de token.
- [x] Implementar Perfil y formularios con lista explícita de campos. Grupos/permisos Django. Datos de usuario por ámbito.
- [x] Login, logout POST, reset por correo con respuesta genérica y validadores Django.
- [x] Croppr, canvas, preview, multipart, imagen final validada con Pillow y vista de foto protegida.
- [x] Usuarios de prueba administrables solo dentro del ámbito y roles predefinidos; roles globales solo técnico.

Validación: `.venv/bin/pytest tests_django/test_accounts.py` y prueba de navegador del recorte.

## Task 3: CRUD y consultas autorizadas

Owner: principal. Files: `gestion/forms.py`, `gestion/access.py`, `gestion/queries.py`, `gestion/views.py`, `gestion/urls.py`, `tests_django/test_crud.py`.

- [x] Probar lector no escribe, editor no archiva, IDs ajenos 404, FK ajena inválida y cliente sin acceso administrativo.
- [x] Implementar ModelForms, dos CRUD completos con deleted_at y catálogos existentes; códigos automáticos y RUT.
- [x] Consultas con búsqueda, filtros, orden permitido, paginación y sesión por módulo. Pruebas con más de 30 filas, estado entre rutas y página inválida.
- [x] Excel con conjunto filtrado completo, ámbito, exclusión de archivados y cadenas tratadas como texto.
- [x] Portal y detalle filtrados por propietario; dos clientes de la misma delegación.

Validación: `.venv/bin/pytest tests_django/test_crud.py`.

## Task 4: Templates y navegación

Owner: siguiente subagente, `templates/base.html`, `templates/gestion/`, `templates/errors/`, `static/sgr/app.css`, `static/sgr/app.js`, `static/vendor/bootstrap*`, `static/vendor/sweetalert*`.

- [x] Base municipal heredada, menú por rol, perfil y logout POST; enlaces visibles para todos los recorridos.
- [x] Listados, detalles, formularios con modal Bootstrap abierto también con errores, labels visibles y errores asociados.
- [x] Confirmar archivado con SweetAlert2; cancelar sin POST. Guardado válido regresa al listado conservado.
- [x] Páginas 400/403/404/500 con salida segura y mensajes sin detalles técnicos.
- [x] Verificar teclado, 375/768/1280, recursos locales y ausencia de enlaces rotos.

Validación: suite HTTP, guard de copy firma y recorrido en navegador.

## Task 5: Channels y eventos

Owner: principal. Files: `gestion/consumers.py`, `gestion/realtime.py`, `gestion/routing.py`, `config/asgi.py`, `tests_django/test_realtime.py`; integración `static/sgr/app.js` después de Task 4.

- [x] Pruebas de conexión anónima/origen indebido, A vs B y clientes excluidos; canales reales con Redis cuando esté disponible.
- [x] Guardado/archivado notifica exclusivamente después del commit; rollback o formulario inválido no notifica.
- [x] La tabla se consulta solo al evento WebSocket, con filtros y paginación conservados; estado de desconexión visible.

Validación: `.venv/bin/pytest tests_django/test_realtime.py` y dos sesiones de navegador.

## Task 6: Datos, operación y entrega

Owner: principal o siguiente subagente con ownership delimitado. Files: `gestion/management/commands/seed_demo.py`, `deploy/`, `Dockerfile`, `README.md`, `diagramas/modelos_django.mmd`, `tests_django/test_seed.py`, `.github/workflows/`.

- [x] Semillas idempotentes 2.286 y seis cuentas, fechas variadas; contraseñas solo archivo privado ignorado con modo 600.
- [x] Diagrama desde modelos finales. README con instalación, matriz de cuentas, pruebas, límites y estado real de AWS.
- [x] ASGI sin root, Nginx WebSocket, estáticos, imágenes privadas, correo configurado y secretos externos.
- [x] Retirar credenciales incrustadas y contraseñas publicadas de los archivos activos, conservar pruebas históricas sin exponer nuevos secretos.
- [x] Prueba integral MySQL, Redis, correo de pruebas, HTTP/WS y errores DEBUG=False. Revisar cambios y corregir hallazgos.
- [x] Preparar commits de rama y PR si existe acceso; nunca fingir revisión humana ni despliegue AWS si no hay acceso.

Validación: `.venv/bin/pytest tests_django`; `node --test tests/test_*.cjs`; `python3 -m unittest discover -s tests -p 'test_*.py'`; `manage.py check --deploy`; `makemigrations --check --dry-run`; `collectstatic --noinput`.

## Encargo y registro de ejecución

TASK: implementar la propuesta aprobada y comprobar todos los criterios ejecutables.
RESOURCES: este plan, propuesta, repo actual y PDF original; verificador principal pytest/MySQL/Redis.
AUTONOMY: cambios locales reversibles y Docker local autorizados; máximo tres rondas de corrección por revisión de tarea antes de informar un impedimento concreto. No contratar AWS ni modificar recursos remotos sin identificar el recurso existente.
GOAL: tests de aislamiento, CRUD, perfiles, imágenes, sesiones, exportación y WebSocket pasan; evidencia de navegador y estado AWS documentados.
GUARDRAILS: un subagente implementador activo a la vez, archivos separados del principal; ninguna eliminación de datos existentes, secretos o revisiones ficticias.
OUTPUT: implementación en la rama feature, README operativo y registro `docs/EVALUACION_3_ESTADO.md` con verificaciones y pendientes externos medidos.

Comprobación de alcance: requisitos fijados por PDF y propuesta, sin meta estética indefinida. Coste limitado por tareas y rondas de corrección; AWS depende de acceso real. Los verificadores se instalarán y ejecutarán antes de declarar éxito.

## Pendientes externos tras la implementación local

- [ ] Desplegar y demostrar HTTP, WebSocket y correo en una instancia AWS identificada y accesible.
- [ ] Integrar mediante PR con revisión real de un compañero y registrar aportes reales de cada integrante.

Verificaciones y límites: `docs/EVALUACION_3_ESTADO.md`. La rama feature conserva main sin cambios.
