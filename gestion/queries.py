"""One authorized query powers list, table refresh and unpaginated export."""
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from urllib.parse import urlencode

from .access import scoped
from .models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion, ESTADOS, ESTADOS_ATENCION


MODULES = {
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
    state = {**default, **request.session.get(f'listado_{modulo}', {})}
    previous = state.copy()
    for name in default:
        if name in request.GET:
            state[name] = request.GET[name]
    state['q'] = str(state['q']).strip()[:140]
    allowed_states = dict(ESTADOS_ATENCION if modulo == 'atenciones' else ESTADOS)
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
    if any(state[name] != previous[name] for name in ['q', 'estado', 'tipo', 'tamano', 'orden']):
        state['pagina'] = 1
    request.session[f'listado_{modulo}'] = state
    return state


def query_for(user, modulo, state):
    config = MODULES[modulo]
    query = scoped(user, config['model'])
    if modulo == 'atenciones':
        query = query.select_related('tipo', 'subatencion', 'responsable', 'cliente')
        if state['tipo']:
            query = query.filter(tipo_id=state['tipo'])
    elif modulo == 'subatenciones':
        query = query.select_related('tipo')
    if state['q']:
        condition = Q()
        for field in config['search']:
            condition |= Q(**{f'{field}__icontains': state['q']})
        query = query.filter(condition)
    if state['estado']:
        query = query.filter(estado=state['estado'])
    return query.order_by(state['orden'], '-id')


def list_context(request, modulo):
    config = MODULES[modulo]
    state = state_for(request, modulo)
    query = query_for(request.user, modulo, state)
    page = Paginator(query, state['tamano']).get_page(state['pagina'])
    state['pagina'] = page.number
    request.session[f'listado_{modulo}'] = state
    model_name = config['model']._meta.model_name
    can = lambda action: request.user.has_perm(f'gestion.{action}_{model_name}')
    cols = [dict(label=label, key=key) for label, key in config['columns']]
    rows = [{'obj': obj, 'cells': [display_value(obj, col['key']) for col in cols]} for obj in page]
    base = reverse('gestion:listado', args=[modulo])
    pagination = []
    for number in page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1):
        pagination.append({'number': number, 'url': f'{base}?{urlencode({**state, "pagina": number})}' if isinstance(number, int) else '', 'current': number == page.number})
    return {
        'modulo': modulo, 'titulo': config['title'], 'state': state, 'page_obj': page,
        'columns': cols, 'rows': rows, 'can_add': can('add') and modulo != 'delegaciones',
        'can_change': can('change'), 'can_delete': can('delete') and modulo != 'delegaciones',
        'filter_choices': ESTADOS_ATENCION if modulo == 'atenciones' else ESTADOS,
        'order_choices': [(key, sort_label(key)) for key in config['sort']],
        'page_sizes': [5, 15, 30], 'pagination': pagination,
        'export_url': reverse('gestion:exportar', args=[modulo]),
        'tipos': scoped(request.user, TipoAtencion).filter(estado='Activo'),
    }


def display_value(obj, key):
    from datetime import datetime
    from django.utils import timezone
    value = obj
    for part in key.split('.'):
        value = getattr(value, part, '') if value else ''
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime('%d-%m-%Y %H:%M')
    return str(value) if value is not None else ''


def sort_label(key):
    names = {'nombre': 'Nombre', 'codigo': 'Código', 'folio': 'Folio', 'solicitante_nombre': 'Solicitante', 'created_at': 'Fecha de creación'}
    return names[key.lstrip('-')] + (' descendente' if key.startswith('-') else ' ascendente')
