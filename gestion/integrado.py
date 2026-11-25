"""Reglas de la matriz SGR para el cuarto trimestre de 2026."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


# Columna AREA del código de verificación en cada hoja (APA, COS, COM1-4, SOC, PYG, SEG).
AREAS_VERIFICACION = {'delegado': 'DEL', 'social': 'SOC', 'administrativo': 'APA', 'organizaciones': 'COM',
                      'compras': 'CYP', 'planificacion': 'PYG', 'servicios': 'COS', 'seguridad': 'SEG'}

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

# Listas de territorio de las hojas TUBO COMPAÑIAS y TUBO ANTENA (matriz SGR 3er trimestre, revisión).
TERRITORIOS_TUBO = {
    'LAS COMPANIAS': ['Latorre', 'Rukalaf', 'Toqui', 'Zorrilla'],
    'LA ANTENA - LA FLORIDA': ['Alfalfares', 'Antena', 'Ceres', 'La Florida'],
}

# Hoja RECLAMOS de la matriz: cada felicitación vale 10% (máximo 3) y el sobrecumplimiento del colaborador no
# puede superar 150%. Cada reclamo descuenta 30%: así lo calculan 11 de las 13 hojas por funcionario (celda
# RECLAMOS = -0,3) y el reclamo registrado en la hoja RECLAMOS; el -0,2 del encabezado y de COOR DISERCO y
# G SOC 1 corresponde a la versión anterior de la plantilla.
BONO_FELICITACION = Decimal('10')
MAX_FELICITACIONES = 3
DESCUENTO_RECLAMO = Decimal('30')
TOPE_FINAL = Decimal('150')
# Hojas SEMAFORO y RESUMEN: naranjo desde el 60% del objetivo al día de hoy.
FACTOR_NARANJO = Decimal('0.6')
# Tono del componente de resumen (static/sgr/resumenes.css) para cada color del semáforo.
TONO_SEMAFORO = {'verde': 'verde', 'naranjo': 'ambar', 'rojo': 'rojo'}
# Nuevo requerimiento, punto 7: ningún ítem puede superar 120% de cumplimiento.
TOPE_ITEM = Decimal('120')

# Hoja SALON: cumplimiento de la delegación con ponderadores propios, que suman 1,0 sin el gestor de
# seguridad (la hoja lo evalúa en un bloque aparte, G SEGUR). Cada fila suma avances y metas de todos los
# funcionarios del cargo (por ejemplo, las cuatro hojas T OC) y algunas agrupan dos ítems de la hoja del cargo.
# (área, ítem, ponderador, cargo, ítems de la matriz por cargo que suma)
SALON = [
    ('Apoyo administrativo', 'Atención de usuario teléfono y presencial', '0.06', 'administrativo',
     ['ATENCIÓN DE USUARIO TELÉFONO Y PRESENCIAL']),
    ('Apoyo administrativo', 'Llamadas preventivas a usuarios', '0.05', 'administrativo', ['LLAMADAS PREVENTIVAS A USUARIOS']),
    ('Apoyo administrativo', 'Informe de inventarios', '0.03', 'administrativo', ['INFORME DE INVENTARIOS']),
    ('Apoyo administrativo', 'Informe a comunicaciones', '0.05', 'administrativo', ['INFORME A COMUNICACIONES']),
    ('Organizaciones comunitarias', 'Atención de usuario teléfono y presencial', '0.05', 'organizaciones',
     ['ATENCIÓN DE USUARIO TELÉFONO Y PRESENCIAL']),
    ('Organizaciones comunitarias', 'Visitas, reuniones con organizaciones', '0.04', 'organizaciones',
     ['VISITAS, REUNIONES CON ORGANIZACIONES']),
    ('Organizaciones comunitarias', 'Conformación de directivas definitivas', '0.05', 'organizaciones',
     ['CONFORMACIÓN DE ORGANIZACIONES']),
    ('Organizaciones comunitarias', 'Gestión de talleres y actividades', '0.05', 'organizaciones',
     ['GESTIÓN DE TALLERES Y ACTIVIDADES']),
    ('DISERCO', 'Informes', '0.03', 'servicios', ['INFORMES PERSONAL', 'INFORME TRABAJO']),
    ('DISERCO', 'Operativos', '0.04', 'servicios', ['OPERATIVO DELEGACIÓN', 'OPERATIVO DISERCO']),
    ('DISERCO', 'Talleres', '0.05', 'servicios', ['TALLERES']),
    ('DISERCO', 'Terreno', '0.04', 'servicios', ['TERRENO']),
    ('DISERCO', 'Atención requerimiento usuario', '0.05', 'servicios', ['ATENCIÓN REQUERIMIENTO USUARIO']),
    ('Gestión social', 'Atención social a usuario presencial', '0.05', 'social', ['ATENCIÓN SOCIAL A USUARIO PRESENCIAL']),
    ('Gestión social', 'Visita social en terreno', '0.05', 'social', ['VISITA TERRENO']),
    ('Gestión social', 'Entrega informe', '0.04', 'social', ['ENTREGA INFORME']),
    ('Gestión social', 'Entrega beneficio', '0.04', 'social', ['ENTREGA BENEFICIO']),
    ('Planificación y control', 'Reunión semanal con el equipo', '0.04', 'planificacion', ['REUNIÓN SEMANAL CON EL EQUIPO']),
    ('Planificación y control', 'Solución de problemas a usuarios particulares', '0.04', 'planificacion',
     ['SOLUCIÓN DE PROBLEMAS A USUARIOS PARTICULARES']),
]
SALON_TUBO = Decimal('0.05')         # Soluciones de ingresos al tubo: meta 80% realizado.
SALON_PENDIENTES = Decimal('0.05')   # Pendientes en tubo menor a 10%.
SALON_EMERGENCIA = Decimal('0.05')
META_TUBO_DELEGACION = Decimal('80')


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
    porcentaje = min(TOPE_ITEM, Decimal(validas) * 100 / ajustada) if ajustada else None
    return {'meta': meta, 'cantidad': validas, 'ajustada': ajustada,
            'porcentaje': porcentaje, 'ponderado': porcentaje * meta.ponderador / 100 if porcentaje is not None else None}


def con_datos_usuario(gestion):
    return bool(str(getattr(gestion, 'solicitante', '') or '').strip()
                and str(getattr(gestion, 'solicitante_telefono', '') or '').strip())


def gestiones_contables(gestiones):
    """Nuevo requerimiento, punto 1: las solicitudes del delegado son «otra gestión» y no se contabilizan."""
    return [gestion for gestion in gestiones if getattr(gestion, 'solicitante_cargo', '') != 'delegado']


def resultado_tubo(meta, gestiones):
    """Soluciones al ingreso al tubo: gestiones realizadas / ingresadas frente a la tasa meta (p. ej. 80%).

    Punto 2: una solicitud sin nombre y teléfono del usuario no da puntaje; sigue contando como ingresada
    para que omitir esos datos no mejore la tasa."""
    gestiones = gestiones_contables(gestiones)
    total = len(gestiones)
    realizadas = sum(1 for gestion in gestiones if gestion.estado == 'Realizado' and con_datos_usuario(gestion))
    objetivo = Decimal(meta.meta_cantidad)
    porcentaje = None
    if total and objetivo:
        porcentaje = min(TOPE_ITEM, Decimal(realizadas) * 100 / total * 100 / objetivo)
    return {'meta': meta, 'cantidad': realizadas, 'ajustada': Decimal(total), 'tasa': True,
            'porcentaje': porcentaje, 'ponderado': porcentaje * meta.ponderador / 100 if porcentaje is not None else None}


def resultado_final(base, felicitaciones, reclamos):
    """Aplica la hoja RECLAMOS: +10% por felicitación (máx. 3), -30% por reclamo, entre 0% y 150%."""
    if base is None:
        return None
    bono = BONO_FELICITACION * min(felicitaciones, MAX_FELICITACIONES)
    return max(Decimal('0'), min(TOPE_FINAL, Decimal(base) + bono - DESCUENTO_RECLAMO * reclamos))


def titulo_item(cargo, nombre):
    """Nombre con que cargar_matriz_sgr crea el ítem de un cargo (el nombre es único por delegación)."""
    return f'{nombre.capitalize()} ({dict(CARGOS)[cargo]})'


def puntaje_pendientes(tasa):
    """Hoja SALON: 100% si los pendientes son hasta 10% del tubo, 50% hasta 50% y 0% sobre eso."""
    if tasa is None:
        return None
    return Decimal(100) if tasa <= 10 else Decimal(50) if tasa <= 50 else Decimal(0)


def resultado_delegacion(metas, metricas, gestiones):
    """Hoja SALON: cumplimiento ponderado de la delegación.

    `metas` son los ítems activos de la delegación, `metricas` las filas de resultado_item de todos sus
    funcionarios y `gestiones` las del tubo de la delegación en el período. Una fila sin datos no se pondera
    y el peso considerado se informa, para que nadie lea un total inflado sin saber por qué."""
    nombres = {meta.nombre for meta in metas}
    filas = []

    def agregar(area, nombre, ponderador, tipo, meta, avance, porcentaje, nota=''):
        filas.append({'area': area, 'nombre': nombre, 'ponderador': ponderador * 100, 'tipo': tipo, 'meta': meta,
                      'avance': avance, 'porcentaje': porcentaje, 'nota': nota,
                      'ponderado': porcentaje * ponderador if porcentaje is not None else None})

    for area, nombre, ponderador, cargo, fuentes in SALON:
        titulos = {titulo_item(cargo, fuente) for fuente in fuentes}
        propias = [fila for fila in metricas if fila['meta'].nombre in titulos and fila['meta'].cargo_sgr == cargo]
        meta = sum((fila['ajustada'] for fila in propias), Decimal(0))
        avance = sum(fila['cantidad'] for fila in propias)
        nota = ('La delegación no tiene este ítem activo.' if not titulos & nombres else
                'Sin funcionarios con este cargo.' if not propias else 'Meta en cero.' if not meta else '')
        porcentaje = min(TOPE_ITEM, Decimal(avance) * 100 / meta) if meta else None
        agregar(area, nombre, Decimal(ponderador), 'cantidad', meta, avance, porcentaje, nota)

    contables = gestiones_contables(gestiones)
    total = len(contables)
    realizadas = sum(1 for gestion in contables if gestion.estado == 'Realizado' and con_datos_usuario(gestion))
    pendientes = sum(1 for gestion in contables if gestion.estado == 'Pendiente')
    tasa = Decimal(realizadas) * 100 / total if total else None
    agregar('Tubo de trabajo', 'Soluciones de ingresos al tubo', SALON_TUBO, 'tubo', META_TUBO_DELEGACION,
            {'realizadas': realizadas, 'total': total, 'tasa': tasa},
            min(TOPE_ITEM, tasa * 100 / META_TUBO_DELEGACION) if tasa is not None else None,
            '' if total else 'Sin gestiones en el tubo.')
    tasa_pendientes = Decimal(pendientes) * 100 / total if total else None
    agregar('Tubo de trabajo', 'Pendientes en tubo menor a 10%', SALON_PENDIENTES, 'pendientes', Decimal(10),
            {'pendientes': pendientes, 'total': total, 'tasa': tasa_pendientes}, puntaje_pendientes(tasa_pendientes),
            '' if total else 'Sin gestiones en el tubo.')
    emergencias = {titulo_item(cargo, 'EMERGENCIA') for cargo, _ in CARGOS}
    atendidas = sum(fila['cantidad'] for fila in metricas if fila['meta'].nombre in emergencias)
    agregar('Emergencias', 'Emergencia', SALON_EMERGENCIA, 'emergencia', None, atendidas,
            Decimal(100) if atendidas else None, '' if atendidas else 'Sin emergencias en el período: no aplica.')

    peso = sum((fila['ponderador'] for fila in filas if fila['porcentaje'] is not None), Decimal(0))
    suma = sum((fila['ponderado'] for fila in filas if fila['ponderado'] is not None), Decimal(0))
    return {'filas': filas, 'peso': peso, 'total': suma * 100 / peso if peso else None}


def dias_calendario(ausencias, inicio, fin):
    dias = set()
    for ausencia in ausencias:
        desde, hasta = max(inicio, ausencia.desde), min(fin, ausencia.hasta)
        dias.update(desde + timedelta(days=n) for n in range((hasta - desde).days + 1) if hasta >= desde)
    return len(dias)


def semaforo(avance, inicio, fin, hoy, ausencias):
    """Hoja SEMAFORO: objetivo al día = días disponibles transcurridos / días disponibles del trimestre.

    Las ausencias ya prorratean la meta de cada ítem (resultado_item); por eso el objetivo se mide sobre
    los días disponibles del funcionario y llega a 100% al cierre. Descontarlas también del objetivo sobre
    el total del trimestre las restaría dos veces."""
    total = (fin - inicio).days + 1
    corte = min(hoy, fin)
    transcurridos = (corte - inicio).days + 1 if corte >= inicio else 0
    netos = max(0, transcurridos - dias_calendario(ausencias, inicio, corte)) if transcurridos else 0
    disponibles = total - dias_calendario(ausencias, inicio, fin)
    objetivo = Decimal(netos) * 100 / Decimal(disponibles) if disponibles > 0 else Decimal(0)
    umbral = objetivo * FACTOR_NARANJO
    if avance is None:
        color = None
    elif avance >= objetivo:
        color = 'verde'
    elif avance >= umbral:
        color = 'naranjo'
    else:
        color = 'rojo'
    return {'objetivo': objetivo, 'umbral': umbral, 'color': color, 'transcurridos': transcurridos, 'netos': netos,
            'disponibles': disponibles, 'tono': TONO_SEMAFORO.get(color, 'neutro')}


def trimestre_de(fecha):
    return fecha.year, (fecha.month - 1) // 3 + 1


def trimestres_anteriores(anio, trimestre, cantidad):
    for _ in range(cantidad):
        trimestre -= 1
        if trimestre == 0:
            anio, trimestre = anio - 1, 4
        yield anio, trimestre
