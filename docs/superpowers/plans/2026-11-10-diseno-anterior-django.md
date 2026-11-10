# Adaptación del diseño anterior: Implementation Plan

**Goal:** Recuperar la interfaz de la segunda evaluación sobre el backend Django
de la tercera evaluación, según la confirmación del usuario.

**Architecture:** Herencia de templates Django y CSS adicional después de los
estilos existentes. Los endpoints, formularios, consultas y permisos permanecen
en el servidor. JavaScript nuevo únicamente para Mostrar/Ocultar contraseña.

**Tech Stack:** Django templates, CSS, JavaScript, Bootstrap, Playwright, pytest.

## Global Constraints

- Referencia visual: `index.html`, `evaluacion2/css/sgr_eval2.css`, `assets/municipal/brand.css`.
- Conservar íntegros los contratos de la Evaluación III descritos en el spec.
- Trabajar en la rama feature actual; preservar README y el informe ya modificados.
- Implementar en esta sesión, sin nuevas dependencias; revisión final independiente
  de lectura según `requesting-code-review`.

## 1. Autenticación y estructura

- [x] Crear `tests_browser/check_design.py`: probar contraseña oculta por defecto,
  alternancia Mostrar/Ocultar sin envío y login por Enter; ejecutar y observar el
  fallo por ausencia del control Mostrar.
- [x] Adaptar `templates/base.html`, añadir `templates/shared/icon.html`,
  `templates/cuentas/auth_base.html` y adaptar las cuatro páginas de recuperación.
- [x] Añadir `static/sgr/interface.js` y `legacy.css`. Mantener `contenido`,
  `module-nav`, las rutas, POST logout y etiquetas accesibles actuales.

## 2. Superficies de gestión

- [x] Adaptar `listado.html` y `_tabla.html`: breadcrumb, panel con herramientas,
  búsqueda y Excel, acciones azul/amarillo/rojo y estados con texto explícito.
- [x] Adaptar inicio, detalle, portal, cuentas y perfil al mismo sistema visual.
- [x] Conservar `#record-modal`, `#record-form`, `#tabla-region`, `#realtime-status`,
  `#profile-form` y los controles Croppr para reutilizar los scripts actuales.

## 3. Verificación y entrega

- [x] Ejecutar el test de interacción y revisar capturas en 320/375/768/1280 px.
- [x] Ejecutar los recorridos existentes de browser, Croppr y las tres suites.
- [x] Ejecutar `node --check`, checks Django, guard es-CL y `git diff --check`.
- [x] Revisar el diff final para comprobar que backend y cambios ajenos permanecen.
- [x] Mostrar la aplicación adaptada en Safari y reportar los límites externos AWS.
