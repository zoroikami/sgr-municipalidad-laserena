"""Un ModelForm por mantenedor, reutilizado al crear y editar."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from rut import normalize_rut, RutError
from .models import Delegacion, Rol, Usuario, ItemMeta, TipoAtencion, SubAtencion, Atencion


class AccesoForm(AuthenticationForm):
    username = forms.CharField(label='Usuario, correo o RUT')

    def clean(self):
        identifier = self.cleaned_data.get('username', '').strip()
        try:
            rut = normalize_rut(identifier)
        except RutError:
            rut = identifier
        user = get_user_model().objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier) | Q(rut__iexact=rut)).first()
        if user:
            self.cleaned_data['username'] = user.username
        return super().clean()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.estado != 'Activo':
            raise ValidationError('La cuenta está inactiva o suspendida.')


class CatalogoForm(forms.ModelForm):
    """Estilos Bootstrap y validación del nombre en un único lugar."""
    def __init__(self, *args, user=None, **kwargs):
        self.actor = user
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            if name in ('descripcion',):
                field.widget.attrs['rows'] = 3
            if name == 'estado':
                active = 'Activa' if self._meta.model in (Delegacion, SubAtencion) else 'Activo'
                inactive = 'Inactiva' if active == 'Activa' else 'Inactivo'
                self.fields[name] = forms.ChoiceField(label='Estado', choices=[(active, active), (inactive, inactive)], widget=forms.Select(attrs={'class':'form-select'}))

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if len(nombre) < 3:
            raise ValidationError('Ingrese un nombre de al menos 3 caracteres.')
        return nombre


class DelegacionForm(CatalogoForm):
    class Meta:
        model = Delegacion
        fields = ['nombre', 'direccion', 'comuna', 'estado']
        labels = {'nombre':'Nombre', 'direccion':'Dirección', 'comuna':'Comuna'}


class RolForm(CatalogoForm):
    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion', 'permisos', 'alcance', 'estado']
        labels = {'descripcion':'Descripción', 'permisos':'Permisos', 'alcance':'Alcance'}
        widgets = {'permisos':forms.Select(choices=[('total','Administración total'), ('coordinacion','Coordinación'), ('delegacion','Delegación'), ('operador','Operador'), ('lectura','Solo lectura')])}


class ItemMetaForm(CatalogoForm):
    class Meta:
        model = ItemMeta
        fields = ['nombre', 'descripcion', 'unidad_medida', 'meta_cantidad', 'estado']
        labels = {'descripcion':'Descripción', 'unidad_medida':'Unidad de medida', 'meta_cantidad':'Meta (cantidad)'}


class TipoAtencionForm(CatalogoForm):
    class Meta:
        model = TipoAtencion
        fields = ['nombre', 'descripcion', 'estado']
        labels = {'descripcion':'Descripción'}


class SubAtencionForm(CatalogoForm):
    class Meta:
        model = SubAtencion
        fields = ['nombre', 'tipo', 'estado']
        labels = {'tipo':'Tipo de atención'}


class UsuarioForm(CatalogoForm):
    password = forms.CharField(label='Contraseña', required=False, strip=False, widget=forms.PasswordInput, help_text='Al crear, ingrese una contraseña de al menos 8 caracteres. Al editar, déjela vacía para conservar la actual.')

    class Meta:
        model = Usuario
        fields = ['rut', 'nombre', 'email', 'rol', 'delegacion', 'estado']
        labels = {'rut':'RUT', 'nombre':'Nombre completo', 'email':'Correo electrónico', 'rol':'Rol', 'delegacion':'Delegación'}
        widgets = {'rut':forms.TextInput(attrs={'data-rut':'', 'maxlength':12, 'placeholder':'12.345.678-5', 'aria-describedby':'id_rut_feedback id_rut_helptext'})}
        help_texts = {'rut':'Incluye siempre el dígito verificador (número o K). Ejemplo: 12.345.678-5.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('rut', 'rol', 'delegacion'):
            self.fields[name].required = True
        self.fields['password'].required = not self.instance.pk
        if self.actor and not self.actor.is_superuser and self.actor.rol_id not in ('ROL01', 'ROL02') and not (self.actor.rol and self.actor.rol.permisos == 'total'):
            self.fields['rol'].queryset = Rol.objects.filter(
                codigo__in=['ROL04', 'ROL05']).exclude(permisos='total')
            self.fields['delegacion'].queryset = Delegacion.objects.filter(codigo=self.actor.delegacion_id)

    def clean_rut(self):
        try:
            return normalize_rut(self.cleaned_data['rut'])
        except RutError as exc:
            raise ValidationError(str(exc)) from exc

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un usuario con este correo.')
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password:
            validate_password(password, self.instance)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.pk:
            user.username = user.email
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            self.save_m2m()
        return user


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
