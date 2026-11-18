"""Tablero de correspondencia con las mismas reglas de ámbito que sus registros."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .access import authorize, scoped
from .models import Carta


# Inferencia documentada en docs/tablero-canvas.md; no son estados nuevos.
TRANSICIONES_CARTA = {
    'En proceso': ('Aprobada', 'No aplica'),
    'Aprobada': ('Finalizada',),
}


@login_required
@require_GET
def cartas_tablero(request):
    authorize(request.user, Carta)
    query = scoped(request.user, Carta).select_related('encargado').order_by(
        F('fecha_actividad').asc(nulls_last=True), 'fecha', 'pk')
    columnas = []
    for (estado, _), color in zip(Carta.ESTADOS, ['proceso', 'ingresado', 'realizado', 'pendiente']):
        registros = query.filter(estado=estado)
        columnas.append({'estado': estado, 'color': color, 'cantidad': registros.count(),
                         'registros': registros[:100], 'destinos': TRANSICIONES_CARTA.get(estado, ())})
    return render(request, 'gestion/cartas_tablero.html', {
        'titulo': 'Tubo de cartas', 'modulo': 'cartas', 'columnas': columnas, 'total': query.count(),
    })


@login_required
@require_POST
def cartas_mover(request, pk):
    authorize(request.user, Carta, 'change')
    with transaction.atomic():
        obj = get_object_or_404(scoped(request.user, Carta).select_for_update(), pk=pk)
        destino = request.POST.get('estado')
        if request.POST.get('desde') != obj.estado or destino not in TRANSICIONES_CARTA.get(obj.estado, ()):
            messages.error(request, 'La carta cambió de estado o la transición no está permitida. Revisa el tablero.')
        else:
            obj.estado = destino
            obj.save(update_fields=['estado', 'updated_at'])
            messages.success(request, f'{obj.codigo}: {destino}.')
    return redirect('gestion:cartas_tablero')
