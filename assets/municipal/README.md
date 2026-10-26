# Identidad municipal

Los tres frontends cargan `brand.css` después de sus estilos para compartir tipografía, colores y logo.

- Logo: `logo-la-serena.svg`, trazado vectorial del logo horizontal adjunto (escudo, “LA SERENA” e “ILUSTRE MUNICIPALIDAD”), con las proporciones originales y los márgenes exteriores recortados en un lienzo de 716 × 199. Fondo transparente, sin imágenes raster incrustadas. El PNG histórico se conserva sin modificar. La cabecera muestra el SVG blanco; las superficies claras aplican un filtro monocromático para mantener su legibilidad sin agregar un recuadro.
- Cabecera y autenticación de evaluacion2: `logo-la-serena-horizontal.svg`, versión horizontal oficial descargada de https://framework.laserena.cl/img/horizontal-blanco.svg el 15-10-2026. Se conserva el trazado original y se normaliza la codificación a UTF-8.
- Paleta institucional proporcionada el 13-10-2026: rojo luminoso `#DB3334`, rojo heráldico `#C41230` y rojo oscuro `#8B1D19`. Las superficies y los separadores usan mezclas de estos colores con blanco; los textos mantienen un neutro oscuro legible. El rojo heráldico identifica cabecera, botones principales y foco; el rojo oscuro sus estados de interacción y el luminoso los acentos.
- Guardar atención: verde `#287346`, con estados de interacción y foco propios.
- Estados activos: verde lima `#D9F99D`, texto `#365314`. Acciones: Ver en celeste suave, Editar en amarillo y Eliminar en rojo suave. Cada acción tiene estados de foco, hover, pulsación y deshabilitado, además de su etiqueta visible.
- Tipografía formal de sistema: SF en macOS, Segoe UI en Windows y Helvetica/Arial como respaldo. No requiere descargas ni archivos de fuentes comerciales.
- Excel: SVG local minimalista, sin dependencias externas para el icono.
- Formulario, historial y tablero comparten un ancho máximo de 74 rem. El historial incluye título, controles, tabla desplazable y paginación dentro del mismo marco.
- Selector de delegación: superficie blanca de 320 px por 44 px, nombre principal y código secundario, ubicación y flecha única. Conserva un select nativo accesible y las restricciones del perfil; las etiquetas visuales se sincronizan con la selección.

La jerarquía tipográfica usa títulos de 26-32 px, encabezados de sección de 20 px, subtítulos de 18 px, texto de 16 px, controles de 15 px y notas de 13 px. Las tablas de evaluacion2 siguen principios de Apple: jerarquía contenida, filas sin bandas, separadores finos, cifras tabulares, estados discretos y acciones contextuales. Ver incluye un ojo SVG decorativo y conserva su etiqueta accesible. Cada tabla se desplaza dentro de su propio marco y tiene encabezados semánticos y una región accesible por teclado.

Cabecera, navegación, formularios, ventanas y botones siguen el mismo ritmo de espacios, tipografía y bordes. La aplicación exige credenciales y no ofrece perfiles automáticos, accesos rápidos ni barra de suplantación de roles. Las cuentas y permisos existentes se conservan. Las sesiones del antiguo acceso automático se descartan al actualizar.

Los códigos de delegaciones (`DEL01`) e ítems/metas (`IT001`) se asignan al guardar, tanto en la API como en modo local. La API genera el correlativo dentro de una transacción de escritura y no acepta códigos elegidos por el cliente. Los códigos existentes se conservan y no se editan.

SweetAlert2 se monta en `body`, por encima de cabecera y modales, con captura de teclado independiente. Los errores de guardado, eliminación y autenticación se presentan sin cierre automático. La paginación mantiene primera/última página y una ventana de tres páginas, con elipsis y controles que se ajustan al ancho disponible.

Pie de página: franja negra al final de los tres frontends con “© 2026 Ilustre Municipalidad de La Serena. Todos los derechos reservados.”, basada en la [plantilla oficial](https://framework.laserena.cl/templates/footer.html). Su espaciado y tipografía siguen el patrón compartido. Se mantiene local, sin cargar scripts del sitio municipal.

Perfil personal: el avatar de la cabecera abre «Mi perfil» para cualquier usuario autenticado. Permite previsualizar, guardar o quitar su propia foto. Usuarios nuevos reciben `avatar-default.svg` y el formulario de creación permite subir una foto opcional. Acepta JPG, PNG o WebP de hasta 5 MB; la interfaz prepara un JPEG cuadrado de 512 px. El contenido de la imagen se guarda en SQLite (`user_profiles.photo_data`) y se recupera al iniciar sesión. Los endpoints de perfil usan una sesión verificada del propietario; los tokens se almacenan con hash y caducan después de siete días. La foto no depende de localStorage. SweetAlert conserva su capa superior a los modales.

Todos los códigos de delegaciones, roles, ítems/metas, tipos y subatenciones se generan al guardar. Los formularios nuevos no solicitan códigos manuales; la edición conserva el código existente.

RUT: los campos editables de RUT en usuarios y atención ciudadana validan formato y dígito verificador con módulo 11, incluido `K`, en la interfaz y el servidor. Se guarda una versión normalizada sin puntos y con guion; los duplicados se comprueban también contra los formatos históricos. El formulario de atención pide nombre y RUT por separado y no asigna RUT ficticios. Los filtros de búsqueda aceptan consultas parciales y conservan su alcance sobre columnas visibles. Esta validación matemática no acredita inscripción ni identidad en un registro oficial; no se realizan consultas externas. Referencia del criterio de módulo 11: [manual del SII](https://www.sii.cl/factura_electronica/Webservice_Registro_Reclamo_DTE_V1.1.pdf).
