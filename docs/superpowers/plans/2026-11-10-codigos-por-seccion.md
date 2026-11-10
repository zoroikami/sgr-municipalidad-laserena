# Recuperar códigos por sección

Petición: volver a los códigos anteriores, iniciales y correlativo ascendente.
Referencia comprobada: `data_eval2.js:generateCode` y `server.py:next_record_code`.

Formatos: DEL01, IT001, TA001, SA001; folio ATN-año-0001. El correlativo es global
por sección (anual para atenciones), automático en servidor y crece más allá del
ancho mínimo. Incluye archivados para no reutilizar identificadores.

## Implementación

- [x] Probar formato, continuación, archivados, desborde y concurrencia en MySQL.
- [x] Adaptar Secuencia con bloqueo transaccional y máximo numérico existente.
- [x] Añadir referencia interna al código anterior para trazabilidad y reversión.
- [x] Migrar códigos existentes, conservando IDs y relaciones, en dos fases para
  evitar colisiones de índices únicos; las referencias anteriores no son editables.
- [x] Usar la referencia anterior como clave estable de semillas, para que repetir
  la carga no duplique registros ni reemplace ediciones o claves de cuentas.
- [x] Respaldar MySQL en `.private/backups/` antes de aplicar la migración local.
- [x] Ejecutar suite Django, semillas idempotentes y recorridos de browser.

La migración es reversible. Ante colisión entre un código anterior y un registro
nuevo creado después, la reversión se rechaza antes de escribir; el respaldo
privado conserva el estado previo completo. No se reescribe el backend histórico,
ni los roles Django, ni el RUT utilizado para identificar cuentas.

Preservar los cambios ya terminados de paneles y descripciones (commit ab2b60d)
y las modificaciones previas independientes de README e informe de evaluación.

## Resultados

- Migración aplicada con 6 delegaciones, 360 metas, 30 tipos, 90 subatenciones y
  1.800 atenciones. Contadores locales: DEL=6, IT=360, TA=30, SA=90 y ATN-2026-=1800.
- La carga de semillas repetida conservó todos los campos de negocio, códigos,
  contraseñas y contenido del archivo privado de credenciales.
- 70 pruebas Django aprobadas, incluidas conversión/reversión, rechazo de colisión
  en reversión y cuatro conexiones MySQL sincronizadas con contador inicialmente
  inexistente. La prueba fría reprodujo un deadlock antes de corregirlo.
- La inicialización usa un upsert parametrizado con bloqueo exclusivo, seguido
  del bloqueo de la fila de secuencia. Evita la promoción de bloqueos compartidos
  que produjo el fallo con `get_or_create`, según el comportamiento documentado
  de [InnoDB 8.4](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html).
- `check_flows.py` y `check_paneles.py` aprobados después de migrar los datos.
  Django sin advertencias de despliegue ni migraciones pendientes.
- Revisión de lectura adicional sin hallazgos importantes. Los códigos IT001,
  IT002 e IT003 se comprobaron también en Safari.
