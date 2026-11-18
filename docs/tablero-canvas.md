# Seguimiento de cartas y gestiones

La vista de cartas reutiliza el formato Card/Canvas del Tubo de trabajo y las clases `tubo-*` del sistema. Conserva los cuatro estados de la hoja «TUBO CARTAS»: En proceso, Aprobada, Finalizada y No aplica. Los registros archivados y los de otras delegaciones quedan fuera del ámbito autorizado.

Los documentos no establecen el grafo de transición de cartas. Se infiere el recorrido mínimo En proceso → Aprobada → Finalizada y la alternativa En proceso → No aplica. Finalizada y No aplica son terminales. No se agrega arrastrar y soltar. El avance requiere POST, CSRF, permiso de cambio y coincidencia del estado de origen bajo bloqueo de fila. Los lectores pueden consultar el tablero sin controles de cambio.

Las tarjetas se ordenan por fecha de actividad ascendente, las fechas vacías van al final y los empates se resuelven por clave primaria. Cada columna muestra hasta 100 registros e incluye el acceso al listado completo cuando supera ese límite; los totales incluyen todos los registros autorizados.

## Historial (RF-018 y CA-03)

Cada avance desde los tableros o la edición conserva estado anterior, nuevo estado, autor, instante y observación opcional. Estado e historial se escriben en la misma transacción bajo bloqueo de fila. Reintentos con un origen obsoleto y ediciones sin cambio de estado no generan entradas. La edición permite el estado actual y los siguientes estados autorizados; el Tubo conserva la secuencia Ingresado → Pendiente → En proceso → Realizado.

La observación de la transición es un campo separado de la descripción general del registro. El historial se consulta solo desde el detalle y hereda sus permisos y ámbito de delegación. No hay rutas para modificarlo. La migración no inventa fechas de cierre para registros anteriores: comienzan sin entradas hasta la primera transición registrada.

## Plazos (RF-019, CA-03 y HU-12)

El Tubo destaca «Vencido» cuando el compromiso es anterior a la fecha local y la gestión no está Realizada. Cartas aplica el mismo aviso a la fecha de actividad exclusivamente mientras está En proceso. Los resúmenes cuentan todos los vencidos del ámbito autorizado, incluidos los que exceden las 100 tarjetas visibles.

Los compromisos de hoy muestran «Vence hoy» y los de los próximos tres días muestran «Vence en N días». No se avisa para fechas vacías o posteriores a esa ventana. Una gestión Realizada o carta Finalizada muestra «Realizado fuera de plazo» si la fecha local de su última transición al estado final es posterior a su compromiso/actividad. No se usa la última edición como fecha de realización ni se infieren cierres para registros históricos sin transición registrada. Cada transición conserva además la fecha objetivo vigente al cambiar de estado. El cierre tardío compara con esa fecha congelada al cerrar; editar o quitar la fecha después del cierre no altera el resultado histórico. Los historiales anteriores sin fecha objetivo conservada se consideran de fecha desconocida.

Ambos tableros ordenan por fecha de compromiso/actividad ascendente, con fechas vacías al final y clave primaria como desempate. No se implementa arrastrar y soltar.
