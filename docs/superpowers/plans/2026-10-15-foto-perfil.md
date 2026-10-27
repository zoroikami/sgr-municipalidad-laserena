# Foto personal en el perfil

Objetivo: mostrar un avatar en la cabecera y permitir que cualquier usuario conectado cambie o quite únicamente su propia foto desde «Mi perfil».

Arquitectura: conservar HTML/CSS/JavaScript y Python/SQLite existentes. Separar la lógica del perfil en un controlador de interfaz y un servicio Python. El servidor vincula la foto al usuario de la sesión autenticada, sin aceptar identificadores de otra cuenta. Mantener las rutas actuales, filtros sobre columnas visibles y la capa global de SweetAlert.

- [x] Añadir pruebas de persistencia, autorización por propietario, validación y eliminación de fotos en una base temporal; ejecutarlas antes de implementar el servicio.
- [x] Crear tablas aditivas de perfiles/sesiones, emitir un token verificado al ingresar y agregar GET/PUT /api/profile y revocación al salir. No modificar roles, datos personales ni registros existentes.
- [x] Añadir métodos de datos para sesión y perfil, conservando el modo local por usuario cuando no existe backend.
- [x] Implementar avatar e iniciales en la cabecera, perfil accesible con datos de solo lectura, archivo JPEG/PNG/WebP de hasta 5 MB, previsualización y reducción a JPEG de 512 × 512 antes de guardar. Pedir confirmación para quitar la foto.
- [x] Integrar ambos HTML, adaptar móvil, teclado/foco y estados de carga/error; conservar SweetAlert sobre los modales.
- [x] Ejecutar pruebas Python/Node, respaldar SQLite y reiniciar el servidor para aplicar las tablas aditivas. Actualizar versiones de recursos para evitar caché antigua.
- [ ] Revisión visual: bloqueada por indisponibilidad de Sky Computer Use (sin apps ni navegadores conectados). Verificación HTTP y pruebas automatizadas disponibles.

Ampliación solicitada: asignar avatar predeterminado a usuarios nuevos y permitir foto opcional en su creación. Guardar imágenes exclusivamente en SQLite; sin conexión al backend no se admite guardado de fotos. Generar códigos automáticamente también para roles (ROL), tipos (TA) y subatenciones (SA), tanto en backend como en modo local.

Validación de RUT solicitada durante la implementación: normalización y módulo 11 compartidos por formularios de creación de usuario y atención, validación adicional en Python y modo local, prevención de duplicados con distinto formato. No se alteran RUT históricos. No se consulta inscripción en Registro Civil/SII; esa verificación requiere una fuente autorizada, aún no proporcionada.

Ampliación de recorte y metas: agregar un editor compartido de foto con arrastre, zoom, teclado, confirmación y cancelación; conservar el original durante el ajuste y exportar solo el recorte elegido. Cerrar Mi perfil únicamente tras persistir la foto. Quitar el ajuste manual de meta_cantidad en formularios, servidor y modo local: nuevas metas usan el valor automático existente (100); las metas existentes conservan su cantidad. Se consultó opcionalmente si existe otra regla de cálculo.

Verificación final (2026-10-16): 22 pruebas Python y 48 Node aprobadas. Editor con pruebas de geometría, arrastre/zoom, confirmación/cancelación, errores de lectura/canvas y cierre del formulario de origen. Formularios de metas de solo lectura y protección adicional del valor en servidor/modo local. Recursos versionados por contenido; servidor local reiniciado con respaldo SQLite y comparación de todos los registros sin cambios. Revisión visual continúa pendiente por indisponibilidad de Computer Use.
