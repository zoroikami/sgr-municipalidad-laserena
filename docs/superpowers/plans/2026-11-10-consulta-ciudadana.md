# Consulta ciudadana por correo: plan

**Goal:** Permitir consultar una atención sin cuenta mediante folio y código privado enviado al correo del solicitante.

**Architecture:** Datos opcionales en Atencion y servicios en gestion/consulta.py; formularios y vistas públicas separados del CRUD. Envío SMTP posterior al commit y validación con límite Redis. Templates y estilos reutilizan la identidad municipal.

**Tech Stack:** Django 5.2, MySQL, RedisCache, SMTP, templates y CSS existentes.

## Requisitos globales

Solo lectura pública mínima; no exponer datos personales. Mantener roles, ámbitos, rutas de login y sesiones vigentes. No enviar mensajes a terceros durante verificaciones de producción.

## 1. Código privado y correo

- [x] Escribir pruebas para crear/cambiar correo, enviar por SMTP, renovar, conservar código si falla SMTP y rechazar códigos vencidos/ajenos.
- [x] Añadir solicitante_email, consulta_codigo_hash y consulta_enviado_at en gestion/models.py y migración gestion/0004_public_consultation.py.
- [x] Implementar generación, HMAC, caducidad, envío y consulta en gestion/consulta.py. Integrar correo en AtencionForm y callbacks on_commit en el guardado y reenvío autorizado.

## 2. Consulta pública

- [x] Escribir pruebas HTTP para raíz anónima, formulario POST, mínimos campos públicos, CSRF, errores uniformes, archivo, límite por IP y Redis indisponible.
- [x] Crear gestion/public_forms.py y gestion/public_views.py; registrar /consulta/ y el POST autorizado de reenvío. Configurar alias RedisCache con tiempos de conexión acotados.
- [x] Mantener / para dashboard autenticado y mostrar entrada ciudadana sin sesión.

## 3. Interfaz y verificación

- [x] Crear templates/gestion/consulta_publica.html, correo de acceso y CSS acotado, conservando marca y accesibilidad. Añadir acceso desde login y acción de correo en detalle de atención.
- [x] Probar en navegador el recorrido completo con Mailpit y diferentes anchos. Comprobar fallos de consulta sin divulgar datos privados.
- [x] Ejecutar suite completa, checks, revisión independiente, migración local y actualizar README.
- [ ] Commit, push, PR, respaldo y despliegue AWS. Verificar página pública, login, roles y versión sin enviar mensajes externos de prueba.
