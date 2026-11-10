# Delegaciones y roles municipales

Diseño aprobado por el usuario el 10 de noviembre de 2026.

- Superadministrador y Coordinador pueden elegir una delegación activa o Todas las delegaciones en la cabecera. La selección pertenece a la sesión, no modifica el perfil ni los permisos del usuario.
- El ámbito elegido se aplica a inicio, CRUD, catálogos dependientes, Excel, cuentas y portal cuando corresponda. Cambiar de delegación limpia filtros anteriores; las actualizaciones de Channels respetan la sesión vigente.
- Restaurar Superadministrador, Coordinador, Delegado Municipal, Operador / Funcionario y Consultor. Conservar Cliente para sus registros propios.
- Migrar Administrador a Delegado Municipal, Editor a Operador / Funcionario y Lector a Consultor sin cambiar contraseñas, perfiles o datos de negocio.
- Superadministrador conserva acceso técnico global; Coordinador gestiona módulos municipales en ámbito comunal sin gestionar cuentas ni roles. Delegado Municipal gestiona metas, atenciones y cuentas locales. Operador / Funcionario registra y edita atenciones locales. Consultor consulta módulos municipales locales. Cliente conserva el portal aislado.
- Solo un superadministrador puede asignar roles comunales o privilegios técnicos. Un grupo llamado Superadministrador nunca eleva una cuenta por sí solo.
- La casilla Cuenta activa se coloca a la izquierda del texto, alineada verticalmente, reutilizando tokens municipales y foco accesible.

Verificación: pruebas MySQL/Redis para límites de ámbito, escrituras, exportaciones, migración de membresías, selección inválida y asignación de roles; revisión visual en escritorio y teléfono. Cambios locales, sin despliegue remoto.
