"""Reglas de la matriz SGR para el cuarto trimestre de 2026."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


CARGOS = [
    ('delegado', 'Delegado'), ('social', 'Gestor social'),
    ('administrativo', 'Apoyo administrativo'), ('organizaciones', 'Organizaciones comunitarias'),
    ('compras', 'Gestor de compras y proyectos'), ('planificacion', 'Gestión y planificación'),
    ('servicios', 'Coordinador de servicios comunitarios'), ('seguridad', 'Gestor de seguridad ciudadana'),
]

# Nuevo requerimiento: subfamilias de organizaciones comunitarias (territoriales y funcionales).
SUBFAMILIAS = {
    'territorial': ['Junta de vecinos'],
    'funcional': ['Club de adulto mayor', 'Organización deportiva', 'Centro de madres', 'Centro cultural',
                  'Agrupación juvenil', 'Comité de seguridad', 'Comité de allegados', 'Comité de vecinos',
                  # Base JJVV: vivienda y agua potable rural pueden regirse por otro marco legal (correo de coordinación).
                  'Comité de vivienda', 'Comité de agua potable rural', 'Centro de padres y apoderados',
                  'Por clasificar'],
}

# Hoja RECLAMOS de la matriz: cada felicitación vale 10% (máximo 3), cada reclamo
# descuenta 20% y el sobrecumplimiento del colaborador no puede superar 150%.
BONO_FELICITACION = Decimal('10')
MAX_FELICITACIONES = 3
DESCUENTO_RECLAMO = Decimal('20')
TOPE_FINAL = Decimal('150')
# Hojas SEMAFORO y RESUMEN: naranjo desde el 60% del objetivo al día de hoy.
FACTOR_NARANJO = Decimal('0.6')


def primera_fecha_admisible(hoy=None):
    """Nuevo requerimiento, punto 4: la semana (lunes a viernes) se cierra el lunes siguiente."""
    hoy = hoy or timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes - timedelta(days=7) if hoy.weekday() == 0 else lunes


def limites_trimestre(anio, trimestre):
    mes = (trimestre - 1) * 3 + 1
    fin_mes = mes + 2
    ultimo = (date(anio, fin_mes, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return date(anio, mes, 1), ultimo


def periodo_actual(hoy=None):
    """Período de medición vigente (RF-005, RF-026) y plazo de ingreso semanal (punto 4)."""
    hoy = hoy or timezone.localdate()
    anio, trimestre = hoy.year, (hoy.month - 1) // 3 + 1
    inicio, fin = limites_trimestre(anio, trimestre)
    totales = (fin - inicio).days + 1
    transcurridos = (hoy - inicio).days + 1
    lunes = hoy - timedelta(days=hoy.weekday())
    primera = primera_fecha_admisible(hoy)
    return {
        'anio': anio, 'trimestre': trimestre, 'nombre': f'{trimestre}º trimestre {anio}',
        'inicio': inicio, 'fin': fin, 'dias_totales': totales, 'dia': transcurridos,
        'restantes': (fin - hoy).days, 'dias_habiles': len(dias_habiles(inicio, fin)),
        'meta_esperada': Decimal(transcurridos) * 100 / Decimal(totales),
        'semana_inicio': lunes, 'semana_fin': lunes + timedelta(days=4), 'cierre_semana': lunes + timedelta(days=7),
        'primera_admisible': primera, 'cierra_hoy': hoy.weekday() == 0,
        'semana_anterior_inicio': lunes - timedelta(days=7),
    }


def validar_fecha(fecha, hoy=None):
    hoy = hoy or timezone.localdate()
    primera = primera_fecha_admisible(hoy)
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
    """Soluciones al ingreso al tubo: gestiones realizadas / ingresadas frente a la tasa meta (p. ej. 80%).

    Nuevo requerimiento, punto 1: las solicitudes del delegado son «otra gestión» y no se contabilizan."""
    gestiones = [gestion for gestion in gestiones if getattr(gestion, 'solicitante_cargo', '') != 'delegado']
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
