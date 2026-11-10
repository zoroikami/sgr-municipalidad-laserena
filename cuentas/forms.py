from io import BytesIO
import warnings

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from PIL import Image, ImageOps, UnidentifiedImageError

from cuentas.rut import RUT_INPUT_HELP, RutError, normalize_rut
from .models import Perfil
from .roles import LOCAL_ROLE_NAMES, ROLE_NAMES
from gestion.delegation import active_delegation

MAX_PHOTO_BYTES = 2 * 1024 * 1024


def validated_photo(upload):
    """Decode the complete file and rewrite pixels, removing supplied names and metadata."""
    if upload.size > MAX_PHOTO_BYTES:
        raise ValidationError('La foto debe pesar hasta 2 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as image:
                image_format = image.format
                if image_format not in ('JPEG', 'PNG'):
                    raise ValidationError('Selecciona una foto JPEG o PNG.')
                image.verify()
            upload.seek(0)
            with Image.open(upload) as image:
                image.load()
                pixels = ImageOps.exif_transpose(image).convert('RGB')
                output = BytesIO()
                pixels.save(output, format=image_format)
        if output.tell() > MAX_PHOTO_BYTES:
            raise ValidationError('La foto debe pesar hasta 2 MiB. Reduce su tamaño.')
        return ContentFile(output.getvalue(), name='foto.' + ('jpg' if image_format == 'JPEG' else 'png'))
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValidationError('No pudimos leer la foto completa. Selecciona un JPEG o PNG válido.') from exc


class MunicipalAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Usuario o correo electrónico', max_length=254)

    def clean(self):
        identifier = self.cleaned_data.get('username', '')
        matches = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier))
        identified = bool(identifier) and matches.count() == 1
        if identified:
            self.cleaned_data['username'] = matches.first().username
        elif identifier:
            # Preserve Django's dummy hash and neutral invalid-login error for unknown/ambiguous IDs.
            self.cleaned_data['username'] = '__sgr_unknown_identity__'
        result = super().clean()
        if not identified:
            raise self.get_invalid_login_error()
        return result


class ProfileForm(forms.ModelForm):
    foto = forms.FileField(label='Nueva foto', required=False,
        widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png'}),
        help_text='JPEG o PNG de hasta 2 MiB. Recorta la imagen antes de guardarla.')
    email = forms.EmailField(label='Correo electrónico')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {'first_name': 'Nombres', 'last_name': 'Apellidos'}

    def clean_foto(self):
        upload = self.cleaned_data.get('foto')
        return validated_photo(upload) if upload else None

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe una cuenta con este correo electrónico.')
        return email


class ManagedUserForm(forms.ModelForm):
    email = forms.EmailField(label='Correo electrónico')
    rut = forms.CharField(label='RUT', max_length=20, help_text=RUT_INPUT_HELP,
                         widget=forms.TextInput(attrs={'placeholder': '12345678-5', 'spellcheck': 'false'}))
    role = forms.ChoiceField(label='Rol', choices=[(name, name) for name in ROLE_NAMES])
    new_password = forms.CharField(label='Contraseña inicial', required=False,
        widget=forms.PasswordInput, help_text='Obligatoria para una cuenta nueva. Al editar, déjala vacía para conservar la contraseña.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        labels = {'username': 'Usuario', 'first_name': 'Nombres', 'last_name': 'Apellidos', 'is_active': 'Cuenta activa'}

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        from gestion.models import Delegacion
        self.actor = actor
        self.creating = self.instance.pk is None
        self.fields['new_password'].required = self.creating
        if self.creating:
            self.initial['role'] = 'Operador / Funcionario'
        self.fields['role'].choices = [(name, name) for name in (ROLE_NAMES if actor.is_superuser else LOCAL_ROLE_NAMES)]
        if actor.is_superuser:
            selected = active_delegation(actor)
            self.fields['delegacion'] = forms.ModelChoiceField(label='Delegación',
                queryset=Delegacion.objects.filter(estado='Activo'), initial=selected,
                disabled=selected is not None, required=False)
            self.fields['rut'].required = False
        if not self.creating:
            self.initial['rut'] = self.instance.perfil.rut
            self.initial['role'] = ('Superadministrador' if self.instance.is_superuser else
                self.instance.groups.filter(name__in=ROLE_NAMES).values_list('name', flat=True).first())
            if actor.is_superuser:
                self.initial['delegacion'] = self.instance.perfil.delegacion_id

    def clean_rut(self):
        if not self.cleaned_data['rut'] and self.actor.is_superuser:
            return None
        try:
            rut = normalize_rut(self.cleaned_data['rut'])
        except RutError as exc:
            raise ValidationError(str(exc)) from exc
        if Perfil.objects.filter(rut=rut).exclude(user_id=self.instance.pk).exists():
            raise ValidationError('Ya existe una cuenta con este RUT.')
        return rut

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe una cuenta con este correo electrónico.')
        return email

    def clean(self):
        data = super().clean()
        if self.actor.is_superuser and not data.get('rut') and data.get('role') != 'Superadministrador':
            self.add_error('rut', 'Ingresa el RUT de la cuenta municipal.')
        if self.actor.is_superuser and not data.get('delegacion') and data.get('role') != 'Superadministrador':
            self.add_error('delegacion', 'Selecciona una delegación para la cuenta municipal.')
        if self.instance.pk == self.actor.pk and self.actor.is_superuser:
            if not data.get('is_active') or data.get('role') != 'Superadministrador':
                raise ValidationError('Conserva tu acceso de superadministrador activo al editar tu propia cuenta.')
        password = data.get('new_password')
        if password:
            candidate = User(username=data.get('username', ''), email=data.get('email', ''),
                             first_name=data.get('first_name', ''), last_name=data.get('last_name', ''))
            try:
                password_validation.validate_password(password, candidate)
            except ValidationError as exc:
                self.add_error('new_password', exc)
        return data

    def save(self, commit=True):
        if not commit:
            raise ValueError('Las cuentas y su ámbito deben guardarse juntos.')
        user = super().save(commit=False)
        if self.actor.is_superuser:
            user.is_superuser = user.is_staff = self.cleaned_data['role'] == 'Superadministrador'
        if self.cleaned_data.get('new_password'):
            user.set_password(self.cleaned_data['new_password'])
        user.save()
        delegation = self.cleaned_data['delegacion'] if self.actor.is_superuser else self.actor.perfil.delegacion
        Perfil.objects.update_or_create(user=user, defaults={'delegacion': delegation, 'rut': self.cleaned_data['rut']})
        user.groups.set([Group.objects.get_or_create(name=self.cleaned_data['role'])[0]])
        return user


class GroupPermissionsForm(forms.Form):
    group = forms.ModelChoiceField(label='Grupo', queryset=Group.objects.order_by('name'))
    permissions = forms.ModelMultipleChoiceField(label='Permisos', required=False,
        queryset=Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename'),
        widget=forms.CheckboxSelectMultiple)
