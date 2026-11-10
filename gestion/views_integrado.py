from calendar import monthrange
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .access import authorize, scoped
from .forms_integrado import ActividadSGRForm, AusenciaSGRForm, PeriodoSGRForm, MetaSGRForm
from .integrado import resultado_item
from .models import ActividadSGR, AusenciaSGR, GestionTubo, ItemMeta


@login_required
@require_GET
def tablero(request):
    authorize(request.user, GestionTubo)
    query = scoped(request.user, GestionTubo).select_related('responsable', 'atencion', 'organizacion')
    total = query.count()
    realizados = query.filter(estado='Realizado').count()
    columnas = []
    siguientes = {'Ingresado': 'Pendiente', 'Pendiente': 'En proceso', 'En proceso': 'Realizado'}
    colores = ['ingresado', 'pendiente', 'proceso', 'realizado']
    for (estado, _), color in zip(GestionTubo.ESTADOS, colores):
        registros = query.filter(estado=estado)
        columnas.append({'estado': estado, 'color': color, 'cantidad': registros.count(),
                         'registros': registros[:100], 'siguiente': siguientes.get(estado)})
    return render(request, 'gestion/tablero.html', {'titulo': 'Tubo de trabajo', 'columnas': columnas,
        'total': total, 'realizados': realizados, 'porcentaje': realizados * 100 / total if total else 0,
        'proceso': query.filter(estado='En proceso').count(), 'pendientes': query.filter(estado='Pendiente').count()})


@login_required
@require_POST
def mover(request, pk):
    authorize(request.user, GestionTubo, 'change')
    siguientes = {'Ingresado': 'Pendiente', 'Pendiente': 'En proceso', 'En proceso': 'Realizado'}
    with transaction.atomic():
        obj = get_object_or_404(scoped(request.user, GestionTubo).select_for_update(), pk=pk)
        destino = siguientes.get(obj.estado)
        if not destino or request.POST.get('desde') != obj.estado:
            messages.error(request, 'La gestión cambió de estado. Revisa el tablero antes de continuar.')
        else:
            obj.estado = destino
            obj.save(update_fields=['estado', 'updated_at'])
            messages.success(request, f'{obj.codigo}: {destino}.')
    return redirect('gestion:tablero')


@login_required
def registrar(request, ausencia=False):
    if request.method not in ('GET', 'POST'):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET', 'POST'])
    model, form_class = (AusenciaSGR, AusenciaSGRForm) if ausencia else (ActividadSGR, ActividadSGRForm)
    authorize(request.user, model, 'add')
    if ausencia and not request.user.has_perm('gestion.validar_delegado'):
        raise PermissionDenied('Las ausencias deben ser registradas por el delegado.')
    form = form_class(request.POST if request.method == 'POST' else None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if not ausencia and obj.felicitacion and obj.respaldo_formal and request.user.has_perm('gestion.validar_delegado'):
            obj.informado_por = request.user
        try:
            with transaction.atomic():
                obj.full_clean()
                obj.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Ausencia registrada.' if ausencia else f'Actividad registrada. {obj.motivo_puntaje}')
            return redirect('gestion:resultados_sgr')
    return render(request, 'gestion/formulario.html', {'titulo': 'Registrar ausencia' if ausencia else 'Registrar actividad SGR',
        'form': form, 'return_url': reverse('gestion:resultados_sgr')})


@login_required
@require_GET
def resultados(request):
    authorize(request.user, ActividadSGR)
    hoy = timezone.localdate()
    data = request.GET or {'anio': hoy.year, 'trimestre': (hoy.month - 1) // 3 + 1, 'responsable': request.user.pk}
    form = PeriodoSGRForm(data, user=request.user)
    rows, actividades, ausencias = [], [], []
    total = None
    equipo = []
    if form.is_valid():
        anio, trimestre = form.cleaned_data['anio'], form.cleaned_data['trimestre']
        mes = (trimestre - 1) * 3 + 1
        inicio, fin = date(anio, mes, 1), date(anio, mes + 2, monthrange(anio, mes + 2)[1])
        funcionario = form.cleaned_data['responsable']
        metas = list(scoped(request.user, ItemMeta).filter(delegacion_id=funcionario.perfil.delegacion_id, estado='Activo'))
        todos = list(scoped(request.user, ActividadSGR).filter(fecha__range=(inicio, fin)).select_related('item', 'responsable'))
        todas_ausencias = list(scoped(request.user, AusenciaSGR).filter(desde__lte=fin, hasta__gte=inicio))
        for user in form.fields['responsable'].queryset.filter(perfil__delegacion_id=funcionario.perfil.delegacion_id):
            registros = [a for a in todos if a.responsable_id == user.pk]
            libres = [a for a in todas_ausencias if a.responsable_id == user.pk]
            metricas = [resultado_item(meta, registros, libres, inicio, fin) for meta in metas
                        if not meta.cargo_sgr or meta.cargo_sgr == user.perfil.cargo_sgr]
            peso = sum(row['meta'].ponderador for row in metricas if row['porcentaje'] is not None)
            resultado = sum(row['ponderado'] for row in metricas if row['ponderado'] is not None) * 100 / peso if peso else None
            equipo.append({'funcionario': user, 'porcentaje': resultado})
            if user.pk == funcionario.pk:
                rows, actividades, ausencias, total = metricas, registros, libres, resultado
    valores = [r['porcentaje'] for r in equipo if r['porcentaje'] is not None]
    return render(request, 'gestion/resultados_sgr.html', {'titulo': 'Resultados SGR', 'filter_form': form,
        'resultados': rows, 'actividades': actividades, 'ausencias': ausencias, 'total': total,
        'equipo': equipo, 'total_equipo': sum(valores) / len(valores) if valores else None})


@login_required
def configurar_meta(request, pk):
    if request.method not in ('GET', 'POST'):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET', 'POST'])
    authorize(request.user, ItemMeta, 'change')
    if not request.user.has_perm('gestion.validar_delegado'):
        raise PermissionDenied('La configuración corresponde al delegado.')
    obj = get_object_or_404(scoped(request.user, ItemMeta), pk=pk)
    form = MetaSGRForm(request.POST if request.method == 'POST' else None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Meta y ponderador actualizados.')
        return redirect('gestion:resultados_sgr')
    return render(request, 'gestion/formulario.html', {'titulo': f'Configurar {obj.nombre}', 'form': form,
        'return_url': reverse('gestion:resultados_sgr')})
