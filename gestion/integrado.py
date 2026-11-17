"""Reglas de la matriz SGR para el cuarto trimestre de 2026."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


CARGOS = [
    ('delegado', 'Delegado'), ('social', 'Gestor social'),
    ('administrativo', 'Apoyo administrativo'), ('organizaciones', 'Organizaciones comunitarias'),
    ('compras', 'Gestor de compras y proyectos'), ('planificacion', 'Gestión y planificación'),
    ('servicios', 'Coordinador de servicios comunitarios'), ('seguridad', 'Gestor de seguridad ciudadana'),
]

# Hoja RECLAMOS de la matriz: cada felicitación vale 10% (máximo 3), cada reclamo
# descuenta 20% y el sobrecumplimiento del colaborador no puede superar 150%.
BONO_FELICITACION = Decimal('10')
MAX_FELICITACIONES = 3
DESCUENTO_RECLAMO = Decimal('20')
TOPE_FINAL = Decimal('150')
# Hojas SEMAFORO y RESUMEN: naranjo desde el 60% del objetivo al día de hoy.
FACTOR_NARANJO = Decimal('0.6')


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


def resultado_item(meta, actividades, ausencias, inicio, fin, gestiones=None):
    if getattr(meta, 'indicador', 'cantidad') == 'tubo':
        return resultado_tubo(meta, gestiones or [])
    habiles = dias_habiles(inicio, fin)
    libres = set()
    for ausencia in ausencias:
        libres.update(dias_habiles(max(inicio, ausencia.desde), min(fin, ausencia.hasta)))
    ajustada = Decimal(meta.meta_cantidad) * Decimal(len(habiles - libres)) / Decimal(len(habiles) or 1)
    # Las felicitaciones se bonifican sobre el resultado final (hoja RECLAMOS), no como acción del ítem.
    validas = sum(1 for actividad in actividades
                  if actividad.item_id == meta.pk and actividad.puntuable and not actividad.felicitacion)
    porcentaje = min(Decimal('120'), Decimal(validas) * 100 / ajustada) if ajustada else None
    return {'meta': meta, 'cantidad': validas, 'ajustada': ajustada,
            'porcentaje': porcentaje, 'ponderado': porcentaje * meta.ponderador / 100 if porcentaje is not None else None}


def resultado_tubo(meta, gestiones):
    """Soluciones al ingreso al tubo: gestiones realizadas / ingresadas frente a la tasa meta (p. ej. 80%)."""
    total = len(gestiones)
    realizadas = sum(1 for gestion in gestiones if gestion.estado == 'Realizado')
    objetivo = Decimal(meta.meta_cantidad)
    porcentaje = None
    if total and objetivo:
        porcentaje = min(Decimal('120'), Decimal(realizadas) * 100 / total * 100 / objetivo)
    return {'meta': meta, 'cantidad': realizadas, 'ajustada': Decimal(total), 'tasa': True,
            'porcentaje': porcentaje, 'ponderado': porcentaje * meta.ponderador / 100 if porcentaje is not None else None}


def resultado_final(base, felicitaciones, reclamos):
    """Aplica la hoja RECLAMOS: +10% por felicitación (máx. 3), -20% por reclamo, entre 0% y 150%."""
    if base is None:
        return None
    bono = BONO_FELICITACION * min(felicitaciones, MAX_FELICITACIONES)
    return max(Decimal('0'), min(TOPE_FINAL, Decimal(base) + bono - DESCUENTO_RECLAMO * reclamos))


def dias_calendario(ausencias, inicio, fin):
    dias = set()
    for ausencia in ausencias:
        desde, hasta = max(inicio, ausencia.desde), min(fin, ausencia.hasta)
        dias.update(desde + timedelta(days=n) for n in range((hasta - desde).days + 1) if hasta >= desde)
    return len(dias)


def semaforo(avance, inicio, fin, hoy, ausencias):
    """Hoja SEMAFORO: objetivo = días transcurridos sin ausencias × porcentaje diario del trimestre."""
    total = (fin - inicio).days + 1
    corte = min(hoy, fin)
    transcurridos = (corte - inicio).days + 1 if corte >= inicio else 0
    netos = max(0, transcurridos - dias_calendario(ausencias, inicio, corte)) if transcurridos else 0
    objetivo = Decimal(netos) * 100 / Decimal(total)
    umbral = objetivo * FACTOR_NARANJO
    if avance is None:
        color = None
    elif avance >= objetivo:
        color = 'verde'
    elif avance >= umbral:
        color = 'naranjo'
    else:
        color = 'rojo'
    return {'objetivo': objetivo, 'umbral': umbral, 'color': color, 'transcurridos': transcurridos, 'netos': netos}


def trimestre_de(fecha):
    return fecha.year, (fecha.month - 1) // 3 + 1


def trimestres_anteriores(anio, trimestre, cantidad):
    for _ in range(cantidad):
        trimestre -= 1
        if trimestre == 0:
            anio, trimestre = anio - 1, 4
        yield anio, trimestre
