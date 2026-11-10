import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from cuentas.rut import RutError, normalize_rut
from .storage import private_photo_storage


def photo_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f'perfiles/{uuid.uuid4().hex}{extension}'


class Perfil(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    delegacion = models.ForeignKey('gestion.Delegacion', on_delete=models.PROTECT, blank=True, null=True)
    rut = models.CharField('RUT', max_length=12, unique=True, blank=True, null=True)
    foto = models.ImageField('Foto', upload_to=photo_upload_path, storage=private_photo_storage, blank=True)

    class Meta:
        permissions = [
            ('view_cuentas', 'Puede consultar cuentas de su delegación'),
            ('add_cuentas', 'Puede crear cuentas en su delegación'),
            ('change_cuentas', 'Puede editar cuentas de su delegación'),
        ]

    def clean(self):
        super().clean()
        global_access = self.user_id is not None and self.user.is_superuser
        if not global_access and not self.delegacion_id:
            raise ValidationError({'delegacion': 'Selecciona una delegación.'})
        if not self.rut and global_access:
            return
        try:
            self.rut = normalize_rut(self.rut)
        except RutError as exc:
            raise ValidationError({'rut': str(exc)}) from exc

    def save(self, *args, **kwargs):
        self.rut = None if self.user.is_superuser and not self.rut else normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
