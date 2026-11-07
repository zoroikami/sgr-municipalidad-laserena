from django import forms
from django.contrib.auth import get_user_model

from .access import delegation_id
from .models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion


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
        self.fields['solicitante_rut'].help_text = 'Ingresa un RUT válido con su dígito verificador.'


FORMS = {'metas': ItemMetaForm, 'atenciones': AtencionForm, 'tipos': TipoAtencionForm,
         'subatenciones': SubAtencionForm, 'delegaciones': DelegacionForm}
