# Seguimiento de cartas y gestiones

La vista de cartas reutiliza el formato Card/Canvas del Tubo de trabajo y las clases `tubo-*` del sistema. Conserva los cuatro estados de la hoja «TUBO CARTAS»: En proceso, Aprobada, Finalizada y No aplica. Los registros archivados y los de otras delegaciones quedan fuera del ámbito autorizado.

Los documentos no establecen el grafo de transición de cartas. Se infiere el recorrido mínimo En proceso → Aprobada → Finalizada y la alternativa En proceso → No aplica. Finalizada y No aplica son terminales. El avance requiere POST, CSRF, permiso de cambio y coincidencia del estado de origen bajo bloqueo de fila. Los lectores pueden consultar el tablero sin controles de cambio.

Las tarjetas se ordenan por fecha de actividad ascendente, las fechas vacías van al final y los empates se resuelven por clave primaria. Cada columna muestra hasta 100 registros e incluye el acceso al listado completo cuando supera ese límite; los totales incluyen todos los registros autorizados.

## Historial (RF-018 y CA-03)

Cada avance desde los tableros o la edición conserva estado anterior, nuevo estado, autor, instante y observación opcional. Estado e historial se escriben en la misma transacción bajo bloqueo de fila. Reintentos con un origen obsoleto y ediciones sin cambio de estado no generan entradas. La edición permite el estado actual y los siguientes estados autorizados; el Tubo conserva la secuencia Ingresado → Pendiente → En proceso → Realizado.

La observación de la transición es un campo separado de la descripción general del registro. El historial se consulta solo desde el detalle y hereda sus permisos y ámbito de delegación. No hay rutas para modificarlo. La migración no inventa fechas de cierre para registros anteriores: comienzan sin entradas hasta la primera transición registrada.

## Plazos (RF-019, CA-03 y HU-12)

El Tubo destaca «Vencido» cuando el compromiso es anterior a la fecha local y la gestión no está Realizada. Cartas aplica el mismo aviso a la fecha de actividad exclusivamente mientras está En proceso. Los resúmenes cuentan todos los vencidos del ámbito autorizado, incluidos los que exceden las 100 tarjetas visibles.

Los compromisos de hoy muestran «Vence hoy» y los de los próximos tres días muestran «Vence en N días». No se avisa para fechas vacías o posteriores a esa ventana. Una gestión Realizada o carta Finalizada muestra «Realizado fuera de plazo» si la fecha local de su última transición al estado final es posterior a su compromiso/actividad. No se usa la última edición como fecha de realización ni se infieren cierres para registros históricos sin transición registrada. Cada transición conserva además la fecha objetivo vigente al cambiar de estado. El cierre tardío compara con esa fecha congelada al cerrar; editar o quitar la fecha después del cierre no altera el resultado histórico. Los historiales anteriores sin fecha objetivo conservada se consideran de fecha desconocida.

Ambos tableros ordenan por fecha de compromiso/actividad ascendente, con fechas vacías al final y clave primaria como desempate.

## Arrastrar y soltar

El pedido de Harold del 24-11-2026 habilita el arrastre de tarjetas en ambos tableros. Solo son arrastrables las tarjetas con permiso de edición y al menos una transición disponible. Mientras se arrastra, las columnas permitidas muestran un borde discontinuo del color de su estado; al entrar en una de ellas, el borde pasa a sólido. Soltar en otra columna no cambia nada. Las tarjetas terminadas y la vista del consultor no ofrecen arrastre.

Al soltar en una columna permitida, SweetAlert2 solicita una observación opcional de hasta 2000 caracteres, conservando la que ya se haya escrito para ese destino. Cancelar cierra el diálogo sin enviar el cambio. Confirmar rellena la observación y llama a `requestSubmit()` sobre el formulario POST existente de esa tarjeta y destino. El script obtiene los destinos exclusivamente de dichos formularios; no contiene una copia de las reglas de transición. La recarga del servidor actualiza las columnas, contadores, plazos y aspecto de la tarjeta. Los intentos con estado de origen obsoleto siguen rechazándose sin duplicar el historial.

Los botones y campos de observación siguen disponibles para teclado y dispositivos táctiles. El arrastre nativo está pensado para ratón; no se añade un gesto táctil que interfiera con el desplazamiento. Si falta JavaScript o SweetAlert2, los botones siguen funcionando. El estilo usa los tokens municipales existentes y elimina el levantamiento de la tarjeta cuando se solicita movimiento reducido.

`tests_django/test_tablero_dnd.py` verifica los permisos y destinos renderizados, el historial y los reintentos, y ejecuta pruebas con un servidor Django y Chromium reales: arrastre válido/inválido, cancelación, observación, anchos 375/1280, consultor sin cambios y botones sin JavaScript o sin SweetAlert2. Las pruebas de navegador se omiten explícitamente si no está instalado Chromium; para habilitarlas: `python -m playwright install chromium`.
