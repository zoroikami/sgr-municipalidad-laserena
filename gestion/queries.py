"""One authorized query powers list, table refresh and unpaginated export."""
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, Prefetch
from django.urls import reverse
from urllib.parse import urlencode
from cuentas.rut import RutError, format_rut, normalize_rut

from .access import scoped
from .delegation import has_global_scope
from .forms import AtencionFilterForm
from .models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion, ESTADOS, ESTADOS_ATENCION, Organizacion, GestionTubo, Carta
from .models import ActividadSGR, CasoSocial


CARTA_FIELDS = [('Código', 'codigo'), ('Fecha de ingreso', 'fecha'),
    ('Nº de ingreso', 'numero_ingreso'), ('Para', 'para'), ('Remite', 'remite'),
    ('Fono de contacto', 'telefono'), ('Actividad o tema', 'nombre'),
    ('Fecha de la actividad', 'fecha_actividad'), ('Encargado de seguimiento', 'encargado.get_full_name'),
    ('Estado', 'estado'), ('Pronunciamiento', 'pronunciamiento'),
    ('Derivada a', 'derivada_a'), ('Observación', 'observacion')]

# Columnas de la hoja TUBO de la matriz SGR (más los datos del solicitante del nuevo requerimiento).
TUBO_FIELDS = [('Código', 'codigo'), ('Fecha de solicitud', 'fecha_solicitud'),
    ('Actividad / solicitud / problema', 'nombre'), ('INT/EXT', 'origen'), ('Solicitante', 'solicitante'),
    ('RUT solicitante', 'solicitante_rut'), ('Teléfono solicitante', 'solicitante_telefono'),
    ('Solicitante funcionario', 'solicitante_funcionario_texto'), ('Territorio', 'territorio'),
    ('Responsable', 'responsable.get_full_name'), ('Fecha de compromiso', 'fecha_compromiso'),
    ('Área / persona de apoyo', 'apoyo'), ('Avance, observaciones', 'observaciones'), ('Estatus', 'estado')]

CASO_FIELDS = [('Código', 'codigo'), ('Nombre del usuario', 'nombre'), ('RUT del usuario', 'usuario_rut'),
    ('Teléfono del usuario', 'usuario_telefono'), ('Gestor social', 'responsable.username'),
    ('Fecha de ingreso', 'fecha_ingreso'), ('Tipo de atención', 'tipo.nombre'), ('Subatención', 'subatencion.nombre'),
    ('Descripción', 'descripcion'), ('Estado', 'estado'), ('Requiere visita', 'requiere_visita'),
    ('Visita programada', 'fecha_programada_visita'), ('Visita realizada', 'fecha_visita'),
    ('Entrega del informe', 'fecha_informe'), ('Entrega del beneficio', 'fecha_beneficio'),
    ('Devoluciones del informe', 'devoluciones')]

MODULES = {
    'casos': {'model': CasoSocial, 'title': 'Casos sociales',
        'search': ['codigo', 'nombre', 'usuario_rut', 'subatencion__nombre'],
        'columns': [('Código', 'codigo'), ('Nombre del usuario', 'nombre'), ('Subatención', 'subatencion.nombre'),
                    ('Gestor social', 'responsable.username'), ('Estado', 'estado'), ('Ingreso', 'fecha_ingreso')],
        'export_columns': CASO_FIELDS, 'detail_columns': CASO_FIELDS,
        'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'fecha_ingreso', '-fecha_ingreso', 'created_at', '-created_at']},
    'cartas': {'model': Carta, 'title': 'Cartas de oficina de partes',
        'search': ['codigo', 'numero_ingreso', 'nombre', 'remite', 'derivada_a', 'pronunciamiento',
                   'encargado__first_name', 'encargado__last_name', 'encargado__username'],
        'columns': [('Código', 'codigo'), ('Nº de ingreso', 'numero_ingreso'), ('Actividad o tema', 'nombre'),
                    ('Remite', 'remite'), ('Para', 'para'), ('Estado', 'estado'), ('Fecha de ingreso', 'fecha')],
        'export_columns': CARTA_FIELDS, 'detail_columns': CARTA_FIELDS,
        'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'fecha', '-fecha', 'created_at', '-created_at']},
    'organizaciones': {'model': Organizacion, 'title': 'Organizaciones comunitarias',
        'search': ['codigo', 'nombre', 'familia', 'subfamilia', 'domicilio', 'registro_pj'],
        'columns': [('Código', 'codigo'), ('Nombre', 'nombre'), ('Familia', 'familia'), ('Subfamilia', 'subfamilia'), ('Verificada', 'verificada'), ('Estado', 'estado')],
        'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'created_at', '-created_at']},
    'tubo': {'model': GestionTubo, 'title': 'Gestiones en tubo',
        'search': ['codigo', 'nombre', 'solicitante', 'solicitante_rut', 'territorio', 'apoyo'],
        'columns': [('Código', 'codigo'), ('Gestión', 'nombre'), ('Solicitante', 'solicitante'), ('Territorio', 'territorio'), ('Apoyo', 'apoyo'), ('Estado', 'estado')],
        'export_columns': TUBO_FIELDS,
        'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'created_at', '-created_at']},
    'metas': {'model': ItemMeta, 'title': 'Ítems y Metas', 'search': ['codigo', 'nombre', 'descripcion'],
              'columns': [('Código', 'codigo'), ('Nombre', 'nombre'), ('Unidad', 'unidad_medida'), ('Meta', 'meta_cantidad'), ('Estado', 'estado'), ('Creación', 'created_at')],
              'sort': ['nombre', '-nombre', 'codigo', '-codigo', 'created_at', '-created_at']},
    'atenciones': {'model': Atencion, 'title': 'Atenciones ciudadanas', 'search': ['folio', 'solicitante_nombre', 'solicitante_rut', 'descripcion'],
                   'columns': [('Folio', 'folio'), ('Solicitante', 'solicitante_nombre'), ('Tipo de atención', 'tipo.nombre'), ('Estado', 'estado'), ('Creación', 'created_at')],
                   'sort': ['folio', '-folio', 'solicitante_nombre', '-solicitante_nombre', 'created_at', '-created_at']},
    'tipos': {'model': TipoAtencion, 'title': 'Tipos de atención', 'search': ['codigo', 'nombre'],
              'columns': [('Código', 'codigo'), ('Nombre', 'nombre'), ('Estado', 'estado'), ('Creación', 'created_at')],
              'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'created_at', '-created_at']},
    'subatenciones': {'model': SubAtencion, 'title': 'Subatenciones', 'search': ['codigo', 'nombre', 'tipo__nombre'],
                      'columns': [('Código', 'codigo'), ('Nombre', 'nombre'), ('Tipo', 'tipo.nombre'), ('Estado', 'estado'), ('Creación', 'created_at')],
                      'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'created_at', '-created_at']},
    'delegaciones': {'model': Delegacion, 'title': 'Delegaciones', 'search': ['codigo', 'nombre', 'direccion'],
                     'columns': [('Código', 'codigo'), ('Nombre', 'nombre'), ('Dirección', 'direccion'), ('Estado', 'estado')],
                     'sort': ['codigo', '-codigo', 'nombre', '-nombre', 'created_at', '-created_at']},
}


def state_for(request, modulo):
    config = MODULES[modulo]
    default = {'q': '', 'estado': '', 'orden': '-created_at', 'tamano': 15, 'pagina': 1, 'tipo': ''}
    if modulo == 'atenciones':
        default.update(responsable='', desde='', hasta='')
    state = {**default, **request.session.get(f'listado_{modulo}', {})}
    previous = state.copy()
    for name in default:
        if name in request.GET:
            state[name] = request.GET[name]
    state['q'] = str(state['q']).strip()[:140]
    allowed_states = dict(choices_for(modulo))
    if state['estado'] not in allowed_states:
        state['estado'] = ''
    if state['orden'] not in config['sort']:
        state['orden'] = '-created_at'
    try:
        state['tamano'] = int(state['tamano'])
    except (ValueError, TypeError):
        state['tamano'] = 15
    if state['tamano'] not in (5, 15, 30):
        state['tamano'] = 15
    try:
        state['pagina'] = max(1, min(int(state['pagina']), 10**7))
    except (ValueError, TypeError):
        state['pagina'] = 1
    tipo = str(state['tipo'])
    state['tipo'] = tipo if modulo == 'atenciones' and tipo.isdigit() and len(tipo) <= 12 else ''
    filter_form = None
    if modulo == 'atenciones':
        filter_form = AtencionFilterForm(state, user=request.user)
        if not filter_form.is_valid():
            return state, filter_form
        responsable = filter_form.cleaned_data['responsable']
        state['responsable'] = str(responsable.pk) if responsable else ''
        for name in ('desde', 'hasta'):
            value = filter_form.cleaned_data[name]
            state[name] = value.isoformat() if value else ''
    if any(state[name] != previous[name] for name in default if name != 'pagina'):
        state['pagina'] = 1
    request.session[f'listado_{modulo}'] = state
    return state, filter_form


def query_for(user, modulo, state):
    config = MODULES[modulo]
    query = scoped(user, config['model'])
    if modulo == 'atenciones':
        query = query.select_related('tipo', 'subatencion', 'responsable', 'cliente')
        if state['tipo']:
            query = query.filter(tipo_id=state['tipo'])
        if state['responsable']:
            query = query.filter(responsable_id=state['responsable'])
        if state['desde']:
            query = query.filter(created_at__date__gte=state['desde'])
        if state['hasta']:
            query = query.filter(created_at__date__lte=state['hasta'])
    elif modulo == 'casos':
        query = casos_con_gestiones(query)
    elif modulo == 'cartas':
        query = query.select_related('encargado')
    elif modulo == 'subatenciones':
        query = query.select_related('tipo')
    if state['q']:
        condition = Q()
        for field in config['search']:
            condition |= Q(**{f'{field}__icontains': state['q']})
        if modulo == 'casos':
            try:
                condition |= Q(usuario_rut=normalize_rut(state['q']))
            except RutError:
                pass
        query = query.filter(condition)
    if state['estado']:
        query = query.filter(estado=state['estado'])
    return query.order_by(state['orden'], '-id')


def casos_con_gestiones(query):
    # Tanto el detalle como los hitos exportados conservan el ámbito del caso.
    gestiones = ActividadSGR.objects.filter(delegacion_id=F('caso__delegacion_id')).select_related('item').order_by('fecha', 'pk')
    return query.select_related('responsable', 'tipo', 'subatencion', 'gestion_tubo').prefetch_related(
        Prefetch('gestiones', queryset=gestiones))


def list_context(request, modulo):
    config = MODULES[modulo]
    state, filter_form = state_for(request, modulo)
    invalid_filters = bool(filter_form and filter_form.errors)
    query = config['model'].objects.none() if invalid_filters else query_for(request.user, modulo, state)
    page = Paginator(query, state['tamano']).get_page(state['pagina'])
    state['pagina'] = page.number
    if not invalid_filters:
        request.session[f'listado_{modulo}'] = state
    model_name = config['model']._meta.model_name
    can = lambda action: request.user.has_perm(f'gestion.{action}_{model_name}')
    cols = [dict(label=label, key=key) for label, key in config['columns']]
    rows = [{'obj': obj, 'cells': [display_value(obj, col['key']) for col in cols]} for obj in page]
    base = reverse('gestion:listado', args=[modulo])
    pagination = []
    for number in page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1):
        pagination.append({'number': number, 'url': f'{base}?{urlencode({**state, "pagina": number})}' if isinstance(number, int) else '', 'current': number == page.number})
    export_url = reverse('gestion:exportar', args=[modulo])
    if modulo == 'atenciones':
        export_url = '' if invalid_filters else f'{export_url}?{urlencode(state)}'
    context = {
        'modulo': modulo, 'titulo': config['title'], 'state': state, 'page_obj': page,
        'columns': cols, 'rows': rows, 'can_add': can('add') and (modulo != 'delegaciones' or has_global_scope(request.user)),
        'can_change': can('change'), 'can_delete': can('delete') and modulo != 'delegaciones',
        'filter_choices': choices_for(modulo),
        'order_choices': [(key, sort_label(key)) for key in config['sort']],
        'page_sizes': [5, 15, 30], 'pagination': pagination,
        'filter_form': filter_form, 'invalid_filters': invalid_filters, 'export_url': export_url,
        'tipos': scoped(request.user, TipoAtencion).filter(estado='Activo'),
    }

    if modulo == 'cartas':
        totals = {row['estado']: row['cantidad'] for row in scoped(request.user, Carta)
                  .values('estado').annotate(cantidad=Count('pk'))}
        styles = ['proceso', 'realizado', 'realizado', '']
        context['cartas_resumen'] = [
            {'label': label, 'cantidad': totals.get(value, 0), 'clase': style}
            for (value, label), style in zip(Carta.ESTADOS, styles)]
        context['cartas_resumen'].append({'label': 'Total', 'cantidad': sum(totals.values()), 'clase': ''})
    return context


def display_value(obj, key):
    from datetime import datetime
    from django.utils import timezone
    value = obj
    for part in key.split('.'):
        value = getattr(value, part, '') if value else ''
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime('%d-%m-%Y %H:%M')
    if key in ('rut', 'solicitante_rut', 'usuario_rut'):
        return format_rut(value)
    if callable(value):
        value = value() or getattr(getattr(obj, 'encargado', None), 'username', '')
    if isinstance(value, bool):
        return 'Sí' if value else 'No'
    return str(value) if value is not None else ''


def choices_for(modulo):
    if modulo == 'casos':
        return CasoSocial.ESTADOS
    if modulo == 'cartas':
        return Carta.ESTADOS
    return GestionTubo.ESTADOS if modulo == 'tubo' else ESTADOS_ATENCION if modulo == 'atenciones' else ESTADOS


SORT_LABELS = {
    # Etiquetas breves: caben en el filtro sin recortar y distinguen la dirección del orden.
    'created_at': ('Más antiguos', 'Más recientes'), 'fecha': ('Ingreso más antiguo', 'Ingreso más reciente'),
    'nombre': ('Nombre A–Z', 'Nombre Z–A'), 'solicitante_nombre': ('Solicitante A–Z', 'Solicitante Z–A'),
    'codigo': ('Código menor primero', 'Código mayor primero'), 'folio': ('Folio menor primero', 'Folio mayor primero'),
    'fecha_ingreso': ('Ingreso más antiguo', 'Ingreso más reciente'),
}


def sort_label(key):
    ascendente, descendente = SORT_LABELS[key.lstrip('-')]
    return descendente if key.startswith('-') else ascendente
