"""Reglas de la matriz SGR para el cuarto trimestre de 2026."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


CARGOS = [
    ('delegado', 'Delegado'), ('social', 'Gestor social'),
    ('administrativo', 'Apoyo administrativo'), ('organizaciones', 'Organizaciones comunitarias'),
    ('compras', 'Gestor de compras y proyectos'), ('planificacion', 'Gestión y planificación'),
    ('servicios', 'Coordinador de servicios comunitarios'),
]


def validar_fecha(fecha, hoy=None):
    hoy = hoy or timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())
    primera = lunes - timedelta(days=7) if hoy.weekday() == 0 else lunes
    if fecha > hoy:
        raise ValidationError('No puedes registrar acciones futuras.')
    if fecha < primera:
        raise ValidationError('La semana anterior cierra el lunes siguiente. Desde el martes no admite ingresos.')


def dias_habiles(inicio, fin):
    """Lunes a viernes. No se presume un calendario de feriados no proporcionado."""
    if fin < inicio:
        return set()
    return {inicio + timedelta(days=n) for n in range((fin - inicio).days + 1)
            if (inicio + timedelta(days=n)).weekday() < 5}


def resultado_item(meta, actividades, ausencias, inicio, fin):
    habiles = dias_habiles(inicio, fin)
    libres = set()
    for ausencia in ausencias:
        libres.update(dias_habiles(max(inicio, ausencia.desde), min(fin, ausencia.hasta)))
    ajustada = Decimal(meta.meta_cantidad) * Decimal(len(habiles - libres)) / Decimal(len(habiles) or 1)
    validas = sum(1 for actividad in actividades if actividad.item_id == meta.pk and actividad.puntuable)
    porcentaje = min(Decimal('120'), Decimal(validas) * 100 / ajustada) if ajustada else None
    return {'meta': meta, 'cantidad': validas, 'ajustada': ajustada,
            'porcentaje': porcentaje, 'ponderado': porcentaje * meta.ponderador / 100 if porcentaje is not None else None}
