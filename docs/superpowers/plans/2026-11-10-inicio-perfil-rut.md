# Inicio, foto de perfil, RUT y guardado

Petición del usuario: mini tablas en Inicio, selección de foto más cómoda con
recorte acotado, ayuda para ingresar RUT sin puntos y con guion, formato legible
después de guardar y un mismo color en todos los botones Guardar.

## Diseño e implementación

- Inicio: cuatro tablas compactas con los tres registros recientes de cada
  sección autorizada, código/folio, nombre y estado; detalle por registro y
  enlace al listado completo. Conservar ámbito, permisos y exclusión de archivados.
- Foto: botón «Elegir foto», nombre del archivo, imagen actual, marco de recorte
  de hasta 384 × 320 px, controles de movimiento/zoom, confirmación y cancelación.
  Las copias de imagen creadas por Croppr tenían dimensiones naturales sin límite:
  el problema se reprodujo con una foto de 6000 × 4000 px.
- El límite visual se aplica a ambas imágenes de Croppr, sin cambiar los píxeles
  de origen ni el mapeo del recorte. El archivo final y el guardado privado siguen
  usando las validaciones de contenido y tamaño de la Evaluación III.
- Aplicar el recorte enfoca su vista previa, sin saltar al botón Guardar del final.
  Con JavaScript desactivado el input de archivo sigue disponible.
- RUT: ayuda en usuarios y atenciones; inputs sin puntos y con guion, formato
  con puntos al mostrar perfil, detalle y lista de usuarios. Mantener almacenamiento
  normalizado y validación del dígito verificador, sin tocar identificadores.
- Guardado: clase común `btn-save`, con el verde municipal existente, en perfil,
  CRUD, cuentas, roles y formularios de contraseña. Login y filtros conservan su
  acción y tratamiento propios.

## Verificación

- [x] Pruebas previas: vistas sin previews y sin formato/ayuda RUT fallaron como se
  esperaba; reproducción real de Croppr mostró ancho6000 y alto4000 antes del arreglo.
- [x] Pruebas de aislamiento, orden reciente, permisos y formato sin cambiar la BD.
- [x] Prueba de alta de usuario con RUT normalizado y mostrado con puntos.
- [x] Suite Django completa y pruebas históricas de RUT.
- [x] Chromium: mini tablas, 375/1280, fotos grandes horizontales/verticales,
  tamaño acotado, foco, confirmación/cancelación y color de guardado uniforme.
- [x] Recorridos existentes: WebSocket, portal, validación, SMTP y Croppr.
- [x] Sintaxis JavaScript, guard es-CL, checks Django, diff y revisión final.

Resultados: 75 pruebas Django aprobadas y las dos pruebas históricas de RUT.
Los recorridos `check_usability.py`, `check_flows.py`, `check_paneles.py` y
`check_crop.py` aprobaron las comprobaciones correspondientes. Capturas revisadas
de mini tablas y recorte horizontal/vertical; proporciones de imagen conservadas.
La revisión estática independiente no encontró problemas importantes.

Conservar los cambios previos independientes de README e informe de evaluación.
Los requisitos externos AWS y revisión académica de compañeros no cambian.
