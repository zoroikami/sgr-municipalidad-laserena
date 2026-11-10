from django import forms
from django.contrib.auth import get_user_model
from cuentas.rut import RUT_INPUT_HELP

from .access import delegation_id
from .models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion


class AtencionFilterForm(forms.Form):
    responsable = forms.ModelChoiceField(
        label='Responsable', required=False, queryset=get_user_model().objects.none(),
        empty_label='Todos los responsables', widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'invalid_choice': 'Selecciona un responsable de tu delegación.'},
    )
    desde = forms.DateField(
        label='Desde', required=False, input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
        error_messages={'invalid': 'Ingresa una fecha Desde válida.'},
    )
    hasta = forms.DateField(
        label='Hasta', required=False, input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
        error_messages={'invalid': 'Ingresa una fecha Hasta válida.'},
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        org = delegation_id(user)
        # Include archived assignments so that archiving a last record keeps the filter valid.
        assigned = Atencion.all_objects.filter(delegacion_id=org).order_by().values('responsable_id')
        self.fields['responsable'].queryset = get_user_model().objects.filter(
            pk__in=assigned, perfil__delegacion_id=org,
        ).order_by('first_name', 'last_name', 'username')
        self.fields['responsable'].label_from_instance = lambda account: account.get_full_name() or account.username

    def clean(self):
        dates = super().clean()
        start = dates.get('desde')
        end = dates.get('hasta')
        if start and end and end < start:
            self.add_error('hasta', 'La fecha Hasta debe ser igual o posterior a la fecha Desde.')
        return dates


class ScopedModelForm(forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        self.user = user
        self.org_id = delegation_id(user)
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'delegacion_id'):
            self.instance.delegacion_id = self.org_id
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-select' if isinstance(field.widget, forms.Select) else 'form-control')
            field.widget.attrs.setdefault('aria-describedby', f'id_{name}_help id_{name}_errors')
            if name == 'descripcion':
                field.help_text = f'Máximo {field.max_length} caracteres.'
                field.error_messages['max_length'] = f'La descripción debe tener como máximo {field.max_length} caracteres.'

    def clean_nombre(self):
        name = self.cleaned_data['nombre'].strip()
        query = self._meta.model.all_objects.filter(nombre__iexact=name)
        if self._meta.model is Delegacion:
            query = query.filter(pk=self.org_id)
        else:
            query = query.filter(delegacion_id=self.org_id)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError('Ya existe un registro con este nombre en tu delegación, incluido el archivo.')
        return name


class ItemMetaForm(ScopedModelForm):
    meta_cantidad = forms.IntegerField(label='Cantidad de meta', disabled=True, initial=100,
                                     help_text='Se asigna automáticamente. Las metas existentes conservan su cantidad.')

    class Meta:
        model = ItemMeta
        fields = ['nombre', 'descripcion', 'unidad_medida', 'meta_cantidad', 'estado']


class TipoAtencionForm(ScopedModelForm):
    class Meta:
        model = TipoAtencion
        fields = ['nombre', 'descripcion', 'estado']


class SubAtencionForm(ScopedModelForm):
    class Meta:
        model = SubAtencion
        fields = ['nombre', 'tipo', 'descripcion', 'estado']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoAtencion.objects.filter(delegacion_id=self.org_id, estado='Activo')


class DelegacionForm(ScopedModelForm):
    class Meta:
        model = Delegacion
        fields = ['nombre', 'direccion', 'comuna', 'estado']


class AtencionForm(ScopedModelForm):
    class Meta:
        model = Atencion
        fields = ['solicitante_nombre', 'solicitante_rut', 'tipo', 'subatencion', 'cliente', 'descripcion', 'estado']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.instance.responsable = self.user
        self.fields['tipo'].queryset = TipoAtencion.objects.filter(delegacion_id=self.org_id, estado='Activo')
        subquery = SubAtencion.objects.filter(delegacion_id=self.org_id, estado='Activo', tipo__estado='Activo', tipo__deleted_at__isnull=True)
        selected_type = self.data.get('tipo') if self.is_bound else self.initial.get('tipo')
        if selected_type and str(selected_type).isdigit():
            subquery = subquery.filter(tipo_id=selected_type)
        self.fields['subatencion'].queryset = subquery
        self.fields['cliente'].queryset = get_user_model().objects.filter(
            perfil__delegacion_id=self.org_id, groups__name='Cliente', is_active=True).distinct()
        self.fields['cliente'].label_from_instance = lambda user: user.get_full_name() or user.username
        self.fields['solicitante_rut'].help_text = RUT_INPUT_HELP
        self.fields['solicitante_rut'].widget.attrs.update({'placeholder': '12345678-5', 'spellcheck': 'false'})


FORMS = {'metas': ItemMetaForm, 'atenciones': AtencionForm, 'tipos': TipoAtencionForm,
         'subatenciones': SubAtencionForm, 'delegaciones': DelegacionForm}
