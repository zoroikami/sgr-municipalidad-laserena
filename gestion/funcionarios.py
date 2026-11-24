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
