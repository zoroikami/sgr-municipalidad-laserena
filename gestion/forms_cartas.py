from django import forms

from .forms_integrado import RelacionesForm, cuentas_ambito
from .models import Carta


class CartaForm(RelacionesForm):
    # Distinct incoming letters may concern the same activity or topic.
    unique_name = False

    class Meta:
        model = Carta
        fields = ['fecha', 'numero_ingreso', 'para', 'remite', 'telefono', 'nombre',
                  'fecha_actividad', 'encargado', 'estado', 'pronunciamiento', 'derivada_a', 'observacion']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha', 'fecha_actividad']}
        help_texts = {
            'fecha': 'Selecciona el día, mes y año de recepción de la carta.',
            'para': 'Selecciona a quién está dirigida la carta.',
            'remite': 'Escribe el nombre de la persona u organización que envía la carta.',
            'telefono': 'Indica un número de contacto, por ejemplo +56 9 1234 5678.',
            'nombre': 'Resume la actividad o el asunto tratado en la carta.',
            'fecha_actividad': 'Selecciona el día, mes y año de la actividad, si corresponde.',
            'encargado': 'Selecciona al funcionario que hará seguimiento de la carta.',
            'estado': 'Selecciona la etapa actual de tramitación de la carta.',
            'pronunciamiento': 'Escribe la respuesta o decisión emitida sobre la solicitud.',
            'derivada_a': 'Indica la persona o el área a la que se envió la carta para su gestión.',
            'observacion': 'Agrega antecedentes o avances que ayuden al seguimiento de la carta.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encargado'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)
        self.fields['encargado'].label_from_instance = lambda user: user.get_full_name() or user.username
        self.fields['numero_ingreso'].help_text = 'Número asignado por oficina de partes, distinto del código automático CAR.'
