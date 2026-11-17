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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encargado'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)
        self.fields['encargado'].label_from_instance = lambda user: user.get_full_name() or user.username
        self.fields['numero_ingreso'].help_text = 'Número asignado por oficina de partes, distinto del código automático CAR.'
