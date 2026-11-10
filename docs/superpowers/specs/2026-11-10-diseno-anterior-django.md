# Diseño anterior sobre Django

El usuario confirmó el 10 de noviembre de 2026 recuperar el diseño de
`index.html` y `evaluacion2/`, manteniendo los requisitos de la Evaluación III.

## Decisión

Adaptar las plantillas Django al diseño existente. Reutilizar la identidad de
`assets/municipal/brand.css`: logo horizontal, rojo institucional, superficies
claras, tipografía del sistema, acciones semánticas y controles redondeados.
El login vuelve a una tarjeta centrada; el área privada recupera cabecera roja,
delegación activa, avatar, menú lateral agrupado, breadcrumbs y tablas en paneles.
En móvil el menú pasa a navegación horizontal dentro de su propia región.

Se descartan tanto volver a la aplicación JavaScript antigua (perdería los
contratos Django) como limitar el cambio al login (dejaría el resto incongruente).
No se incorporan los módulos demostrativos sin backend de la segunda entrega.

## Contratos que se conservan

- Django, MySQL, Channels/Redis, permisos por acción, delegación y propietario.
- Formularios POST con CSRF, validaciones del servidor, archivado transaccional.
- Ambos CRUD, búsqueda, filtros, orden y paginación conservados en sesión.
- Excel completo filtrado y WebSocket sin recarga con aislamiento A/B.
- Perfil y fotos privadas con Croppr, recuperación SMTP por enlace de un uso.
- Portal cliente, errores HTTP reales, navegación por teclado y adaptación móvil.
- Dependencias locales existentes; sin scripts del frontend histórico ni modo local.

La delegación de cabecera informa el ámbito asignado por el servidor. La apariencia
del antiguo selector no permite cambiar a ámbitos no autorizados. La recuperación
conserva enlace y token Django: no se restaura el simulador de códigos antiguo.
AWS, SMTP público y revisiones académicas continúan como pendientes externos.

## Archivos y verificación

Modificar `templates/base.html`, plantillas de cuentas y gestión, y añadir
`static/sgr/legacy.css`, `static/sgr/interface.js` y un partial SVG de iconos.
Conservar los identificadores utilizados por `app.js`, `perfil.js` y las pruebas.
No tocar los cambios previos pendientes en README ni en el informe de estado.

Verificar interacción de Mostrar/Ocultar contraseña, login por Enter, teclado,
ancho de página en 320/375/768/1280 px y capturas de login, listados y perfil.
Ejecutar `pytest tests_django`, pruebas históricas Python/Node, checks Django,
`tests_browser/check_flows.py` y `tests_browser/check_crop.py`.

## Resultado de la adaptación

- 53 pruebas Django aprobadas sobre MySQL/Redis; 22 históricas Python y 48 Node.
- `check_design.py`: Mostrar/Ocultar sin envío, login por Enter, navegación activa,
  acceso a Excel y capturas de login/listados en 320/375/768/1280 px y perfil.
- `check_flows.py`: seis sesiones, eventos solo en A, consultas conservadas,
  teclado de modal, cancelación de archivado, portal por propietario, foto privada,
  recorte persistido y recuperación SMTP con token de un uso aprobados.
- `check_crop.py`: límites de recorte con teclado y archivo final aprobados.
- Django sin migraciones pendientes ni advertencias de `check --deploy`.
- JavaScript válido, guard es-CL: 32 archivos sin hallazgos. Detector externo
  sobre login renderizado sin hallazgos; el análisis de templates sin renderizar
  no resuelve tags Django y marca las imágenes de Croppr aún no seleccionadas.
- `collectstatic`: dos archivos nuevos, 153 estáticos en total.
- Revisión independiente de lectura sin hallazgos importantes. No acredita
  participación ni revisión académica de un compañero.

Se reinició Daphne porque su proceso conservaba templates anteriores en caché.
La aplicación adaptada quedó abierta en Safari en `http://127.0.0.1:8001`.
AWS y SMTP público permanecen pendientes; no se afirma cumplimiento total.
