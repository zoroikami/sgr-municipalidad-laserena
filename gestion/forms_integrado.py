from django import forms
from django.contrib.auth import get_user_model

from .access import scoped
from .forms import ScopedModelForm
from .integrado import validar_fecha
from .integrado import CARGOS
from .models import ActividadSGR, AusenciaSGR, GestionTubo, Organizacion, Atencion, ItemMeta


def cuentas_ambito(org_id):
    users = get_user_model().objects.filter(is_active=True).exclude(groups__name='Cliente')
    return users.filter(perfil__delegacion_id=org_id) if org_id else users.none()


class RelacionesForm(ScopedModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A superuser's submitted delegation also constrains every relation.
        org = self.data.get('delegacion') if self.is_bound and self.user.is_superuser and not self.instance.pk else self.org_id
        self.rel_org = int(org) if str(org).isdigit() else None


class OrganizacionForm(ScopedModelForm):
    class Meta:
        model = Organizacion
        fields = ['nombre', 'familia', 'subfamilia', 'domicilio', 'socios_activos', 'fecha_constitucion',
                  'registro_pj', 'fecha_inscripcion', 'registro_directiva', 'verificada', 'descripcion', 'estado']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_constitucion', 'fecha_inscripcion']}


class GestionTuboForm(RelacionesForm):
    class Meta:
        model = GestionTubo
        fields = ['nombre', 'descripcion', 'fecha_solicitud', 'origen', 'solicitante', 'territorio',
                  'responsable', 'fecha_compromiso', 'apoyo', 'observaciones', 'atencion', 'organizacion']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_solicitud', 'fecha_compromiso']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org)
        for campo, model in [('atencion', Atencion), ('organizacion', Organizacion)]:
            self.fields[campo].queryset = model.objects.filter(delegacion_id=self.rel_org)


class ActividadSGRForm(RelacionesForm):
    class Meta:
        model = ActividadSGR
        fields = ['item', 'cargo', 'fecha', 'descripcion', 'solicitante_nombre', 'solicitante_telefono',
                  'solicitante_delegado', 'es_accion', 'felicitacion', 'respaldo_formal']
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.responsable = self.user
        self.fields['item'].queryset = ItemMeta.objects.filter(delegacion_id=self.rel_org, estado='Activo')
        self.fields['solicitante_telefono'].help_text = 'Sin nombre y teléfono del usuario, la actividad no suma puntaje.'
        if not self.user.has_perm('gestion.validar_delegado'):
            self.fields.pop('respaldo_formal')
        else:
            self.fields['responsable'] = forms.ModelChoiceField(label='Funcionario responsable',
                queryset=cuentas_ambito(self.rel_org), initial=self.user.pk)

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        validar_fecha(fecha)
        return fecha


class AusenciaSGRForm(RelacionesForm):
    class Meta:
        model = AusenciaSGR
        fields = ['responsable', 'desde', 'hasta', 'motivo']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}) for key in ['desde', 'hasta']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.registrado_por = self.user
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org)


class PeriodoSGRForm(forms.Form):
    anio = forms.IntegerField(label='Año', min_value=2020, max_value=2100)
    trimestre = forms.TypedChoiceField(label='Trimestre', choices=[(n, n) for n in range(1, 5)], coerce=int)
    responsable = forms.ModelChoiceField(label='Funcionario', queryset=get_user_model().objects.none())

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = get_user_model().objects.filter(
            perfil__delegacion_id__in=scoped(user, ItemMeta).values('delegacion_id'), is_active=True).exclude(groups__name='Cliente')


class MetaSGRForm(forms.ModelForm):
    cargo_sgr = forms.ChoiceField(label='Cargo municipal', required=False, choices=[('', 'Común a todos los cargos')] + CARGOS)
    class Meta:
        model = ItemMeta
        fields = ['meta_cantidad', 'ponderador', 'cargo_sgr']
