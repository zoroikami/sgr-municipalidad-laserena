# Seguimiento de cartas y gestiones

La vista de cartas reutiliza el formato Card/Canvas del Tubo de trabajo y las clases `tubo-*` del sistema. Conserva los cuatro estados de la hoja «TUBO CARTAS»: En proceso, Aprobada, Finalizada y No aplica. Los registros archivados y los de otras delegaciones quedan fuera del ámbito autorizado.

Los documentos no establecen el grafo de transición de cartas. Se infiere el recorrido mínimo En proceso → Aprobada → Finalizada y la alternativa En proceso → No aplica. Finalizada y No aplica son terminales. No se agrega arrastrar y soltar. El avance requiere POST, CSRF, permiso de cambio y coincidencia del estado de origen bajo bloqueo de fila. Los lectores pueden consultar el tablero sin controles de cambio.

Las tarjetas se ordenan por fecha de actividad ascendente, las fechas vacías van al final y los empates se resuelven por fecha de ingreso y clave. Cada columna muestra hasta 100 registros e incluye el acceso al listado completo cuando supera ese límite; los totales incluyen todos los registros autorizados.

## Historial (RF-018 y CA-03)

Cada avance desde los tableros o la edición conserva estado anterior, nuevo estado, autor, instante y observación opcional. Estado e historial se escriben en la misma transacción bajo bloqueo de fila. Reintentos con un origen obsoleto y ediciones sin cambio de estado no generan entradas. La edición permite el estado actual y los siguientes estados autorizados; el Tubo conserva la secuencia Ingresado → Pendiente → En proceso → Realizado.

La observación de la transición es un campo separado de la descripción general del registro. El historial se consulta solo desde el detalle y hereda sus permisos y ámbito de delegación. No hay rutas para modificarlo. La migración no inventa fechas de cierre para registros anteriores: comienzan sin entradas hasta la primera transición registrada.
