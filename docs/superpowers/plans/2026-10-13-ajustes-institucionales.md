# Ajustes institucionales del SGR

**Objetivo:** generar automáticamente los códigos de delegaciones e ítems/metas, exigir ingreso manual de credenciales, eliminar accesos de demostración, corregir alertas y paginación y aplicar la identidad adjunta.

**Arquitectura:** conservar Python/SQLite y JavaScript sin framework. La API asigna códigos en una transacción; el modo local mantiene el mismo formato. Las alertas comparten configuración y una capa superior a los modales. La paginación muestra extremos y una ventana acotada de páginas. Se conservan roles, cuentas y permisos existentes, pero se eliminan el ingreso automático y la suplantación desde la interfaz.

**Identidad:** rojo luminoso `#DB3334`, rojo heráldico `#C41230` y rojo oscuro `#8B1D19`. Trazar las formas blancas del logo horizontal adjunto a SVG transparente, conservando las proporciones.

## Implementación y verificación
- [x] Añadir pruebas de API para códigos automáticos y rechazo de contraseñas incorrectas; pruebas JavaScript para acceso, persistencia local y paginación.
- [x] Ejecutarlas y comprobar que detectan los comportamientos actuales.
- [x] Corregir `server.py`, `evaluacion2/js/data_eval2.js` y `evaluacion2/js/app_eval2.js` sin cambiar contratos ajenos.
- [x] Quitar accesos rápidos y barra de perfiles de `index.html` y `evaluacion2/index.html`; mantener la navegación por módulos.
- [x] Actualizar `assets/municipal/brand.css`, estilos responsivos y logo SVG; documentar la paleta y el acceso.
- [x] Ejecutar pruebas Python/Node y verificar en navegador alertas sobre modales, errores de red, login, códigos y paginación en varios anchos.

**Resultado:** 5 pruebas de API y 10 pruebas JavaScript aprobadas; comprobación de sintaxis Python/JavaScript y `git diff --check` sin errores. Verificación de navegador con paginación de 100 páginas entre 320 y 1280 px, códigos generados al guardar y alertas de validación/servidor por encima del formulario. La prueba existente de rutas estáticas conserva tres fallos de aserción sobre la ruta CSS, reproducidos también contra `HEAD` anterior a estos cambios.

No eliminar cuentas existentes, no cambiar los códigos existentes, no modificar el mockup histórico ni archivos ajenos, no crear commits.
