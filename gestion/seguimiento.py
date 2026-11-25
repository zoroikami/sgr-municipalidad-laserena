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
    observacion = forms.CharField(required=False, max_length=2000,
        help_text='Explica el cambio, si corresponde; tu comentario quedará en el historial.')


def configurar_estado_formulario(form, obj):
    """No modifica las clases de formularios que comparten otros módulos."""
    if isinstance(obj, Carta):
        estado = obj.estado
        permitidos = (estado, *TRANSICIONES_CARTA.get(estado, ()))
        form.fields['estado'].choices = [(s, s) for s in permitidos]
    elif isinstance(obj, GestionTubo):
        permitidos = (obj.estado, *TRANSICIONES_TUBO.get(obj.estado, ()))
        form.fields['estado'] = forms.ChoiceField(label='Estado', choices=[(s, s) for s in permitidos],
            initial=obj.estado, help_text='Selecciona la etapa actual o la siguiente para avanzar la gestión.',
            widget=forms.Select(attrs={'class': 'form-select', 'aria-describedby': 'id_estado_help id_estado_errors'}))
        form.initial['estado'] = obj.estado
    else:
        return
    if obj:
        form.fields['observacion_estado'] = forms.CharField(label='Observación del cambio de estado',
            required=False, max_length=2000, help_text='Explica el cambio, si corresponde; se conserva en el historial solo si cambia el estado.',
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                'aria-describedby': 'id_observacion_estado_help id_observacion_estado_errors'}))


def registrar_cambio(obj, anterior, autor, observacion=''):
    """Llamar después de guardar, dentro de la transacción que bloquea el registro."""
    if anterior == obj.estado:
        return
    relacion = 'carta' if isinstance(obj, Carta) else 'gestion_tubo'
    HistorialEstado.objects.create(**{relacion: obj}, estado_anterior=anterior,
        estado_nuevo=obj.estado, autor=autor, observacion=observacion,
        fecha_objetivo=obj.fecha_actividad if isinstance(obj, Carta) else obj.fecha_compromiso)
