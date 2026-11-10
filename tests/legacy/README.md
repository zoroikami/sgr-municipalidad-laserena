# Pruebas históricas de la evaluación II

Estas pruebas pertenecen al servidor `server.py`, `profile_service.py` y la interfaz
`evaluacion2/`, retirados de `main` en `ac5bc52`. Se conservan como referencia;
para ejecutarlas hay que usar una revisión anterior a esa limpieza, donde
permanecen en su ubicación original y existen sus dependencias.

La aplicación actual se verifica con `pytest tests_django`. Las pruebas compartidas
de RUT siguen activas en `tests/test_rut.py` y `tests/test_rut.cjs`. El descubrimiento
de unittest y el patrón Node de CI no incluyen este directorio histórico.
