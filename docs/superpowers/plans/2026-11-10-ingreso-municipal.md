# Corregir el destino del ingreso municipal

El usuario reportó que al entrar veía «Administración del entorno» de Django.
La sesión era de un superusuario técnico sin Perfil. `gestion:inicio` redirigía
expresamente esas cuentas a `admin:index`, aunque el usuario buscaba el SGR.

## Corrección

- El Inicio ya no envía automáticamente a la consola técnica: vuelve al login
  municipal con una explicación de la delegación requerida.
- El formulario municipal informa a los superusuarios sin Perfil que necesitan
  una cuenta con delegación asignada. La autenticación técnica en `/admin/`
  conserva su función y sus permisos.
- El login usa el layout público incluso si queda una sesión técnica abierta;
  no renderiza un menú municipal con ámbito vacío.
- Las cuentas municipales y los superusuarios que ya tienen Perfil mantienen
  el ingreso habitual. No se crean perfiles, RUT ni privilegios automáticamente.

## Evidencia

- Antes del cambio fallaron las dos regresiones que reproducen el ingreso de
  soporte por el login municipal y la redirección de su sesión existente.
- Después aprobaron las cinco regresiones nuevas y las 80 pruebas Django.
- `check --deploy --fail-level WARNING` sin problemas.
- En Safari se comprobó el regreso al login público y se ingresó con `admin_a`;
  quedó visible Gestión municipal con delegación Centro y las cuatro mini tablas.
  Se descartó el aviso de guardar contraseña del navegador.

Los cambios previos de README e informe de estado se conservan aparte.
