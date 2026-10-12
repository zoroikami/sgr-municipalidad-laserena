# Identidad municipal

Los tres frontends cargan `brand.css` después de sus estilos para compartir tipografía, colores y logo.

- Logo: `logo-la-serena.svg`, trazado vectorial de las formas blancas del original. Fondo transparente, sin rectángulo rojo ni borde exterior. El PNG original se conserva como fuente. La cabecera muestra el SVG blanco; las superficies claras aplican un filtro monocromático para mantener su legibilidad sin agregar un recuadro.
- Paleta solicitada: rojo principal `#AD0000`, vino `#4A1417`, crema `#EFE1CF` y arena `#D7B59A`. Las superficies y los separadores usan mezclas de estos colores con blanco. El rojo principal proviene del [framework municipal](https://framework.laserena.cl/css/frameworkV1.css), verificado el 12-10-2026.
- Guardar atención: verde `#287346`, con estados de interacción y foco propios.
- Estados activos: verde lima `#D9F99D`, texto `#365314`. Acciones: Ver en celeste suave, Editar en amarillo y Eliminar en rojo suave. Cada acción tiene estados de foco, hover, pulsación y deshabilitado, además de su etiqueta visible.
- Tipografía formal de sistema: SF en macOS, Segoe UI en Windows y Helvetica/Arial como respaldo. No requiere descargas ni archivos de fuentes comerciales.
- Excel: SVG local minimalista, sin dependencias externas para el icono.
- Formulario, historial y tablero comparten un ancho máximo de 74 rem. El historial incluye título, controles, tabla desplazable y paginación dentro del mismo marco.
- Selector de delegación: superficie blanca de 320 px por 44 px, nombre principal y código secundario, ubicación y flecha única. Conserva un select nativo accesible y las restricciones del perfil; las etiquetas visuales se sincronizan con la selección.

La jerarquía tipográfica usa títulos de 26-32 px, encabezados de sección de 20 px, subtítulos de 18 px, texto de 16 px, controles de 15 px y notas de 13 px. Las tablas de evaluacion2 siguen principios de Apple: jerarquía contenida, filas sin bandas, separadores finos, cifras tabulares, estados discretos y acciones contextuales. Ver incluye un ojo SVG decorativo y conserva su etiqueta accesible. Cada tabla se desplaza dentro de su propio marco y tiene encabezados semánticos y una región accesible por teclado.

Cabecera, perfiles, navegación, formularios, ventanas y botones siguen el mismo ritmo de espacios, tipografía y bordes. En móvil, perfiles y módulos se desplazan horizontalmente dentro de sus propios contenedores. La cabecera ofrece un material translúcido discreto, con alternativa opaca cuando el sistema solicita reducir transparencia.

Pie de página: franja negra al final de los tres frontends con “© 2026 Ilustre Municipalidad de La Serena. Todos los derechos reservados.”, basada en la [plantilla oficial](https://framework.laserena.cl/templates/footer.html). Su espaciado y tipografía siguen el patrón compartido. Se mantiene local, sin cargar scripts del sitio municipal.
