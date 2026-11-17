# Proyecto Integrado 3

Esta rama incorpora el tubo de trabajo, el registro de acciones SGR, organizaciones comunitarias y el ajuste de metas por ausencias. Conserva las atenciones ciudadanas existentes y sus permisos por delegación.

## Instalación

Con las dependencias del proyecto instaladas y el entorno configurado:

```sh
python manage.py migrate
python manage.py asignar_delegado NOMBRE_DE_USUARIO
```

El último comando se ejecuta únicamente para el funcionario designado como delegado. Requiere una cuenta activa con delegación y rol Delegado Municipal o Coordinador. La atribución permite informar felicitaciones, registrar ausencias y configurar metas; no modifica el rol de acceso. La administración técnica también dispone de esas funciones. Las migraciones incorporan los permisos de los módulos nuevos a Coordinador, Delegado Municipal, Operador / Funcionario y Consultor sin restablecer los permisos personalizados de los módulos existentes. Consultor solo consulta y Cliente sigue accediendo únicamente a su portal. La atribución especial de delegado se asigna explícitamente. El comando opcional `sincronizar_roles` restablece los permisos predeterminados completos; úsalo solo si ese es el resultado deseado.

Las actividades se atribuyen al funcionario de la delegación correspondiente. Para informar una actividad de otra delegación, una cuenta con atribución de delegado debe seleccionar un funcionario de esa delegación. Las cuentas globales pueden cargar los formularios con todas las relaciones visibles; al guardar se validan nuevamente contra la delegación elegida.

En Usuarios se asigna el cargo municipal del funcionario. En Resultados SGR, el delegado configura la cantidad, el ponderador y el cargo de cada ítem. Los ítems sin cargo son comunes. Un ítem con cargo solo participa en el resultado de funcionarios con ese cargo asignado. Los cargos representan funciones municipales y son independientes de los roles de acceso.

## Tubo de trabajo

`/tubo/` presenta Ingresado, Pendiente, En proceso y Realizado. Cada tarjeta muestra solicitante, responsable, apoyo, compromiso y enlace al detalle. Puede vincular una atención ciudadana y una organización de la misma delegación. La gestión realizada se tacha y permanece consultable. Los totales incluyen todos los registros vigentes; cada columna muestra hasta 100 tarjetas y ofrece el listado completo cuando supera ese número.

Los cambios de estado requieren POST con CSRF, permiso de edición y el estado de origen vigente. Una solicitud repetida o un editor desactualizado no avanza dos etapas. Los registros de otra delegación devuelven 404. El tablero se actualiza al recargar o cambiar un estado; no incorpora difusión WebSocket propia.

## Registro y puntuación

`/sgr/` permite consultar año, trimestre y funcionario. `/sgr/actividad/` registra acciones. Los diez puntos del nuevo requerimiento se aplican así:

1. El indicador «El solicitante es el delegado» clasifica la actividad como otra gestión, sin puntaje.
2. Se pueden conservar registros incompletos, pero sin nombre o teléfono del usuario no son puntuables.
3. Máximo siete actividades por funcionario y fecha de actividad; también se limita a siete ingresos por funcionario en el día actual, aunque correspondan a distintas fechas. La comprobación se serializa con bloqueo de la cuenta en MySQL.
4. El lunes admite la semana anterior; desde el martes solo admite fechas desde el lunes de la semana actual. No admite fechas futuras. El calendario usa America/Santiago.
5. El indicador «La acción fue realizada» distingue la ejecución de sus coordinaciones previas. Las coordinaciones se registran sin puntaje.
6. El motivo de puntaje de cada registro se presenta en el informe. Marcar una acción como ejecutada sigue siendo una declaración del funcionario, no una verificación automática de su realización.
7. Cada ítem calcula acciones válidas / meta ajustada, con tope de 120%. Este límite del requerimiento nuevo prevalece sobre las referencias de 150% de la planilla del trimestre anterior.
8. Una felicitación necesita referencia al respaldo formal recibido por el delegado y debe ser informada por una cuenta con la atribución de delegado de la misma delegación. El delegado puede registrarla para el funcionario responsable; un gestor no puede aprobarse su propio respaldo sin esa atribución.
9. `/sgr/ausencia/` permite al delegado registrar días libres, vacaciones, días administrativos y licencias. La meta se prorratea por días de lunes a viernes del trimestre, descontando ausencias. Los intervalos superpuestos no duplican descuentos. No se presume un calendario de feriados no suministrado. Una meta ajustada a cero se presenta como no aplicable.
10. El informe muestra el promedio ponderado de los ítems del funcionario y el promedio de los resultados disponibles del equipo de su delegación. Cada ítem común se aplica a cada funcionario. Los ponderadores se normalizan por su suma; no se suman porcentajes entre personas.

Las metas continúan siendo cantidades enteras de acciones. La planilla también contiene indicadores de razón y otros cálculos, que requieren una definición específica antes de automatizarse. No se importan ni se reinterpretan esos indicadores como cantidades. Las felicitaciones válidas cuentan como una acción; no se agrega un bono porcentual adicional no especificado por el nuevo requerimiento. La configuración de metas es la vigente al consultar; no representa una versión histórica congelada por trimestre.

## Organizaciones

`/gestion/organizaciones/` mantiene familia, subfamilia, domicilio, socios, fechas y registros legales. La importación acepta el formato de ocho columnas de la base JJVV suministrada:

```sh
python manage.py importar_organizaciones "RUTA_A_LA_BASE.xlsx" --delegacion ID --territorio "TERRITORIO EXACTO"
python manage.py importar_organizaciones "RUTA_A_LA_BASE.xlsx" --delegacion ID --territorio "TERRITORIO EXACTO" --aplicar
```

El primer comando simula y revierte las escrituras. El segundo aplica la importación de ese territorio a la delegación indicada. No adivina correspondencias entre territorios y delegaciones. Omite nombres existentes, incluidos los archivados, y no sobrescribe revisiones. La clasificación inicial por nombre es provisional y todas las organizaciones ingresan sin verificar. Los archivos originales y los datos personales de los adjuntos no se incluyen en Git.

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

- **RECLAMOS.** `/sgr/reclamo/` permite al delegado registrar reclamos escritos (WhatsApp, correo o libro de observaciones) por mala atención de un funcionario. Cada reclamo descuenta 20% del resultado final. Cada felicitación válida suma 10%, con un máximo de tres; ya no se cuenta como acción del ítem. El resultado final queda entre 0% y 150%; cada ítem conserva su tope de 120%. Si un funcionario acumula reclamos en tres trimestres seguidos, el informe muestra «Informar a RRHH».
- **SEMÁFORO y RESUMEN.** `/sgr/` muestra, por funcionario de la delegación, el objetivo al día de hoy (días transcurridos del trimestre sin ausencias × porcentaje diario), el semáforo (verde si cumple el objetivo, naranjo desde 60% del objetivo, rojo bajo ese umbral), el último ingreso, los días sin ingresar, el número de ingresos y los ingresos diarios.
- **GES SEG.** Nuevo cargo «Gestor de seguridad ciudadana».
- **Hojas por cargo.** `python manage.py cargar_matriz_sgr --delegacion ID [--aplicar] [--desactivar-comunes]` crea los ítems, metas y ponderadores de G SOC, T OC, AP ADM, COOR DISERCO, PLAN y CON y GES SEG. Sin `--aplicar` solo simula. `--desactivar-comunes` deja inactivos los ítems sin cargo de esa delegación.
- **Soluciones al ingreso al tubo.** Los ítems tienen tipo de indicador. El indicador del tubo mide gestiones realizadas / gestiones ingresadas del funcionario en el trimestre frente a la tasa meta (80%).

Emergencia se carga con meta 0 (no aplica) hasta que el delegado la configure cuando ocurra.
