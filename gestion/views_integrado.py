from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .access import authorize, scoped
from .forms_integrado import ActividadSGRForm, AusenciaSGRForm, PeriodoSGRForm, MetaSGRForm, ReclamoSGRForm
from .integrado import (resultado_final, resultado_item, semaforo, trimestres_anteriores, limites_trimestre,
                        CARGOS, MAX_FELICITACIONES)
from .models import ActividadSGR, AusenciaSGR, GestionTubo, ItemMeta, ReclamoSGR


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


def initial_formulario(request):
    """Selección previa (delegación, funcionario, cargo) que acota las listas dependientes."""
    return {name: request.GET[name] for name in ('delegacion', 'responsable', 'cargo')
            if request.GET.get(name, '').isascii() and request.GET.get(name, '').replace('_', '').isalnum()}


@login_required
@require_GET
def items_actividad(request):
    """RF-003: ítems vigentes del cargo del funcionario elegido, para recargar el formulario."""
    authorize(request.user, ActividadSGR, 'add')
    form = ActividadSGRForm(user=request.user, initial=initial_formulario(request))
    return JsonResponse({
        'cargo': form.cargo_efectivo, 'cargo_fijo': bool(form.cargo_asignado),
        'items': [{'id': item.pk, 'nombre': item.nombre} for item in form.fields['item'].queryset],
    })


@login_required
def registrar(request, ausencia=False, reclamo=False):
    if request.method not in ('GET', 'POST'):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET', 'POST'])
    if reclamo:
        model, form_class, titulo, aviso = ReclamoSGR, ReclamoSGRForm, 'Registrar reclamo', 'Reclamo registrado. Descuenta 20% del resultado del funcionario.'
    elif ausencia:
        model, form_class, titulo, aviso = AusenciaSGR, AusenciaSGRForm, 'Registrar ausencia', 'Ausencia registrada.'
    else:
        model, form_class, titulo, aviso = ActividadSGR, ActividadSGRForm, 'Registrar actividad SGR', None
    authorize(request.user, model, 'add')
    if (ausencia or reclamo) and not request.user.has_perm('gestion.validar_delegado'):
        raise PermissionDenied('Las ausencias y los reclamos deben ser registrados por el delegado.')
    form = form_class(request.POST if request.method == 'POST' else None, user=request.user,
                      initial=initial_formulario(request))
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if model is ActividadSGR and obj.felicitacion and obj.respaldo_formal and request.user.has_perm('gestion.validar_delegado'):
            obj.informado_por = request.user
        try:
            with transaction.atomic():
                obj.full_clean()
                obj.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, aviso or f'Actividad registrada. {obj.motivo_puntaje}')
            return redirect('gestion:resultados_sgr')
    return render(request, 'gestion/formulario.html', {'titulo': titulo,
        'items_url': reverse('gestion:items_actividad') if model is ActividadSGR else '',
        'form': form, 'sgr_section': True, 'return_url': reverse('gestion:resultados_sgr')})


@login_required
@require_GET
def resultados(request):
    authorize(request.user, ActividadSGR)
    hoy = timezone.localdate()
    data = request.GET or {'anio': hoy.year, 'trimestre': (hoy.month - 1) // 3 + 1, 'responsable': request.user.pk}
    form = PeriodoSGRForm(data, user=request.user)
    rows, actividades, ausencias, reclamos = [], [], [], []
    total = base = None
    equipo, detalle, objetivo_equipo = [], None, None
    if form.is_valid():
        anio, trimestre = form.cleaned_data['anio'], form.cleaned_data['trimestre']
        inicio, fin = limites_trimestre(anio, trimestre)
        funcionario = form.cleaned_data['responsable']
        org = funcionario.perfil.delegacion_id
        metas = list(scoped(request.user, ItemMeta).filter(delegacion_id=org, estado='Activo'))
        todos = list(scoped(request.user, ActividadSGR).filter(fecha__range=(inicio, fin)).select_related('item', 'responsable'))
        todas_ausencias = list(scoped(request.user, AusenciaSGR).filter(desde__lte=fin, hasta__gte=inicio))
        gestiones = list(scoped(request.user, GestionTubo).filter(fecha_solicitud__range=(inicio, fin)).only('responsable_id', 'estado'))
        todos_reclamos = list(scoped(request.user, ReclamoSGR).filter(fecha__range=(inicio, fin)).select_related('responsable'))
        # Hoja RECLAMOS: no pueden repetirse más de dos trimestres seguidos (se informa a RRHH).
        previos = [limites_trimestre(a, t) for a, t in trimestres_anteriores(anio, trimestre, 2)]
        con_reclamos_previos = [set(scoped(request.user, ReclamoSGR).filter(fecha__range=rango).values_list('responsable_id', flat=True))
                                for rango in previos]
        ultimos = dict(scoped(request.user, ActividadSGR).filter(fecha__lte=fin).values('responsable_id')
                       .annotate(ultimo=Max('fecha')).values_list('responsable_id', 'ultimo'))
        cargos = dict(CARGOS)
        objetivo_equipo = semaforo(None, inicio, fin, hoy, [])['objetivo']
        for user in form.fields['responsable'].queryset.filter(perfil__delegacion_id=org).select_related('perfil'):
            registros = [a for a in todos if a.responsable_id == user.pk]
            libres = [a for a in todas_ausencias if a.responsable_id == user.pk]
            propias = [g for g in gestiones if g.responsable_id == user.pk]
            quejas = [r for r in todos_reclamos if r.responsable_id == user.pk]
            metricas = [resultado_item(meta, registros, libres, inicio, fin, propias) for meta in metas
                        if not meta.cargo_sgr or meta.cargo_sgr == user.perfil.cargo_sgr]
            peso = sum(row['meta'].ponderador for row in metricas if row['porcentaje'] is not None)
            parcial = sum(row['ponderado'] for row in metricas if row['ponderado'] is not None) * 100 / peso if peso else None
            felicitaciones = sum(1 for a in registros if a.felicitacion and a.puntuable)
            final = resultado_final(parcial, felicitaciones, len(quejas))
            luz = semaforo(final, inicio, fin, hoy, libres)
            ultimo = ultimos.get(user.pk)
            fila = {'funcionario': user, 'cargo': cargos.get(user.perfil.cargo_sgr, 'Sin cargo asignado'),
                    'base': parcial, 'porcentaje': final, 'felicitaciones': felicitaciones,
                    'felicitaciones_validas': min(felicitaciones, MAX_FELICITACIONES), 'reclamos': len(quejas),
                    'semaforo': luz, 'ultimo': ultimo, 'dias_sin_ingreso': (hoy - ultimo).days if ultimo else None,
                    'ingresos': len(registros),
                    'diarios': Decimal(len(registros)) / luz['transcurridos'] if luz['transcurridos'] else None,
                    'rrhh': bool(quejas) and all(user.pk in previo for previo in con_reclamos_previos)}
            equipo.append(fila)
            if user.pk == funcionario.pk:
                rows, actividades, ausencias, reclamos, total, base, detalle = metricas, registros, libres, quejas, final, parcial, fila
    valores = [r['porcentaje'] for r in equipo if r['porcentaje'] is not None]
    total_equipo = sum(valores) / len(valores) if valores else None
    equipo.sort(key=lambda r: (r['porcentaje'] is None, -(r['porcentaje'] or 0)))
    resumen = {color: sum(1 for r in equipo if r['semaforo']['color'] == color) for color in ('verde', 'naranjo', 'rojo')}
    return render(request, 'gestion/resultados_sgr.html', {'titulo': 'Resultados SGR', 'sgr_section': True, 'filter_form': form,
        'resultados': rows, 'actividades': actividades, 'ausencias': ausencias, 'reclamos': reclamos, 'total': total, 'base': base,
        'detalle': detalle, 'equipo': equipo, 'total_equipo': total_equipo, 'resumen_semaforo': resumen,
        'objetivo_equipo': objetivo_equipo})


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
        'sgr_section': True, 'return_url': reverse('gestion:resultados_sgr')})
