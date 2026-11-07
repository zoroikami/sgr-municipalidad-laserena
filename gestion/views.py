from io import BytesIO
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

from .access import authorize, delegation_id, is_cliente, scoped
from .forms import FORMS
from .models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion
from .queries import MODULES, display_value, list_context, query_for, state_for
from .realtime import notify_after_commit


def module_config(modulo):
    if modulo not in MODULES:
        raise Http404
    return MODULES[modulo]


@login_required
def inicio(request):
    if request.user.is_superuser and not hasattr(request.user, 'perfil'):
        return redirect('admin:index')
    if is_cliente(request.user):
        return redirect('gestion:portal')
    delegation_id(request.user)
    stats = []
    for module in ['atenciones', 'metas', 'tipos', 'subatenciones']:
        config = MODULES[module]
        if request.user.has_perm(f'gestion.view_{config["model"]._meta.model_name}'):
            stats.append({'titulo': config['title'], 'total': scoped(request.user, config['model']).count(),
                          'url': reverse('gestion:listado', args=[module])})
    return render(request, 'gestion/inicio.html', {'titulo': 'Gestión municipal', 'stats': stats})


@login_required
@require_GET
def listado(request, modulo):
    config = module_config(modulo)
    authorize(request.user, config['model'])
    return render(request, 'gestion/listado.html', list_context(request, modulo))


@login_required
@require_GET
def tabla(request, modulo):
    config = module_config(modulo)
    authorize(request.user, config['model'])
    response = render(request, 'gestion/_tabla.html', list_context(request, modulo))
    response['Cache-Control'] = 'no-store'
    return response


def form_view(request, modulo, pk=None):
    config = module_config(modulo)
    model = config['model']
    authorize(request.user, model, 'change' if pk else 'add')
    if modulo == 'delegaciones' and not pk:
        raise PermissionDenied('La creación de delegaciones corresponde a administración técnica.')
    obj = get_object_or_404(scoped(request.user, model), pk=pk) if pk else None
    form = FORMS[modulo](request.POST if request.method == 'POST' else None,
                         request.FILES if request.method == 'POST' else None,
                         instance=obj, user=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                saved = form.save()
                if modulo == 'atenciones':
                    notify_after_commit(saved.delegacion_id)
        except IntegrityError:
            form.add_error(None, 'Ya existe un registro con esos datos. Revisa el nombre y vuelve a guardar.')
        else:
            messages.success(request, 'Los cambios se guardaron correctamente.' if pk else 'El registro se creó correctamente.')
            return redirect('gestion:listado', modulo=modulo)
    return render(request, 'gestion/formulario.html', {
        'form': form, 'obj': obj, 'modulo': modulo,
        'titulo': ('Editar ' if pk else 'Crear ') + config['title'],
        'return_url': reverse('gestion:listado', args=[modulo]),
    })


@login_required
def crear(request, modulo):
    if request.method not in ['GET', 'POST']:
        return HttpResponse(status=405)
    return form_view(request, modulo)


@login_required
def editar(request, modulo, pk):
    if request.method not in ['GET', 'POST']:
        return HttpResponse(status=405)
    return form_view(request, modulo, pk)


def details_for(obj, modulo):
    fields = MODULES[modulo]['columns'] + [('Descripción', 'descripcion')]
    if modulo == 'atenciones':
        fields += [('RUT solicitante', 'solicitante_rut'), ('Subatención', 'subatencion.nombre'),
                   ('Responsable', 'responsable.get_full_name'), ('Delegación', 'delegacion.nombre')]
    details = [{'label': label, 'value': display_value(obj, key)} for label, key in fields if key != 'responsable.get_full_name']
    if modulo == 'atenciones':
        details.append({'label': 'Responsable', 'value': obj.responsable.get_full_name() or obj.responsable.username})
    return details


@login_required
@require_GET
def detalle(request, modulo, pk):
    config = module_config(modulo)
    authorize(request.user, config['model'])
    obj = get_object_or_404(scoped(request.user, config['model']), pk=pk)
    name = config['model']._meta.model_name
    return render(request, 'gestion/detalle.html', {
        'obj': obj, 'modulo': modulo, 'titulo': str(obj), 'details': details_for(obj, modulo),
        'can_change': request.user.has_perm(f'gestion.change_{name}'),
        'can_delete': modulo != 'delegaciones' and request.user.has_perm(f'gestion.delete_{name}'),
        'return_url': reverse('gestion:listado', args=[modulo]),
    })


@login_required
@require_POST
def archivar(request, modulo, pk):
    config = module_config(modulo)
    authorize(request.user, config['model'], 'delete')
    if modulo == 'delegaciones':
        raise PermissionDenied('La delegación activa no se puede archivar desde este módulo.')
    obj = get_object_or_404(scoped(request.user, config['model']), pk=pk)
    try:
        with transaction.atomic():
            # Referenced catalogues stay usable until their business records are resolved.
            if modulo in ['tipos', 'subatenciones'] and obj.atencion_set.filter(deleted_at__isnull=True).exists():
                raise ProtectedError('Registro relacionado', [obj])
            if modulo == 'tipos' and obj.subatencion_set.filter(deleted_at__isnull=True).exists():
                raise ProtectedError('Subatenciones relacionadas', [obj])
            obj.deleted_at = timezone.now()
            obj.save(update_fields=['deleted_at', 'updated_at'])
            if modulo == 'atenciones':
                notify_after_commit(obj.delegacion_id)
    except ProtectedError:
        messages.error(request, 'Este registro tiene relaciones vigentes. Revisa las atenciones o subatenciones antes de archivarlo.')
    else:
        messages.success(request, 'El registro se archivó correctamente.')
    return redirect('gestion:listado', modulo=modulo)


@login_required
@require_GET
def exportar(request, modulo):
    config = module_config(modulo)
    authorize(request.user, config['model'])
    state = state_for(request, modulo)
    query = query_for(request.user, modulo, state)
    book = Workbook(write_only=True)
    sheet = book.create_sheet(config['title'][:31])
    sheet.append([title for title, _ in config['columns']])
    for obj in query.iterator(chunk_size=1000):
        cells = []
        for _, key in config['columns']:
            value = display_value(obj, key)
            # Treat user-entered =,+,-,@ text as text, never as spreadsheet formulas.
            cell = WriteOnlyCell(sheet, value=value)
            cell.data_type = 's'
            cells.append(cell)
        sheet.append(cells)
    stream = BytesIO()
    book.save(stream)
    response = HttpResponse(stream.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="sgr-{modulo}.xlsx"'
    response['Cache-Control'] = 'no-store'
    return response


@login_required
@require_GET
def subatenciones(request):
    authorize(request.user, Atencion)
    tipo = request.GET.get('tipo', '')
    if not tipo.isdigit() or len(tipo) > 12:
        return JsonResponse({'error': 'Selecciona un tipo válido.'}, status=400)
    # Unknown and foreign IDs have the same empty result.
    query = scoped(request.user, SubAtencion).filter(tipo_id=tipo, estado='Activo', tipo__estado='Activo', tipo__deleted_at__isnull=True)
    return JsonResponse({'results': list(query.values('id', 'nombre'))})


def own_records(user):
    if not is_cliente(user):
        raise PermissionDenied('Esta sección está disponible para cuentas de clientes.')
    return Atencion.objects.filter(cliente=user, delegacion_id=delegation_id(user)).select_related('tipo', 'subatencion')


@login_required
@require_GET
def portal(request):
    from django.core.paginator import Paginator
    query = own_records(request.user)
    page = Paginator(query, 15).get_page(request.GET.get('pagina'))
    return render(request, 'gestion/portal.html', {'titulo': 'Mis atenciones', 'page_obj': page})


@login_required
@require_GET
def portal_detalle(request, pk):
    obj = get_object_or_404(own_records(request.user), pk=pk)
    return render(request, 'gestion/detalle.html', {
        'titulo': f'Mi atención {obj.folio}', 'obj': obj, 'modulo': 'atenciones',
        'details': details_for(obj, 'atenciones'), 'can_change': False, 'can_delete': False,
        'return_url': reverse('gestion:portal'),
    })


@require_GET
def health(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    import os
    return JsonResponse({'status': 'ok', 'service': 'SGR Django', 'commit': os.environ.get('APP_COMMIT', 'local')})
