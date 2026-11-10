# Evaluación Sumativa III · TI3041: diagnóstico y propuesta

Fecha: 6 de noviembre de 2026.

Estado: propuesta aprobada por el usuario e implementada en la rama de trabajo.
Este diseño no acredita por sí solo cumplimiento ni despliegue. Los resultados
y pendientes externos están registrados en `EVALUACION_3_ESTADO.md`.

Fuente: `Evaluacion_Sumativa_3_Back_End_TI3041.pdf`, facilitado desde Downloads
(10 páginas). Los requisitos de esta evaluación sustituyen las decisiones
incompatibles de la segunda entrega.

## 1. Decisión de arquitectura

Se recomienda migrar el SGR a Django con MySQL, conservando su identidad
institucional y sus funciones operativas. MySQL corresponde al motor definido
en `base_datos/database_sgr.sql`; actualmente ese script no es el motor usado
por `server.py`, que utiliza SQLite. La base nueva se gestionará mediante
migraciones de Django. No se ejecutará el script histórico destructivo sobre
datos existentes.

Alternativas consideradas:

| Alternativa | Ventaja | Consecuencia |
| --- | --- | --- |
| Migración incremental a Django y MySQL, recomendada | Una aplicación final; permite conservar la identidad y los recorridos existentes | Hay que reemplazar autenticación, persistencia y control de acceso |
| Aplicación Django independiente para la evaluación | Permite mantener intacta la aplicación anterior durante el desarrollo | Duplica cuentas y datos; obliga a resolver después la integración y el acceso público a la versión antigua |

Agregar funciones al servidor Python actual sin migrarlo no satisface el
requisito explícito de Django, MVT, ModelForm, grupos y Channels.

La aplicación Django será el punto de entrada final. Los prototipos y diagramas
anteriores se conservarán como antecedentes; los archivos históricos no se
servirán indiscriminadamente desde la raíz del repositorio. La versión anterior
podrá recuperarse mediante Git. La transición de datos existentes se hará con
respaldo y una importación separada, sin confundir registros reales con semillas.

## 2. Diagnóstico del repositorio

| Área | Evidencia actual | Trabajo necesario |
| --- | --- | --- |
| Framework y persistencia | `server.py`: HTTPServer, SQL manual y SQLite; no hay proyecto Django ni migraciones | Proyecto Django, ORM, apps internas, MySQL y migraciones |
| Interfaz | HTML, CSS y JavaScript de `evaluacion2/`; formularios y SweetAlert2 existentes | Templates heredados, formularios Django y modales Bootstrap funcionales |
| Modelos | Delegaciones, roles, usuarios, metas, tipos, subatenciones y atenciones | Relaciones reales y aislamiento por delegación; diagrama del modelo implementado |
| CRUD | Seis mantenedores; atenciones con ingreso y listado | Mantener los mantenedores y completar detalle, edición y archivado de atenciones |
| Autorización | Visibilidad y parte de los filtros controlados por el cliente; las rutas de negocio no aplican una política central de autorización | Grupos/permisos Django y consultas limitadas en todas las vistas |
| Contraseñas | La comparación actual usa valores de texto; recuperación mediante código | Hashes Django, validadores, cambio con clave actual y recuperación mediante enlace y token |
| Secretos | Hay credenciales incorporadas al código y contraseñas de demostración publicadas | Configuración por entorno, eliminación de valores publicados en la versión nueva y sustitución privada de las credenciales expuestas |
| Perfil | Foto propia asociada a una sesión; recorte personalizado con canvas | Nombre/correo editables, Croppr, multipart, MEDIA y validación real de imagen JPEG/PNG hasta 2 MiB |
| Consulta | Búsqueda y paginación en JavaScript; estado mantenido en el controlador | Consultas del servidor, orden permitido y estado por módulo en sesión Django |
| Exportación | Excel generado en el navegador mediante SheetJS | Excel generado desde la misma consulta autorizada y filtrada del servidor |
| Tiempo real | No existe Channels ni WebSocket de CRUD | ASGI, Redis, grupos por delegación y actualización parcial de la tabla |
| Clientes | Sin rol ni portal de cliente final | Dos clientes de la misma delegación, con listado y detalle propios |
| Datos | Semillas pequeñas durante `init_db()` | Comando idempotente con más de 2.000 registros de negocio |
| AWS | Script para el servidor anterior; README sin dirección pública verificable | Despliegue ASGI, MySQL persistente, estáticos, MEDIA, correo y HTTP/WebSocket |
| Git | Checkout inicial en `main` | Desarrollo en `feature/...`, integración por PR y revisión real de otro integrante |

Las pruebas existentes permiten verificar comportamientos de la versión previa,
pero no acreditan permisos Django, Channels, MySQL ni los criterios nuevos.

## 3. Estructura propuesta

- `config/`: configuración por entorno, rutas, ASGI y manejo de errores.
- `cuentas/`: login, logout POST, perfil propio, Croppr, cambio y recuperación de
  contraseña, grupos y gestión acotada de cuentas.
- `gestion/`: delegaciones, catálogos, metas, atenciones, consultas, exportaciones,
  portal de clientes y consumidores WebSocket.
- `templates/`: base heredada municipal, pantallas por módulo, fragmentos de tabla
  y páginas 400, 403, 404 y 500.
- `static/`: recursos municipales y dependencias de interfaz versionadas.
- `deploy/`: configuración para Nginx y servicio ASGI sin usuario root, más guía
  de instalación y verificación en EC2.

Los componentes tendrán pruebas de integración HTTP y WebSocket. Las
dependencias se fijarán en versiones exactas al implementar, después de comprobar
compatibilidad entre Django, Channels, servidor ASGI, MySQL y Pillow.

## 4. Modelo de dominio y ámbitos

Modelos propios principales:

| Modelo | Atributos y relaciones principales |
| --- | --- |
| Delegacion | Código único, nombre, dirección, comuna, estado, created_at |
| Perfil | Usuario 1:1, delegación FK, RUT, foto; rol efectivo gestionado mediante grupos Django |
| TipoAtencion | Delegación FK, código, nombre, descripción, estado y fechas |
| SubAtencion | Delegación FK, tipo FK, código, nombre y estado |
| ItemMeta | Delegación FK, código automático, nombre, descripción, unidad, cantidad, estado, created_at y deleted_at |
| Atencion | Delegación FK, tipo FK, subatención FK, cliente FK opcional, responsable FK, folio automático, solicitante, descripción, estado, created_at y deleted_at |

Multiplicidades: una delegación tiene muchos perfiles, tipos, subatenciones,
metas y atenciones; un tipo tiene muchas subatenciones; una subatención puede
estar vinculada a muchas atenciones; un cliente puede tener muchas atenciones;
cada atención tiene un responsable. Los diagramas definitivos deberán reflejar
las migraciones realmente generadas.

Cada cuenta de evaluación tendrá una única delegación. El ámbito A será Centro
(`DEL01`) y el B Las Compañías (`DEL02`). La aplicación no aceptará una delegación
enviada por el navegador como autorización para cambiar de ámbito.

Los clientes 1 y 2 pertenecerán ambos a Centro: esto permite demostrar que el
portal filtra por propietario, además de filtrar por delegación.

## 5. Política de permisos

| Cuenta | Permisos | Restricciones |
| --- | --- | --- |
| Administrador A | Consultar, exportar, crear, editar y archivar datos de A; gestionar cuentas de prueba de A con roles predefinidos | Sin datos de B; no superusuario; no asignar privilegios técnicos ni alterar permisos globales |
| Editor A | Consultar, exportar, crear y editar datos de A | Sin archivado, eliminación, gestión de cuentas ni datos de B |
| Lector A | Consultar y exportar datos de A | Sin escrituras ni datos de B |
| Lector B | Consultar y exportar datos de B | Sin escrituras ni datos de A |
| Cliente 1 | Consultar listado/detalle de sus atenciones; editar su perfil/foto y contraseña | Sin módulos administrativos ni datos del Cliente 2 |
| Cliente 2 | Consultar listado/detalle de sus atenciones; editar su perfil/foto y contraseña | Sin módulos administrativos ni datos del Cliente 1 |

Podrá existir un superusuario técnico adicional para mantenimiento institucional;
no contará como administrador A. El mantenedor global de roles quedará reservado
a ese usuario técnico. Si se habilita Django Admin, quedará restringido al
superusuario técnico; las seis cuentas de revisión no tendrán acceso.

Las vistas verificarán primero permiso de acción y después buscarán el objeto
en una consulta autorizada. Un usuario autenticado sin permiso recibirá 403;
un identificador inexistente o ajeno, 404. Las mismas reglas se aplicarán a
selectores, formularios manipulados, exportaciones y consultas de actualización.

## 6. Dos CRUD evaluados: Ítems y Metas / Atenciones

Ambos tendrán listado, detalle, creación, edición y archivado persistidos.
Se implementará `deleted_at` en ambos: los archivados quedarán excluidos de
listados, detalles habituales, relaciones seleccionables y exportaciones.

Creación y edición utilizarán ModelForm y modal Bootstrap. Un POST inválido
volverá a mostrar el modal con valores válidos y errores asociados a sus campos;
no escribirá datos ni emitirá eventos de éxito. Guardar mostrará el resultado
real; cancelar no enviará cambios.

El archivado requerirá confirmación SweetAlert2 y POST con CSRF; cancelar o
visitar una URL mediante GET no modificará registros. Se mostrarán mensajes
comprensibles ante relaciones protegidas.

Reglas de negocio mínimas, además de campos requeridos y formatos:

1. Evitar nombres/códigos duplicados dentro del ámbito correspondiente, con
   restricciones compatibles en base de datos y errores de formulario.
2. La cantidad de las metas no podrá ser negativa. Se conservará la conducta
   vigente: nuevas metas con cantidad automática 100; edición sin aceptar una
   cantidad manipulada por el navegador. Una regla nueva de cálculo requerirá
   una petición posterior, no está incluida en esta evaluación.
3. La subatención debe corresponder al tipo elegido y ambas relaciones deben
   pertenecer a la delegación autorizada y estar disponibles.
4. Un cliente asignado a una atención debe pertenecer a esa delegación y tener
   el rol Cliente. El responsable y la delegación se obtendrán en el servidor.
5. RUT normalizado y validado por módulo 11, reutilizando la lógica existente.

Los códigos y folios se generarán de manera segura ante concurrencia; un
formulario inválido no creará un registro parcial. `created_at` será inmutable
durante la edición y distinto de la fecha de actualización.

## 7. Listados, sesión y Excel

Cada módulo tendrá búsqueda por al menos dos campos, filtro de negocio y
ordenamiento ascendente/descendente de al menos dos columnas mediante una lista
explícita de valores permitidos. Ejemplos: código/nombre/estado en metas;
folio/solicitante/estado y tipo en atenciones.

El orden inicial será `-created_at, -id`. Se admitirán tamaños 5, 15 y 30.
Página, tamaño, búsqueda, filtro y orden se guardarán por separado para cada
módulo en la sesión Django. Cambiar búsqueda o filtros llevará a página 1;
parámetros inválidos y páginas fuera de rango se normalizarán. Abrir detalles,
editar, cancelar o visitar otro módulo conservará la consulta anterior.

Los dos Excel incluirán todos los resultados de la consulta filtrada y
autorizada, sin limitarse a la página actual. Tendrán encabezados legibles y
excluirán archivados, credenciales, tokens e información de autenticación.

## 8. Sesiones, recuperación y perfil

Se utilizarán autenticación y sesiones de Django, logout POST con CSRF,
protección de vistas privadas y validadores de contraseñas. La recuperación
enviará un enlace con token a través de SMTP o un buzón de pruebas accesible;
la respuesta de solicitud será genérica para correos existentes e inexistentes.
Se comprobarán expiración, token inválido y rechazo del enlace ya utilizado.

El perfil solo permitirá nombre, correo y foto del usuario autenticado, sin
aceptar cambios de rol, permisos, delegación ni identificadores de otra cuenta.
El cambio de contraseña pedirá clave actual y confirmación de la nueva.

Croppr seleccionará el recorte; canvas generará el archivo final y permitirá
previsualizarlo antes del guardado multipart. Pillow comprobará el contenido,
formato JPEG/PNG y tamaño máximo de 2 MiB en el servidor. Se validarán también
archivos truncados o falsificados. Cancelar mantendrá la foto anterior. La foto
almacenada se servirá mediante una vista protegida que respete los permisos;
un directorio MEDIA público no deberá permitir consultar fotos ajenas.

## 9. WebSocket de negocio

Channels funcionará en ASGI con Redis como capa de canales, para permitir varios
procesos en AWS. Las conexiones exigirán sesión autenticada, permiso de lectura
y origen permitido. El servidor calculará el grupo desde la delegación del
perfil; el navegador no elegirá libremente a qué ámbito suscribirse.

Después de guardar o archivar una atención correctamente, `transaction.on_commit`
emitirá una notificación mínima al grupo autorizado. El lector A consultará
entonces un fragmento HTTP protegido y sustituirá solo la tabla y paginación,
respetando su estado actual. No habrá polling ni recarga completa. El lector B
no recibirá el evento de A. Los clientes no tendrán acceso al canal
administrativo; el portal funcionará con sus consultas HTTP por propietario.

La interfaz informará conexión, desconexión y errores. Un error al guardar no
emitirá una notificación de cambio exitoso. Si un registro deja de coincidir con
el filtro, desaparecerá al actualizar la tabla.

## 10. Semillas y seis cuentas

Distribución reproducible propuesta, sin contar usuarios, perfiles, sesiones,
permisos ni registros internos:

| Modelo de negocio | Total | Distribución |
| --- | ---: | --- |
| Delegacion | 6 | Delegaciones municipales del proyecto |
| ItemMeta | 360 | 60 por delegación |
| TipoAtencion | 30 | 5 por delegación |
| SubAtencion | 90 | 15 por delegación |
| Atencion | 1.800 | 300 por delegación |
| **Total** | **2.286** | Más de 50 registros en cada CRUD evaluado; ambos permiten más de una página de 30 en A y B |

Los clientes 1 y 2 tendrán 30 atenciones distintas cada uno en Centro, incluidas
en sus 300 atenciones, sin duplicar el total. Los demás solicitantes serán
ficticios. Nombres, fechas, tipos y estados variarán para probar consultas.

El comando usará identificadores estables y creación idempotente: una segunda
ejecución no duplicará datos ni reiniciará contraseñas o ediciones existentes.
Las contraseñas se proporcionarán mediante configuración privada o un archivo
local ignorado y protegido; no aparecerán en README, fixtures públicos ni Git.
El README contendrá alias, rol, ámbito, responsabilidades, límites y recorridos
con resultado esperado para las seis cuentas.

## 11. AWS y colaboración

El despliegue final utilizará EC2 con Nginx, un servicio ASGI sin root, MySQL y
Redis persistentes/configurados, estáticos recopilados y almacenamiento de fotos.
Se configurarán `DEBUG=False`, hosts/orígenes permitidos y secretos por entorno,
así como cookies y HTTPS acordes a la URL final. Nginx soportará Upgrade para
WebSocket y solo expondrá los recursos públicos previstos.

El README documentará desde cero: entorno, dependencias fijadas, variables,
MySQL, migraciones, semillas, correo, estáticos, MEDIA, inicio HTTP/WebSocket,
URL pública comprobada y commit desplegado. No se inventará una IP ni se
declarará AWS completado mediante una prueba exclusivamente local.

La aplicación no requiere contratar servicios nuevos para desarrollarse. Para
completar la evidencia de AWS harán falta acceso a la instancia/recurso elegido,
configuración de correo y una dirección pública. Su disponibilidad se comprobará
antes del despliegue; los secretos no se solicitarán en documentos públicos.

Los cambios se desarrollarán en ramas `feature/...` y se integrarán por PR. El
historial existente no se reescribirá para aparentar cumplimiento. Cada integrante
deberá aportar y revisar PR reales; no se inventarán revisiones ni autorías. La
entrega externa seguirá siendo enlace del repositorio y nombres de integrantes,
sin generar un informe adicional obligatorio.

## 12. Orden de implementación y aceptación

1. Crear rama de trabajo, registrar el estado inicial y respaldar SQLite antes
   de cualquier importación. Preparar Django/MySQL, apps, modelos, migraciones,
   configuración por entorno y permisos.
2. Implementar autenticación, recuperación, perfil y seis cuentas, con pruebas
   de sesión, manipulación de campos, tokens, validadores e imágenes.
3. Migrar mantenedores y completar los dos CRUD evaluados con ModelForm,
   modales, confirmaciones, archivado y validaciones de negocio.
4. Añadir consultas del servidor, restauración de sesión, Excel y portal por
   propietario. Probar permisos en URL y POST directos, relaciones ajenas y
   exportaciones completas.
5. Incorporar Channels/Redis y probar conexión autenticada, orígenes, aislamiento,
   notificación posterior a commit, ausencia de eventos tras rollback y
   actualización de tabla sin F5.
6. Añadir semillas idempotentes, diagrama coherente, páginas de error y guía de
   ejecución. Probar 400/403/404/500 con DEBUG=False en un entorno controlado.
7. Revisar en navegador los recorridos de las seis cuentas, teclado/foco,
   cancelaciones, persistencia del recorte y estado al cambiar de módulo.
8. Preparar PR y despliegue, verificar en AWS HTTP, WebSocket, correo, datos,
   imágenes y correspondencia del commit. Registrar únicamente evidencia
   obtenida y los pasos externos que sigan pendientes.

La matriz de comprobación final seguirá los criterios grupales 5 a 15 de la
rúbrica y conservará los flujos de los criterios individuales 1 a 4. No se
afirmará que se obtuvieron puntos académicos: los asigna el docente.
