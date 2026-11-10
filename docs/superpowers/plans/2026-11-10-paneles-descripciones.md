# Paneles y descripciones

Petición del usuario: limitar descripciones a 500 caracteres y mejorar los accesos
del inicio siguiendo las skills de diseño, conservando el diseño municipal y los
requisitos de la Evaluación III.

## Diseño

Cada acceso completo será un enlace accesible por clic o Enter. La tarjeta incluye
el icono del módulo, título, explicación breve, total real y acción «Abrir panel».
Usa colores municipales, un borde de acento, dos columnas en escritorio y una en
móvil, con estados de hover, foco y pulsación sin movimiento decorativo.

Las descripciones de metas, atenciones, tipos y subatenciones tendrán límite 500
en el modelo, ModelForm y textarea. Un contador acompaña al texto de ayuda. Los
POST manipulados de 501 caracteres se rechazan sin escribir ni truncar datos.
La revisión de datos locales encontró cero descripciones superiores a 500.

## Implementación y comprobaciones

- [x] Crear pruebas de límites 500/501 para altas y ediciones de los cuatro modelos.
  Antes del cambio fallaron los ocho rechazos de 501, como se esperaba.
- [x] Añadir prueba de navegación por tarjeta y contador en navegador. Antes del
  cambio falló por ausencia de la región de enlaces completa.
- [x] Cambiar modelos y formularios; generar migración de los cuatro TextField.
- [x] Añadir contador y reformar enlaces del inicio con datos del servidor.
- [x] Aplicar migración local y comprobar ausencia de migraciones pendientes.
- [x] Ejecutar las 65 pruebas Django y los recorridos de browser pertinentes.
- [x] Revisar capturas a 320/375/768/1280, teclado y validaciones sin JavaScript.
- [x] Ejecutar sintaxis JavaScript, guard es-CL y `git diff --check`.

Resultado: 65 pruebas Django aprobadas, recorridos `check_paneles.py` y
`check_flows.py` aprobados, guard es-CL sin hallazgos y revisión independiente de
lectura sin problemas importantes. El inicio actualizado quedó abierto en Safari.

Archivos: `gestion/models.py`, `forms.py`, `views.py`, migración nueva,
`templates/gestion/inicio.html`, `formulario.html`, `static/sgr/legacy.css`,
`interface.js`, `tests_django/test_descriptions.py`, `tests_browser/check_paneles.py`.
Preservar las modificaciones previas de README y del informe de estado. No cambiar
permisos, consultas, datos existentes ni el backend histórico de la segunda entrega.
