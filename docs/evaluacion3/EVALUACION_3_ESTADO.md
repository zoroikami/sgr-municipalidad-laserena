# Evaluación III: estado verificable

Fecha: 10 de noviembre de 2026, America/Santiago.
Aplicación desplegada desde `main`: merge del PR #13 (`8f189c8807c1d0051ab7dc6eb1c0a751c5d4369a`).

## AWS verificado

- URL pública: https://sgr-184-195-57-121.sslip.io
- EC2 existente: `i-0a5533ede6cc60b7e`, `us-east-1`, Amazon Linux 2023.
- Imagen Docker construida en EC2; Compose con MySQL 8.4.13, Redis, Daphne y Nginx; migraciones aplicadas; `verify_environment --demo --production` aprobado.
- Certificado público Let's Encrypt; cookies Secure y HTTPS/WSS comprobados sin desactivar verificación TLS. Simulación de renovación ACME aprobada y temporizador diario activo.
- Siete sesiones: seis cuentas nombradas y un superadministrador independiente con todos los ámbitos, módulos, gestión de roles y portal ciudadano.
- Recorrido real en navegador: WebSocket A/B, filtros, modal inválido, cancelación SweetAlert, layouts 375/768/1280, aislamiento de clientes, foto recortada persistente y privada.
- Recuperación enviada mediante SMTP a **Mailpit privado**; token de un uso, rechazo de contraseña anterior y cambio con contraseña actual verificados. No acredita entrega a correo externo.
- Posteriormente se configuró **Gmail SMTP** en AWS: autenticación STARTTLS en puerto 587 y `verify_environment --demo --production` aprobados. Gmail aceptó un correo de prueba al destinatario autorizado; no se inspeccionó su bandeja. Remitente y contraseña de aplicación permanecen en la configuración privada del servidor.
- Respaldo previo de MySQL, fotos, configuración e imagen anterior disponible en el host. El historial local anterior quedó conservado en una rama de archivo.
- MySQL y aplicación reiniciados: la huella de registros de negocio, usuarios, hashes de contraseñas y fotos permaneció idéntica; `/api/health/` volvió a responder correctamente.
- Elastic IP `184.195.57.121`, reserva `eipalloc-08967e7da51b66e2c`, asociación `eipassoc-0b0f523c84db1f850`. El enlace permanece estable al detener/iniciar mientras se conserve la reserva y el laboratorio no elimine el recurso. Tiene cargo de IPv4 pública de AWS.

## Validación local completada

| Comprobación | Resultado observado |
| --- | --- |
| Motor y migraciones | MySQL 8.4.7 real, base aislada, migraciones aplicadas; sin migraciones pendientes |
| Suite Django | 91 pruebas aprobadas con MySQL y Redis reales, incluidas provisión de superadministrador, aislamiento del portal, nombres, concurrencia, permisos, recuperación y errores HTTP |
| RUT compartido | 2 pruebas Python y 2 Node aprobadas |
| Servicios | Redis 7.4.11 con envío/recepción real; SMTP entregado a Mailpit 1.27.10 |
| Navegador | Cinco scripts aprobados: Croppr, flujos completos, diseño, paneles y usabilidad |
| Seis sesiones | Administrador/editor/lector A, lector B y dos clientes autenticados en sesiones independientes |
| WebSocket | Editor A cambia lector A sin F5; lector B aislado; filtros y estado de desconexión correctos |
| CRUD y consultas | Formulario inválido permanece en modal; cancelar SweetAlert no archiva; estado de sesión, orden, filtros y Excel verificados |
| Foto | Recorte real persistente; cancelación conserva foto anterior; foto ajena rechazada; mouse y teclado operativos |
| Correo | Recuperación recibida por SMTP, contraseña anterior rechazada, token usado rechazado y contraseña privada restaurada |
| Producción local | DEBUG=False, checks sin advertencias, 155 estáticos recopilados, Nginx 1.28.3 y Daphne |
| HTTPS/WSS | Certificado local efímero confiado explícitamente por el cliente de prueba, sin desactivar verificación TLS; cookies Secure, estáticos, 403/404, fotos privadas y Upgrade WSS comprobados |
| Persistencia | Reinicio de MySQL y segunda ejecución de semillas: misma huella de datos, cuentas, hashes de contraseña y archivos de fotos |
| Semillas | 6 delegaciones + 360 metas + 30 tipos + 90 subatenciones + 1.800 atenciones = 2.286 registros de negocio |
| Configuración | Producción rechaza SQLite; Channels y Daphne obligatorios; secretos fuera de Git |
| Documentación | README actualizado, script de configuración recuperado y diagrama Mermaid/SVG sincronizado con el perfil opcional de soporte global |

El entorno fue Windows con servicios nativos aislados. Redis utilizó el port de
redis-windows para MSYS2; Mailpit y Nginx se obtuvieron de sus proyectos oficiales.
Los binarios, configuraciones privadas, certificados y logs permanecieron fuera del
repositorio. Las capturas están en `output/browser/`, excluido de Git. Esto acredita
el comportamiento local. La imagen Docker para Linux se construyó posteriormente
en EC2 y se verificó allí el despliegue público descrito arriba.

## Preparación reproducible

1. `python scripts/configure_local.py` crea `.env` con secretos nuevos y conserva
   cualquier archivo existente.
2. Iniciar MySQL, Redis y Mailpit con `compose.yaml` o configurar servicios nativos
   equivalentes mediante variables de entorno.
3. Migrar, ejecutar `seed_demo` y `verify_environment --demo`.
4. Ejecutar `pytest tests_django`, pruebas compartidas de RUT y scripts de navegador
   según README. No ejecutar suites simultáneas contra la misma base de pruebas.
5. `verify_environment --production --demo` comprueba servicios y configuración
   segura antes del despliegue. El script de EC2 lo ejecuta después de migrar y cargar.

## Pendientes externos para la entrega

- **Disponibilidad del laboratorio:** mantener EC2 encendido durante la demostración
  y conservar la reserva de Elastic IP; restablecer el laboratorio puede eliminar recursos.
- **Revisión humana:** un compañero debe revisar los PR funcionales de cada
  integrante. Los aportes de zoroikami, Hvsh-bit y Bogotor existen; en los PR
  consultados no aparecían revisiones formales. No se fabrican revisiones ni autoría.
- **GitHub Actions:** los últimos trabajos no iniciaron pasos por bloqueo de
  facturación de la cuenta. Resolverlo corresponde al propietario; después ejecutar
  la CI sobre el commit final.
- **Destinatarios de recuperación:** registrar correos reales en las cuentas que aún
  utilizan `@example.test`; confirmar recepción en el buzón del destinatario.
  Gmail SMTP ya está configurado; la prueba autorizada fue aceptada por el proveedor.
- **Entrega y defensa:** registrar el repositorio y nombres completos en la
  plataforma; entregar las seis credenciales por medio privado y explicar código,
  permisos, ORM/ModelForms, sesión y recorrido de `transaction.on_commit` a Redis,
  WebSocket y la vista protegida de tabla. La pauta no pide un informe adicional.

No se asigna puntaje ni se afirma cumplimiento del 100% de la evaluación: la
revisión real del equipo, facturación de CI y entrega académica siguen pendientes.
