# Evaluación III: estado verificable

Fecha: 10 de noviembre de 2026, America/Santiago.
Base de esta preparación: `main` después del merge del PR #12 (`191edd6`).

## Validación local completada

| Comprobación | Resultado observado |
| --- | --- |
| Motor y migraciones | MySQL 8.4.7 real, base aislada, migraciones aplicadas; sin migraciones pendientes |
| Suite Django | 87 pruebas aprobadas con MySQL y Redis reales, incluidas concurrencia, permisos, recuperación y errores HTTP |
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
el comportamiento local, no un despliegue ni una construcción nueva de la imagen
Docker para Linux. Docker no está instalado en este equipo.

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

- **AWS, pospuesto por el usuario:** construir la imagen Linux en el host de
  despliegue, verificar Compose, certificados públicos, correo y puertos; desplegar
  el `main` final y repetir la demostración con HTTP/WSS, persistencia y las seis
  cuentas. Registrar URL pública, recurso EC2 y SHA desplegado en README.
- **Revisión humana:** un compañero debe revisar los PR funcionales de cada
  integrante. Los aportes de zoroikami, Hvsh-bit y Bogotor existen; en los PR
  consultados no aparecían revisiones formales. No se fabrican revisiones ni autoría.
- **GitHub Actions:** los últimos trabajos no iniciaron pasos por bloqueo de
  facturación de la cuenta. Resolverlo corresponde al propietario; después ejecutar
  la CI sobre el commit final.
- **Correo externo:** reemplazar en el proveedor la credencial SMTP expuesta en una
  versión histórica antes de reutilizar esa cuenta; no se reescribió el historial.
- **Entrega y defensa:** registrar el repositorio y nombres completos en la
  plataforma; entregar las seis credenciales por medio privado y explicar código,
  permisos, ORM/ModelForms, sesión y recorrido de `transaction.on_commit` a Redis,
  WebSocket y la vista protegida de tabla. La pauta no pide un informe adicional.

No se asigna puntaje ni se afirma cumplimiento del 100% de la evaluación antes de
la demostración pública en AWS y la revisión real del equipo.
