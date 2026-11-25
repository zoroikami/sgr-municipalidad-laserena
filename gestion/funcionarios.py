"""Identifica funcionarios municipales por RUT (Perfil.rut) y resume su cargo.

Las funciones resumen el «Descriptor de funciones para los cargos de las Delegaciones» (versión 2026).
El gestor de seguridad no figura en el descriptor: su resumen proviene de la hoja GES SEG de la matriz SGR.
"""
from django.contrib.auth import get_user_model

from cuentas.rut import RutError, normalize_rut
from .integrado import CARGOS

DESCRIPTOR = {
    'delegado': 'Representa a la alcaldía en el territorio y es el puente entre el municipio, los dirigentes y los vecinos.',
    'social': 'Atiende y evalúa casos sociales, realiza visitas en terreno, deriva y ejecuta acciones comunitarias.',
    'administrativo': 'Lleva la agenda del delegado, atiende público, registra atenciones SGR e inventarios.',
    'organizaciones': 'Registro de organizaciones (OROC): constitución, vigencia y asesoría de juntas de vecinos y agrupaciones.',
    'compras': 'Tramita adquisiciones de bienes y servicios y controla el plan anual de compras.',
    'planificacion': 'Coordina procesos internos, informes a jefatura, la reunión semanal y el llenado de la matriz SGR.',
    'servicios': 'Coordina operativos de aseo, ornato y medio ambiente, cuadrillas y el enlace con DISERCO.',
    'seguridad': 'Forma comités de seguridad, levanta incivilidades, media conflictos y recupera espacios públicos.',
}

# Listas completas del «Descriptor de funciones para los cargos de las Delegaciones»,
# versión 2026, páginas 3-8. Se normalizan espacios, puntuación y erratas ortográficas.
# Seguridad no figura en el PDF: se mantienen las labores de GES SEG del resumen anterior.
FUNCIONES = {
    'delegado': [
        'Informar a la autoridad comunal sobre situaciones que pudieran ocurrir en su territorio, '
        'con el objeto de adoptar las medidas preventivas correspondientes.',
        'Ser representante de la máxima autoridad comunal en su territorio, empoderándose de su cargo '
        'para enfrentar y solucionar las necesidades permanentes de los usuarios.',
        'Responsable del buen funcionamiento del territorio desde la parte interna administrativa '
        'al cumplimiento de las gestiones encomendadas a la Delegación.',
        'Visitar periódicamente Juntas de vecinos y Organizaciones comunitarias con el objetivo '
        'de estar presente, generando acompañamiento y apoyo.',
        'Proponer y dar soluciones a las necesidades y problemas de los usuarios del sector, '
        'con el objeto de potenciar y mejorar la gestión de los servicios municipales.',
        'Poner en práctica y supervisar el cumplimiento de planes y políticas de desarrollo '
        'que beneficien a la comunidad, de acuerdo a lo dispuesto por la máxima autoridad comunal.',
        'Mantener buena relación y comunicación con las distintas direcciones y/o departamentos '
        'del municipio, así como con las organizaciones públicas y sociales, con el objetivo '
        'de apoyar el buen funcionamiento de su equipo de trabajo en las soluciones de las tareas encomendadas.',
        'Hacer difusión de los programas y actividades implementados por la Municipalidad.',
        'Delegar trabajos solicitados por la comunidad a su equipo de trabajo, orientando '
        'y guiando el buen desempeño de las acciones.',
        'Generar mesas de trabajo con distintos estamentos públicos y privados, siendo '
        'el puente para los usuarios que necesitan atención.',
        'Ejecutar otras funciones que la ley señale, que le encomiende el alcalde '
        'o el Administrador Municipal en el ámbito de sus competencias.',
    ],
    'social': [
        # Atención de casos; acciones comunitarias; coordinación y gestión; auto-mejora.
        'Recepción y evaluación de casos.',
        'Diagnóstico y planificación.',
        'Intervención y seguimiento.',
        'Derivación y articulación.',
        'Visitas en terreno.',
        'Diagnóstico comunitario.',
        'Planificación y ejecución de programas.',
        'Organización y participación comunitaria.',
        'Articular con organizaciones de apoyo social.',
        'Coordinación con otros servicios: Coordinar con otros servicios y programas municipales '
        'para asegurar la atención integral de los ciudadanos.',
        'Gestión de recursos: Gestionar recursos para la atención de casos '
        'y la ejecución de programas comunitarios.',
        'Informes y estadísticas: Elaborar informes y estadísticas sobre la atención '
        'de casos y las acciones comunitarias realizadas.',
        'Participación en reuniones y comités.',
        'Capacitación y actualización.',
        'Apoyo a la gestión municipal.',
    ],
    'administrativo': [
        'Llevar la agenda del delegado para así poder coordinar los diferentes eventos y reuniones '
        'en los que él debe participar, ordenando y centralizando la información.',
        'Coordinador del transporte de la delegación.',
        'Encargado de los auxiliares, mantención y aseo.',
        'Dar atención al público y derivar a las áreas correspondientes dentro de la delegación.',
        'Generar un registro de atenciones (registro en planilla SGR), '
        'para posteriormente llamar preventivamente al usuario.',
        'Generar inventario trimestral de la delegación.',
        'Realizar la entrega de materiales a los funcionarios.',
        'Retroalimentar para la gestión del delegado las solicitudes ingresadas por la comunidad '
        '(correos al alias, solicitudes por carta, en oficina y/o oficina de partes, etc.).',
        'Informes mensuales del personal administrativo (se excluye empleabilidad): permisos, '
        'solicitudes y armado de carpetas para pago, envío de documentos digitales para transparencia.',
        'Encargada de envío de agenda a Comunicaciones.',
        'Temas varios en procesos administrativos para cumplir los objetivos planteados por la Delegación.',
    ],
    'organizaciones': [
        'Potenciar integralmente el desarrollo de los territorios costeros en beneficio de la comunidad.',
        'Creación de organizaciones nuevas y mantener vigencia o cierre de OOCC inactivas.',
        'Asesorar y capacitar en distintas temáticas y procedimientos de las OOCC en general.',
        'Levantamiento de necesidades en cada territorio (visitas) '
        'en conjunto con los dirigentes de cada organización.',
        'Encargado de generar las convocatorias a las distintas actividades municipales que se realicen.',
        'Articulador entre las Organizaciones Comunitarias y distintas áreas municipales '
        'para el cumplimiento de los requerimientos y necesidades de los usuarios.',
        'Generar actividades y talleres a las organizaciones, manteniendo la motivación '
        'y aumentando la educación en temas municipales.',
        'Temas varios en procesos administrativos para cumplir los objetivos planteados por la Delegación.',
    ],
    'compras': [
        'Recopilar y confeccionar la planificación operativa anual de su Dirección, '
        'considerando los requerimientos de todas las unidades de ella.',
        'Realizar control de gestión al cumplimiento del Plan Anual de Compras de su dirección, '
        'evaluando permanentemente las necesidades de éstas con el Director respectivo. '
        'Las necesidades deben estar en directa relación con los requerimientos para '
        'un correcto funcionamiento y operación de la Dirección a su cargo.',
        'Revisar pliego de condiciones, marco de referencia y especificaciones técnicas, '
        'cuando corresponda, dando su visto bueno para posteriormente remitir a la Unidad Revisora '
        'junto con la solicitud y los documentos asociados.',
        'Elaborar las solicitudes o el oficio interno ordinario de contrataciones de bienes '
        'y/o servicios de su dirección con la debida anticipación, de acuerdo a la planificación '
        'existente y a los requerimientos emanados de las distintas unidades.',
        'Incorporar en las solicitudes o el oficio interno ordinario la propuesta de designación '
        'de la Comisión Evaluadora o Evaluador, del Inspector Técnico de Contrato titular '
        'y subrogante, según corresponda.',
    ],
    'planificacion': [
        'Encargado de derivar y apoyar a cada área en la realización '
        'y entrega de los informes solicitados por la Jefatura.',
        'Apoya con registros al levantamiento y/o actualización del diagnóstico '
        'de las necesidades de la comunidad de su sector, así como listados '
        'de información estratégica para la toma de decisiones.',
        'Encargado de mantener el buen funcionamiento de los procesos de la delegación, '
        'participando en acciones de coordinación interna del personal, '
        'derivando tareas del día a día y apoyando el cumplimiento de estas.',
        'Encargado de generar información al delegado referente al trabajo de la matriz SGR, '
        'indicando las fortalezas y debilidades de cada colaborador '
        'y anticiparse a los resultados de la Delegación.',
        'Informar oportunamente al delegado Municipal sobre materias de interés del sector.',
        'Coordinación con departamentos internos y/o equipo de coordinación '
        'de las Delegaciones municipales, cuando la jefatura requiera.',
        'Encargado de tomar acciones rápidas de solución a problemas derivados desde Gabinete.',
        'Participar como representante de la delegación cuando el delegado lo solicite.',
        'Coordinación con los diferentes departamentos municipales para la consecución de los objetivos.',
        'Responsable del buen funcionamiento del llenado de la matriz SGR.',
        'Encargado de gestionar la reunión semanal.',
        'Temas varios en procesos administrativos para cumplir los objetivos planteados por la Delegación.',
    ],
    'servicios': [
        'Servir de enlace permanente entre la Municipalidad y las Juntas de Vecinos, '
        'organizaciones funcionales, clubes deportivos y agrupaciones ambientales '
        'para la realización de operativos de limpieza y reparaciones de BNUP.',
        'Atención del usuario presencial y en terreno cuando se requiera de un análisis técnico '
        'para desarrollar o ejecutar obras de mejoramiento (caminos, desmalezamiento, etc.).',
        'Coordinar la ejecución y seguimiento de operativos de limpieza y desmalezado, '
        'mejoramiento de barrios y recuperación de espacios.',
        'Liderar y coordinar acciones de educación ambiental (talleres de reciclaje, '
        'compostaje, aseo y ornato), operativos de limpieza y programas de reciclaje.',
        'Responsable del buen funcionamiento operativo y administrativo de las cuadrillas '
        'del programa de empleabilidad y cuadrilla de emergencia (polifuncionales).',
        'Coordinar acciones con distintas direcciones municipales (Aseo y Ornato, '
        'Operaciones, maquinarias) para garantizar servicios eficientes para la comunidad.',
        'Recibir, canalizar y realizar el seguimiento de denuncias ciudadanas '
        'relacionadas con el uso indebido de los espacios públicos.',
        'Elaborar informes de gestión periódicos del programa de empleabilidad y cuadrilla de polifuncionales.',
        'Temas varios en procesos administrativos para el buen desempeño '
        'de la delegación en el área de servicios a la comunidad.',
    ],
    'seguridad': [
        'Formar comités de seguridad.',
        'Levantar incivilidades.',
        'Mediar conflictos.',
        'Recuperar espacios públicos.',
    ],
}
SIN_CARGO = 'Funcionario sin cargo asignado'


def cargo_de(user):
    """Cargo SGR del funcionario; un delegado sin cargo cargado se reconoce por su rol."""
    cargo = getattr(getattr(user, 'perfil', None), 'cargo_sgr', '') or ''
    if not cargo and user.groups.filter(name='Delegado Municipal').exists():
        cargo = 'delegado'
    return cargo


def nombre_cargo(cargo):
    return dict(CARGOS).get(cargo, SIN_CARGO)


def buscar_funcionario(rut):
    """Cuenta municipal activa con ese RUT. Las cuentas Cliente (vecinos) no son funcionarios."""
    try:
        rut = normalize_rut(rut)
    except RutError:
        return None
    return (get_user_model().objects.filter(is_active=True, perfil__rut=rut)
            .exclude(groups__name='Cliente').select_related('perfil__delegacion').first())


def ficha(user):
    """Datos mínimos para el aviso: sin RUT, correo ni datos de contacto."""
    cargo = cargo_de(user)
    delegacion = user.perfil.delegacion
    return {'nombre': user.get_full_name() or user.username, 'cargo': cargo, 'cargo_nombre': nombre_cargo(cargo),
            'funciones': DESCRIPTOR.get(cargo, ''), 'delegacion': delegacion.nombre if delegacion else '',
            'delegacion_id': delegacion.pk if delegacion else None, 'es_delegado': cargo == 'delegado'}
