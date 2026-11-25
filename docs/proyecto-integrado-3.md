# Proyecto Integrado 3

Esta rama incorpora el tubo de trabajo, el registro de acciones SGR, organizaciones comunitarias y el ajuste de metas por ausencias. Conserva las atenciones ciudadanas existentes y sus permisos por delegación.

## Instalación

Con las dependencias del proyecto instaladas y el entorno configurado:

```sh
python manage.py migrate
python manage.py asignar_delegado NOMBRE_DE_USUARIO
```

El último comando se ejecuta únicamente para el funcionario designado como delegado. Requiere una cuenta activa con delegación y rol Delegado Municipal o Coordinador. La atribución permite informar felicitaciones, registrar ausencias y configurar metas; no modifica el rol de acceso. La administración técnica también dispone de esas funciones. Las migraciones incorporan los permisos de los módulos nuevos a Coordinador, Delegado Municipal, Operador / Funcionario y Consultor sin restablecer los permisos personalizados de los módulos existentes. Consultor solo consulta y Cliente sigue accediendo únicamente a su portal. La atribución especial de delegado se asigna explícitamente. El comando opcional `sincronizar_roles` restablece los permisos predeterminados completos; úsalo solo si ese es el resultado deseado.

Las actividades se atribuyen al funcionario de la delegación correspondiente. Para informar una actividad de otra delegación, una cuenta con atribución de delegado debe seleccionar un funcionario de esa delegación. Las cuentas globales eligen primero la delegación; los formularios ofrecen únicamente sus relaciones y al guardar vuelven a validar ese ámbito. Al seleccionar al funcionario y su cargo se acota la lista de ítems vigentes.

En Usuarios se asigna el cargo municipal del funcionario. En Resultados SGR, el delegado configura la cantidad, el ponderador y el cargo de cada ítem. Los ítems sin cargo son comunes. Un ítem con cargo solo participa en el resultado de funcionarios con ese cargo asignado. Los cargos representan funciones municipales y son independientes de los roles de acceso.

## Tubo de trabajo

`/tubo/` presenta Ingresado, Pendiente, En proceso y Realizado. Cada tarjeta muestra solicitante, responsable, apoyo, compromiso y enlace al detalle. Puede vincular una atención ciudadana y una organización de la misma delegación. La gestión realizada se tacha y permanece consultable. Los totales incluyen todos los registros vigentes; cada columna muestra hasta 100 tarjetas y ofrece el listado completo cuando supera ese número.

Las tarjetas con permiso de edición se pueden arrastrar al siguiente estado disponible. Al soltar, un diálogo permite agregar una observación o cancelar; confirmar envía el formulario POST existente. Los botones se conservan para teclado y dispositivos táctiles. Los estados terminales y las cuentas de solo lectura no ofrecen arrastre. El resumen muestra total, tasa de resolución y vencidos; los conteos por estado aparecen en las columnas. Debajo se presenta el avance por colaborador en una tabla con desplazamiento horizontal interno cuando es necesario.

Al ingresar el RUT de una cuenta municipal activa se informa su nombre, cargo, delegación y funciones. Las cuentas Cliente no se identifican como funcionarios. El solicitante identificado aparece también en la tarjeta; si su cargo es Delegado, la gestión se marca como otra gestión y se excluye de la puntuación. Las altas del tubo exigen teléfono. El territorio admite texto libre y ofrece las sugerencias de la delegación y los valores ya registrados, sin repetirlos por diferencias de espacios o mayúsculas.

Los cambios de estado requieren POST con CSRF, permiso de edición y el estado de origen vigente. Una solicitud repetida o un editor desactualizado no avanza dos etapas. Los registros de otra delegación devuelven 404. El tablero se actualiza al recargar o cambiar un estado; no incorpora difusión WebSocket propia.

`/cartas/tablero/` conserva los estados En proceso, Aprobada, Finalizada y No aplica, con arrastre y botones sujetos a sus transiciones permitidas. Ambos tableros registran autor, estado anterior y nuevo, fecha y observación, y destacan compromisos vencidos, próximos a vencer y cierres fuera de plazo. Las reglas y límites se describen en [Seguimiento de cartas y gestiones](tablero-canvas.md).

## Registro y puntuación

`/sgr/` permite consultar año, trimestre y funcionario. `/sgr/actividad/` registra acciones. Los diez puntos del nuevo requerimiento se aplican así:

1. El indicador «El solicitante es el delegado» clasifica la actividad SGR como otra gestión, sin puntaje. En el tubo, el RUT identifica al solicitante y conserva su cargo; las solicitudes del delegado se excluyen del indicador del tubo.
2. Las actividades sin nombre o teléfono del usuario no son puntuables. Las altas del tubo exigen teléfono; los registros históricos incompletos siguen contando como ingresados, pero no como realizados para calcular el puntaje. Así, omitir datos no mejora la tasa. El estado operativo Realizado y la tasa de resolución del tablero siguen mostrando el seguimiento de las gestiones, aunque alguna no sea puntuable.
3. Máximo siete actividades por funcionario y fecha de actividad; también se limita a siete ingresos por funcionario en el día actual, aunque correspondan a distintas fechas. La comprobación se serializa con bloqueo de la cuenta en MySQL.
4. El lunes admite la semana anterior; desde el martes solo admite fechas desde el lunes de la semana actual. No admite fechas futuras. El calendario usa America/Santiago.
5. El indicador «La acción fue realizada» distingue la ejecución de sus coordinaciones previas. Las coordinaciones se registran sin puntaje.
6. El motivo de puntaje de cada registro se presenta en el informe. Marcar una acción como ejecutada sigue siendo una declaración del funcionario, no una verificación automática de su realización.
7. Los ítems de cantidad calculan acciones válidas / meta ajustada y los del tubo comparan su tasa de soluciones con la tasa meta. Cada ítem tiene tope de 120%. El resultado final del funcionario, después de felicitaciones y reclamos, tiene un límite independiente de 150% según la hoja RECLAMOS de la matriz.
8. Una felicitación necesita referencia al respaldo formal recibido por el delegado y debe ser informada por una cuenta con la atribución de delegado de la misma delegación. El delegado puede registrarla para el funcionario responsable; un gestor no puede aprobarse su propio respaldo sin esa atribución. No cuenta además como acción del ítem: se aplica como bonificación del resultado final.
9. `/sgr/ausencia/` permite al delegado registrar días libres, vacaciones, días administrativos, licencias, emergencias y días compensatorios (hoja SEMAFORO). La meta se prorratea por días de lunes a viernes del trimestre, descontando ausencias. Los intervalos superpuestos no duplican descuentos. No se presume un calendario de feriados no suministrado. Una meta ajustada a cero se presenta como no aplicable.
10. El informe muestra el promedio ponderado de los ítems del funcionario y el promedio de los resultados disponibles del equipo de su delegación. Cada ítem común se aplica a cada funcionario. Los ponderadores se normalizan por su suma; no se suman porcentajes entre personas.

Los ítems distinguen metas de cantidad y de tasa. En el indicador del tubo, la meta es una tasa porcentual (por ejemplo, 80%), no una cantidad de acciones. Cada felicitación válida suma diez puntos porcentuales al resultado final, con un máximo de tres; cada reclamo descuenta veinte puntos. El resultado final queda entre 0% y 150%. La configuración de metas es la vigente al consultar; no representa una versión histórica congelada por trimestre.

## Organizaciones

`/gestion/organizaciones/` mantiene familia, subfamilia, domicilio, socios, fechas y registros legales. La importación acepta el formato de ocho columnas de la base JJVV suministrada:

```sh
python manage.py importar_organizaciones "RUTA_A_LA_BASE.xlsx" --delegacion ID --territorio "TERRITORIO EXACTO"
python manage.py importar_organizaciones "RUTA_A_LA_BASE.xlsx" --delegacion ID --territorio "TERRITORIO EXACTO" --aplicar
python manage.py importar_organizaciones "RUTA_A_LA_BASE.xlsx" --todas
python manage.py importar_organizaciones "RUTA_A_LA_BASE.xlsx" --todas --aplicar
```

Sin `--aplicar`, el comando simula y revierte las escrituras. Con `--delegacion` y `--territorio` aplica un territorio exacto a la delegación indicada. Con `--todas` usa las correspondencias explícitas de la base JJVV: CIAS a Las Compañías, CENTRO a Centro, PAMPA a La Pampa, RURAL a Rural, ANTENA y ALFALFARES a La Antena - La Florida, y AV DEL MAR a Avenida del Mar. Exige esas delegaciones activas; las filas sin territorio o sin correspondencia se informan y no se asignan por suposición.

La importación omite nombres existentes en la delegación, incluidos los archivados, y no sobrescribe revisiones. La clasificación inicial por nombre es provisional y todas las organizaciones ingresan sin verificar. Los registros de personalidad jurídica compartidos por organizaciones distintas se informan para revisión; no se eliminan automáticamente. La base suministrada no contiene RUT de personas ni una nómina de presidentes o tesoreros: el aviso de funcionario usa los perfiles de las cuentas municipales. Los archivos originales y los datos personales de los adjuntos no se incluyen en Git.

## Validación original de la rama

Se aplicaron las migraciones sobre SQLite de desarrollo y se verificaron el tablero y el informe en navegador con diez gestiones ficticias (3 ingresadas, 1 pendiente, 1 en proceso y 5 realizadas).

Con `USE_SQLITE=true`, `DJANGO_DEBUG=true` y las variables Django de desarrollo:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q --ignore=tests_django/test_concurrency.py --ignore=tests_django/test_realtime.py -k "not parallel_creations"
```

Resultado: 100 pruebas aprobadas. La suite completa necesita MySQL y Redis: las pruebas existentes de concurrencia no son válidas con bloqueos de SQLite y las de eventos no pueden conectarse a Redis en este equipo. Esas pruebas deben ejecutarse en el entorno de integración del proyecto antes de desplegar. Esta rama no modifica ni despliega la instancia existente.

## Integración con main: 17 de noviembre de 2026

Se integró la rama sobre `main` conservando la consulta ciudadana por correo, los roles municipales y el selector de delegaciones. Las migraciones de unión conservan las dos líneas de historial. La migración de permisos agrega únicamente las atribuciones de los módulos nuevos, sin restablecer las personalizaciones existentes. Se corrigieron la asignación del funcionario responsable, las relaciones de los formularios globales y la validación de actividades fuera de la delegación del funcionario.

El tablero y los resultados reutilizan la identidad municipal vigente: colores, tipografía, encabezados, botones, filtros y navegación activa. Las capturas locales se guardan en `output/browser/integrado/`, fuera de Git.

Verificación realizada con Python 3.14, MySQL 8.4, Redis y Mailpit locales sobre una base aislada:

- `python -m pytest tests_django -q`: **159 pruebas aprobadas**, sin exclusiones.
- Pruebas compartidas de RUT: dos Python y dos JavaScript aprobadas.
- `makemigrations --check --dry-run`, `check --deploy --fail-level WARNING` con configuración segura y `collectstatic --noinput`: correctos.
- Navegador: `check_integrado`, `check_design`, `check_delegation_roles`, `check_client_readonly`, `check_flows` y `check_public_consultation`: aprobados. Formularios y pantallas a 320, 375, 768 y 1280 píxeles; sin errores JavaScript en los módulos nuevos.
- Actualización desde el esquema previo de `main`: se conservaron registros, metas, correo, hash de consulta privada y permisos personalizados. Los permisos de los módulos nuevos se incorporaron correctamente.

`check_integrado.py` realiza comprobaciones de lectura sobre el servidor local y requiere las cuentas demo y `.private/superadmin.json`. Esta validación acredita el entorno local; no constituye un despliegue ni un resultado de GitHub Actions.

## Matriz SGR completa: 17 de noviembre de 2026

Se incorporaron las hojas de la matriz que faltaban:

- **RECLAMOS.** `/sgr/reclamo/` permite al delegado registrar reclamos escritos (WhatsApp, correo o libro de observaciones) por mala atención de un funcionario. Cada reclamo descuenta 30% del resultado final (ver «Reglas decididas»). Cada felicitación válida suma 10%, con un máximo de tres; ya no se cuenta como acción del ítem. El resultado final queda entre 0% y 150%; cada ítem conserva su tope de 120%. Si un funcionario acumula reclamos en tres trimestres seguidos, el informe muestra «Informar a RRHH».
- **SEMÁFORO y RESUMEN.** `/sgr/` muestra, por funcionario de la delegación, el objetivo al día de hoy (días disponibles transcurridos sobre los días disponibles del trimestre; las ausencias ya ajustan la meta y no se descuentan dos veces), el semáforo (verde si cumple el objetivo, naranjo desde 60% del objetivo, rojo bajo ese umbral), el último ingreso, los días sin ingresar, el número de ingresos y los ingresos diarios.
- **GES SEG.** Nuevo cargo «Gestor de seguridad ciudadana».
- **Hojas por cargo.** `python manage.py cargar_matriz_sgr --delegacion ID [--aplicar] [--desactivar-comunes]` crea los ítems, metas y ponderadores de G SOC, T OC, AP ADM, COOR DISERCO, PLAN y CON y GES SEG. Sin `--aplicar` solo simula. `--desactivar-comunes` deja inactivos los ítems sin cargo de esa delegación.
- **Soluciones al ingreso al tubo.** Los ítems tienen tipo de indicador. El indicador del tubo mide gestiones realizadas / gestiones ingresadas del funcionario en el trimestre frente a la tasa meta (80%).

Emergencia se carga con meta 0 (no aplica) hasta que el delegado la configure cuando ocurra.

## Matriz revisada (3er trimestre): 25 de noviembre de 2026

- **SALON, resultado de la delegación.** `/sgr/` muestra, bajo el resultado individual, el cumplimiento ponderado de la delegación con los ponderadores de la hoja SALON (suman 1,0). Cada fila suma el avance y la meta ajustada de todos los funcionarios del cargo; «Informes» y «Operativos» de DISERCO agrupan dos ítems de su hoja. Cada fila tiene tope de 120% (punto 7 del correo). «Soluciones de ingresos al tubo» compara el porcentaje realizado de la delegación con 80%, y «Pendientes en tubo menor a 10%» vale 100% hasta 10% de gestiones en estado Pendiente, 50% hasta 50% y 0% sobre eso. Ambos excluyen las solicitudes del delegado (punto 1), y una gestión realizada sin nombre y teléfono no suma (punto 2). «Emergencia» vale 100% si hubo emergencias atendidas y no aplica si no hubo. Las filas sin datos (sin funcionarios del cargo, sin ítem o sin gestiones) no se ponderan; la página informa el peso considerado. El gestor de seguridad ciudadana se evalúa aparte, como en la hoja (bloque G SEGUR).
- **LISTA, catálogo social.** `python manage.py cargar_catalogo_social (--delegacion ID | --todas) [--aplicar]` crea los tipos «Informes sociales» (aporte económico, aporte material, institución) y «Gestión de subsidios» (IPS, PGU, SUF, SAP). Compara nombres sin distinguir mayúsculas ni tildes y no duplica ni reactiva tipos archivados. Sin `--aplicar` solo simula.
- **Actividades.** Campos opcionales «Acción realizada» (columna ACCIÓN de T OC y DETALLE de AP ADM), «Derivado a» (AP ADM) y «Tipo de gestión DISERCO» (lista de la hoja COOR DISERCO, solo para el coordinador de servicios comunitarios). No cambian el puntaje.
- **Datos de demostración.** `python manage.py archivar_relleno_demo [--aplicar]` archiva los ítems inactivos «… meta territorial NN» que crea `seed_demo`. Los que tienen actividades se mantienen.


## Reglas decididas a partir de la matriz: 25 de noviembre de 2026

Cada decisión se tomó leyendo las fórmulas de la planilla «3ER COMPAÑÍAS MATRIZ SGR TRIMESTRE 2026 REV»:

- **Verificación de actividades.** En todas las hojas `resultado = unidad × verificador válido`, y el verificador vale 1 o 0. Los únicos valores 100 están en una fila de prueba de cada hoja; explican totales imposibles (G SOC 1: 248 atenciones) y no se implementan como multiplicador. Cada actividad muestra su código (`ÁREA-MMDD-número`, por ejemplo `SOC-0721-15`, con las áreas APA, COS, COM, SOC, PYG y SEG de la columna AREA) para nombrar la foto. «Tiene foto de respaldo» reemplaza la columna IMAGEN VERIF. El delegado puede marcar una actividad como no válida, con motivo, desde Resultados SGR, y entonces no suma puntaje. Por defecto es válida, como en la planilla.
- **Ingreso al tubo.** Las filas con INGRESO A TUBO = SÍ se copiaban a mano en la hoja TUBO (la solicitud de maquinaria pesada de COOR DISERCO es la gestión 8 del TUBO). Al registrar una actividad o un caso social, la casilla «Ingresar al tubo de trabajo» crea la gestión en estado Ingresado y la vincula. Exige nombre y teléfono, y si el solicitante es el delegado la gestión queda como otra gestión.
- **Casos sociales (hojas G SOC).** Cada fila es un caso con hasta tres gestiones que suman en sus ítems. El módulo «Casos sociales» registra el ingreso, si requiere visita, la fecha programada y las devoluciones del informe. Las fechas de visita, informe y beneficio salen de las actividades vinculadas al caso. Los plazos de la fila 19 (10 días a la visita programada, visita sin diferencia, 4 días al informe, 4 días al beneficio y 20 días en total) y los reingresos se muestran como información, porque en la planilla no ponderan: las filas 9 a 13 quedan fuera del total I14.
- **Reclamos: 30%.** Once de las trece hojas por funcionario calculan con −0,3 y el reclamo registrado en la hoja RECLAMOS puntúa −0,3. El −0,2 del encabezado y de las hojas COOR DISERCO y G SOC 1 corresponde a la plantilla anterior. Se cambia en `DESCUENTO_RECLAMO`.
- **Seguridad ciudadana.** SALON (bloque G SEGUR) toma el avance de GES SEG y lo puntúa con sus propias metas (6, 45, 12, 50, 60 y 80% del tubo) y ponderadores. En GES SEG las celdas de cumplimiento H6 a H9 apuntan a filas equivocadas y el total I10 omite filas. «Salidas a terreno» queda con ponderador 0, solo informativo. `cargar_matriz_sgr --actualizar` aplica el cambio solo a los ítems que conservan los valores anteriores.
- **Metas individuales.** G SOC2 y G SOC3 ponderan distinto la atención (0,25) y el informe (0,20), G SOC5 tiene meta de beneficios 15 y T OC 3 conformación 10. SALON suma esa meta de 10, así que son ajustes deliberados por persona. El delegado los configura en Resultados SGR con «Meta de …», sin tocar la meta del cargo.
- **Cierre semanal en el tubo.** El punto 4 del correo habla de «gestiones»: las solicitudes nuevas del tubo solo admiten fechas desde el lunes de la semana abierta. Las gestiones ya registradas se pueden seguir editando.
- **Catálogo social.** Además de la hoja LISTA se cargan los tipos de las listas desplegables de G SOC (Derivaciones, Otras gestiones sociales, Entrega de emergencia y la exención de aseo en subsidios), asociando solo pares evidentes.
