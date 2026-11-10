# Proyecto Integrado 3

Esta rama incorpora el tubo de trabajo, el registro de acciones SGR, organizaciones comunitarias y el ajuste de metas por ausencias. Conserva las atenciones ciudadanas existentes y sus permisos por delegación.

## Instalación

Con las dependencias del proyecto instaladas y el entorno configurado:

```sh
python manage.py migrate
python manage.py sincronizar_roles
python manage.py asignar_delegado NOMBRE_DE_USUARIO
```

El último comando se ejecuta únicamente para el funcionario designado como delegado. Requiere una cuenta activa con delegación y rol Editor o Administrador. La atribución permite informar felicitaciones, registrar ausencias y configurar metas; no modifica el rol de acceso. La administración técnica también dispone de esas funciones. Los cuatro roles existentes conservan su alcance: el lector consulta y el cliente sigue accediendo solo a su portal.

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

## Validación local

Se aplicaron las migraciones sobre SQLite de desarrollo y se verificaron el tablero y el informe en navegador con diez gestiones ficticias (3 ingresadas, 1 pendiente, 1 en proceso y 5 realizadas).

Con `USE_SQLITE=true`, `DJANGO_DEBUG=true` y las variables Django de desarrollo:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q --ignore=tests_django/test_concurrency.py --ignore=tests_django/test_realtime.py -k "not parallel_creations"
```

Resultado: 100 pruebas aprobadas. La suite completa necesita MySQL y Redis: las pruebas existentes de concurrencia no son válidas con bloqueos de SQLite y las de eventos no pueden conectarse a Redis en este equipo. Esas pruebas deben ejecutarse en el entorno de integración del proyecto antes de desplegar. Esta rama no modifica ni despliega la instancia existente.
