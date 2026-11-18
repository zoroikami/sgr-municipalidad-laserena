# Seguimiento de cartas y gestiones

La vista de cartas reutiliza el formato Card/Canvas del Tubo de trabajo y las clases `tubo-*` del sistema. Conserva los cuatro estados de la hoja «TUBO CARTAS»: En proceso, Aprobada, Finalizada y No aplica. Los registros archivados y los de otras delegaciones quedan fuera del ámbito autorizado.

Los documentos no establecen el grafo de transición de cartas. Se infiere el recorrido mínimo En proceso → Aprobada → Finalizada y la alternativa En proceso → No aplica. Finalizada y No aplica son terminales. No se agrega arrastrar y soltar. El avance requiere POST, CSRF, permiso de cambio y coincidencia del estado de origen bajo bloqueo de fila. Los lectores pueden consultar el tablero sin controles de cambio.

Las tarjetas se ordenan por fecha de actividad ascendente, las fechas vacías van al final y los empates se resuelven por fecha de ingreso y clave. Cada columna muestra hasta 100 registros e incluye el acceso al listado completo cuando supera ese límite; los totales incluyen todos los registros autorizados.
