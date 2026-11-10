# Delegaciones y roles: plan de implementación

**Goal:** Restaurar roles municipales y cambio de delegación autorizado en la aplicación local.

**Architecture:** Roles centralizados en cuentas/roles.py y migración de grupos con membresías conservadas. Middleware carga el ámbito de sesión sobre la instancia de usuario de la petición; gestion/access.py aplica el mismo filtro a todos sus consumidores y Channels revalida la sesión.

**Tech Stack:** Django 5.2, MySQL 8.4, Channels, Redis, templates y CSS municipal.

## Restricciones

Conservar Cliente, contraseñas, datos y marca. Solo Superadministrador/Coordinador cambian ámbito. Solo Superadministrador asigna acceso comunal/técnico. Sin publicación remota.

## 1. Roles y cuentas

- [x] Escribir y ejecutar pruebas que detecten elevación de privilegios y permisos de los roles restaurados.
- [x] Modificar cuentas/roles.py, cuentas/forms.py, cuentas/views.py y gestion/management/commands/seed_demo.py. Crear cuentas/migrations/0004_restore_municipal_roles.py; renombrar o fusionar membresías existentes sin tocar usuarios.
- [x] Actualizar fixtures y expectativas históricas para los nombres y capacidades aprobados; probar migración e idempotencia.

## 2. Ámbito por sesión

- [x] Escribir pruebas HTTP para selector, aislamiento de sesión, CRUD, Excel, catálogo, cuentas y selección no autorizada.
- [x] Crear gestion/delegation.py: has_global_scope(user), active_delegation(user), DelegationMiddleware. Consumir estas funciones desde access, forms, views, queries y contexto; endpoint POST con CSRF y validación de delegación activa.
- [x] Revalidar selección desde sesión en gestion/consumers.py y probar cambio/revocación de ámbito en sockets existentes.

## 3. Interfaz y validación

- [x] Modificar templates/base.html, templates/shared/sidebar.html, templates/cuentas/_fields.html, static/sgr/legacy.css y static/sgr/interface.js: selector nativo con botón de envío sin JS, casilla alineada.
- [x] Ejecutar pytest tests_django, manage.py check y makemigrations --check --dry-run.
- [x] Respaldar membresías locales, migrar, reiniciar Daphne y verificar interfaz real, login y cambio de ámbito a dos anchos.
- [x] Actualizar README con roles y alcance actuales; revisar el diff final y comunicar resultados.
