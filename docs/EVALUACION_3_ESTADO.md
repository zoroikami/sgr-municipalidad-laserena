# Evaluación III: estado verificable

Fecha: 6 de noviembre de 2026, America/Santiago.

## Implementación local

El SGR funciona con Django 5.2.19, MySQL 8.4, Channels/Redis y Daphne. Incluye
las apps internas `cuentas` y `gestion`, migraciones, templates heredados y los
dos CRUD evaluados: Ítems y Metas / Atenciones ciudadanas.

Se implementaron permisos Django por acción, ámbito por delegación, portal por
propietario, archivado con `deleted_at`, consultas y estado en sesión, exportación
completa, validaciones de servidor, foto privada con Croppr, recuperación por
enlace/token y páginas de error con códigos HTTP reales. Los catálogos y la
gestión de cuentas se mantienen con la política de alcance documentada.

## Verificaciones ejecutadas

| Comprobación | Resultado observado |
| --- | --- |
| `pytest tests_django` | 53 pruebas aprobadas sobre MySQL y Redis reales, incluidas regresiones de concurrencia en ambos CRUD |
| Pruebas históricas Python | 22 aprobadas |
| Pruebas históricas Node | 48 aprobadas |
| Migraciones | Aplicadas en MySQL; `makemigrations --check --dry-run` sin cambios |
| `DJANGO_DEBUG=false manage.py check --deploy --fail-level WARNING` | Sin errores ni advertencias |
| `collectstatic` | 151 archivos recopilados |
| Semillas | 6 delegaciones + 360 metas + 30 tipos + 90 subatenciones + 1.800 atenciones = 2.286 registros de negocio |
| Segunda carga | Sin duplicados, sin reiniciar contraseñas ni sobrescribir ediciones |
| Imagen Docker | Construida localmente; usuario de ejecución `sgr` sin root; se comprobó que no contiene `deploy/tls`, `.env` ni `.private` |
| Nginx | Sintaxis válida usando un certificado efímero exclusivamente local |
| Diagrama | Mermaid validado en Chromium; SVG generado y revisado |
| JavaScript y copy | Sintaxis correcta; guard es-CL: 27 archivos, cero errores/advertencias |

Los tests incluyen accesos directos y POST manipulados, lectores sin escrituras,
editor sin archivado, administrador limitado sin Django Admin, IDs/FK ajenos,
clientes en la misma delegación, archivos falsificados/truncados/grandes,
exportación fuera de la página actual y como texto seguro, tokens de recuperación,
sesiones revocadas y WebSocket posterior al commit, sin evento al hacer rollback.

La revisión final detectó y se corrigieron dos problemas: la exclusión de
certificados privados del contexto Docker y una carrera entre edición y
archivado. Los dos CRUD ahora obtienen y guardan la fila bajo el mismo bloqueo
transaccional que el archivado. Las regresiones reproducen el intercalado con
conexiones MySQL independientes y comprueban que el registro sigue archivado.

### Navegador real

`tests_browser/check_flows.py` completó el recorrido con seis contextos Chromium
independientes y los siguientes resultados:

- Editor A guardó y lector A cambió su tabla sin F5; un marcador en la página
  se conservó. Lector B no recibió evento ni contenido de A.
- Al cambiar un registro para que dejara de cumplir la búsqueda del lector,
  desapareció de su tabla y se conservó el filtro.
- Se mostró la desconexión sin afirmar que los datos continuaban actualizados.
- Un formulario inválido mantuvo datos y errores dentro del modal. Cancelar
  SweetAlert2 no envió ninguna solicitud de archivado.
- Navegar de módulo y regresar restauró búsqueda, tamaño y página. Se revisaron
  capturas a 375, 768 y 1280 píxeles, sin desbordamiento horizontal de la página.
- Login por Enter, recorrido del modal con Tab y cancelación por Enter se
  comprobaron en Chromium. Se añadió retorno de foco al primer/último control
  para impedir que Tab saliera del diálogo hacia los controles del navegador.
- Los dos clientes mostraron atenciones propias distintas y rechazaron el
  detalle del otro cliente y las rutas administrativas.
- Se guardó un recorte reconocible de una imagen de dos colores. La imagen
  persistida contenía únicamente los píxeles seleccionados, se mantuvo al recargar
  y no cambió al cancelar una segunda selección. La foto ajena respondió 404.
- Django envió un correo SMTP a Mailpit; se abrió el enlace, se cambió la
  contraseña, se rechazaron la anterior y el token usado y se restauró la clave
  privada mediante el cambio con contraseña actual. Logout protegió de nuevo
  el portal.

`tests_browser/check_crop.py` reprodujo y verificó la corrección de un problema
detectado en revisión independiente: los controles programáticos de Croppr
podían salir de la imagen o reducirse a cero. Después de limitar geometría y
tamaño, pasaron movimientos repetidos, ampliación/reducción y generación final
en Chromium.

Las capturas están en `output/browser/` local, excluido de Git. El archivo
SQLite anterior se respaldó de forma coherente en `.private/backups/` y no se
modificó ni se importó automáticamente a la base nueva.

## Estado frente a la pauta

| Criterio grupal | Evidencia local / límite |
| --- | --- |
| 5. AWS, semillas y cuentas | Semillas/cuentas verificadas; imagen y configuración listas. AWS pendiente de instancia y acceso |
| 6. Integración, orden y sesión | Ambos CRUD, modales, archivado, consultas y restauración comprobados |
| 7. Validaciones y archivos | ModelForms, reglas, formatos, tamaño y contenido de imágenes comprobados |
| 8. Permisos y protección | Permisos y ámbito en vistas, relaciones, fotos, portal, Excel, fragmentos y consola técnica comprobados |
| 9. WebSocket | Flujo A/A y aislamiento B comprobados localmente con Redis; falta repetirlo en AWS |
| 10. Sesiones, perfil y recuperación | Flujo completo con SMTP/Mailpit comprobado localmente; falta correo en AWS |
| 11. Excel | Ambos módulos, todos los resultados filtrados, sin archivados ni datos ajenos |
| 12. Git y PR | Desarrollo en rama feature; requiere integración y revisión real de compañeros, con aportes propios por integrante |
| 13. Croppr | Recorte final, persistencia, cancelación y propietario comprobados |
| 14. Portal cliente | Dos clientes de A, listados/detalles distintos y rechazo cruzado comprobados |
| 15. Navegación y errores | Recorridos, legibilidad, teclado y 400/403/404/500 con DEBUG=False comprobados |

La revisión independiente final aprobó el alcance local implementado y la calidad
del código después de comprobar las correcciones. No quedaron hallazgos
importantes abiertos; AWS y revisión de compañeros siguen pendientes.

## Pendientes externos

1. Identificar la instancia EC2 y la URL o dominio, y disponer de acceso configurado.
   No hay credenciales AWS/SSH configuradas en este equipo ni una conexión EC2
   utilizable en las integraciones consultadas. Se solicitó esta información al
   usuario. La búsqueda de plugins ofreció analítica AWS, que no administra EC2.
2. Configurar certificado y SMTP/buzón accesible en AWS; desplegar el commit
   revisado de `main` y repetir los recorridos desde una dirección pública.
3. Revisiones y aportes funcionales reales de cada integrante. Las revisiones de
   agentes no acreditan participación académica ni sustituyen la de un compañero.
4. Reemplazar en el proveedor la credencial SMTP que estaba incrustada en la
   versión anterior. Se retiró del código actual, pero no se reescribió el historial.

Estos pendientes impiden afirmar cumplimiento total de la evaluación o asignar
puntaje. No se generó ni inventó una evidencia de despliegue AWS.
