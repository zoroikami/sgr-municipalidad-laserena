"""Reglas compartidas por edición y tableros de seguimiento."""
from django import forms

from .models import Carta, GestionTubo, HistorialEstado


TRANSICIONES_CARTA = {
    'En proceso': ('Aprobada', 'No aplica'),
    'Aprobada': ('Finalizada',),
}
TRANSICIONES_TUBO = {
    'Ingresado': ('Pendiente',),
    'Pendiente': ('En proceso',),
    'En proceso': ('Realizado',),
}


class ObservacionCambioForm(forms.Form):
    observacion = forms.CharField(required=False, max_length=2000)


def configurar_estado_formulario(form, obj):
    """No modifica las clases de formularios que comparten otros módulos."""
    if isinstance(form.instance, Carta):
        estado = obj.estado if obj else 'En proceso'
        permitidos = (estado, *TRANSICIONES_CARTA.get(estado, ())) if obj else (estado,)
        form.fields['estado'].choices = [(s, s) for s in permitidos]
    elif isinstance(obj, GestionTubo):
        permitidos = (obj.estado, *TRANSICIONES_TUBO.get(obj.estado, ()))
        form.fields['estado'] = forms.ChoiceField(label='Estado', choices=[(s, s) for s in permitidos],
            initial=obj.estado, widget=forms.Select(attrs={'class': 'form-select'}))
        form.initial['estado'] = obj.estado
    else:
        return
    if obj:
        form.fields['observacion_estado'] = forms.CharField(label='Observación del cambio de estado',
            required=False, max_length=2000, help_text='Opcional. Se conserva en el historial si cambia el estado.',
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))


def registrar_cambio(obj, anterior, autor, observacion=''):
    """Llamar después de guardar, dentro de la transacción que bloquea el registro."""
    if anterior == obj.estado:
        return
    relacion = 'carta' if isinstance(obj, Carta) else 'gestion_tubo'
    HistorialEstado.objects.create(**{relacion: obj}, estado_anterior=anterior,
        estado_nuevo=obj.estado, autor=autor, observacion=observacion)
