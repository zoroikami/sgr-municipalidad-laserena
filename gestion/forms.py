from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
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
        # Include archived assignments so that archiving a last record keeps the filter valid.
        assigned = Atencion.all_objects.all()
        accounts = get_user_model().objects.all()
        if not user.is_superuser:
            org = delegation_id(user)
            assigned = assigned.filter(delegacion_id=org)
            accounts = accounts.filter(Q(perfil__delegacion_id=org) | Q(is_superuser=True))
        self.fields['responsable'].queryset = accounts.filter(
            pk__in=assigned.order_by().values('responsable_id'),
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
        super().__init__(*args, **kwargs)
        self.org_id = None
        if user.is_superuser:
            self.org_id = getattr(self.instance, 'delegacion_id', None)
            if hasattr(self.instance, 'delegacion_id') and not self.instance.pk:
                self.fields['delegacion'] = forms.ModelChoiceField(
                    label='Delegación', queryset=Delegacion.objects.filter(estado='Activo'))
                self.order_fields(['delegacion'])
        else:
            self.org_id = delegation_id(user)
            if hasattr(self.instance, 'delegacion_id'):
                self.instance.delegacion_id = self.org_id
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-select' if isinstance(field.widget, forms.Select) else 'form-control')
            field.widget.attrs.setdefault('aria-describedby', f'id_{name}_help id_{name}_errors')
            if name == 'descripcion':
                field.help_text = f'Máximo {field.max_length} caracteres.'
                field.error_messages['max_length'] = f'La descripción debe tener como máximo {field.max_length} caracteres.'

    def active_catalog(self, model):
        query = model.objects.filter(estado='Activo')
        if self.org_id:
            return query.filter(delegacion_id=self.org_id)
        return query.filter(delegacion__estado='Activo', delegacion__deleted_at__isnull=True)

    def clean(self):
        data = super().clean()
        if data.get('delegacion'):
            self.instance.delegacion = data['delegacion']
            self.org_id = self.instance.delegacion_id
        name = data.get('nombre')
        if name:
            matches = self._meta.model.all_objects.filter(nombre__iexact=name).exclude(pk=self.instance.pk)
            if self._meta.model is Delegacion:
                matches = matches if self.user.is_superuser else matches.filter(pk=self.org_id)
            else:
                matches = matches.filter(delegacion_id=self.org_id)
            if matches.exists():
                self.add_error('nombre', 'Ya existe un registro con este nombre en esa delegación, incluido el archivo.')
        return data


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
        self.fields['tipo'].queryset = self.active_catalog(TipoAtencion)


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
        self.fields['tipo'].queryset = self.active_catalog(TipoAtencion)
        subquery = self.active_catalog(SubAtencion).filter(tipo__estado='Activo', tipo__deleted_at__isnull=True)
        selected_type = self.data.get('tipo') if self.is_bound else self.initial.get('tipo')
        if selected_type and str(selected_type).isdigit():
            subquery = subquery.filter(tipo_id=selected_type)
        self.fields['subatencion'].queryset = subquery
        clients = get_user_model().objects.filter(groups__name='Cliente', is_active=True, is_superuser=False)
        if self.org_id:
            clients = clients.filter(perfil__delegacion_id=self.org_id)
        else:
            clients = clients.filter(perfil__delegacion__estado='Activo', perfil__delegacion__deleted_at__isnull=True)
        self.fields['cliente'].queryset = clients.distinct()
        self.fields['cliente'].label_from_instance = lambda user: user.get_full_name() or user.username
        self.fields['solicitante_rut'].help_text = RUT_INPUT_HELP
        self.fields['solicitante_rut'].widget.attrs.update({'placeholder': '12345678-5', 'spellcheck': 'false'})


FORMS = {'metas': ItemMetaForm, 'atenciones': AtencionForm, 'tipos': TipoAtencionForm,
         'subatenciones': SubAtencionForm, 'delegaciones': DelegacionForm}
