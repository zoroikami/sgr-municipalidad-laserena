from django import forms
from .models import Delegacion, Rol, Usuario, ItemMeta, TipoAtencion, SubAtencion, Atencion
from rut import normalize_rut, RutError

class DelegacionForm(forms.ModelForm):
    class Meta:
        model = Delegacion
        fields = ['codigo', 'nombre', 'direccion', 'comuna', 'estado']

class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ['codigo', 'nombre', 'descripcion', 'permisos', 'alcance', 'estado']

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['rut', 'nombre', 'email', 'rol', 'delegacion', 'estado', 'foto_perfil']

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if rut:
            try:
                return normalize_rut(rut)
            except RutError as err:
                raise forms.ValidationError(str(err))
        return rut

class ItemMetaForm(forms.ModelForm):
    class Meta:
        model = ItemMeta
        fields = ['codigo', 'nombre', 'descripcion', 'unidad_medida', 'meta_cantidad', 'estado']

class TipoAtencionForm(forms.ModelForm):
    class Meta:
        model = TipoAtencion
        fields = ['codigo', 'nombre', 'descripcion', 'estado']

class SubAtencionForm(forms.ModelForm):
    class Meta:
        model = SubAtencion
        fields = ['codigo', 'nombre', 'tipo', 'estado']

class AtencionForm(forms.ModelForm):
    class Meta:
        model = Atencion
        fields = ['folio', 'solicitante_rut', 'solicitante_nombre', 'delegacion', 'tipo', 'subtipo', 'descripcion', 'responsable_nombre']

    def clean_solicitante_rut(self):
        rut = self.cleaned_data.get('solicitante_rut')
        if rut:
            try:
                return normalize_rut(rut)
            except RutError as err:
                raise forms.ValidationError(str(err))
        return rut
