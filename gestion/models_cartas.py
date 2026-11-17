"""Correspondencia ingresada a oficina de partes, limitada por delegación."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .models import RegistroDelegacion


class Carta(RegistroDelegacion):
    prefijo = 'CAR-'
    ancho_codigo = 5
    ESTADOS = [('En proceso', 'En proceso'), ('Aprobada', 'Aprobada'),
               ('Finalizada', 'Finalizada'), ('No aplica', 'No aplica')]
    nombre = models.CharField('Actividad o tema', max_length=140)
    fecha = models.DateField('Fecha de ingreso', default=timezone.localdate)
    numero_ingreso = models.CharField('Nº de ingreso de oficina de partes', max_length=50)
    para = models.CharField('Para', max_length=20, choices=[
        ('Alcaldesa', 'Alcaldesa'), ('Delegado', 'Delegado'), ('Otro', 'Otro')], default='Delegado')
    remite = models.CharField('Remite', max_length=140)
    telefono = models.CharField('Fono de contacto', max_length=25, blank=True,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,25}$', 'Ingresa un teléfono válido.')])
    fecha_actividad = models.DateField('Fecha de la actividad', null=True, blank=True)
    encargado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='cartas_seguimiento', verbose_name='Encargado de seguimiento')
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='En proceso')
    pronunciamiento = models.TextField('Pronunciamiento', max_length=500, blank=True)
    derivada_a = models.CharField('Derivada a', max_length=160, blank=True)
    observacion = models.TextField('Observación', max_length=2000, blank=True)

    class Meta(RegistroDelegacion.Meta):
        constraints = []
        verbose_name = 'carta'
        verbose_name_plural = 'cartas'

    def clean(self):
        super().clean()
        if self.encargado_id:
            profile = getattr(self.encargado, 'perfil', None)
            if (not self.encargado.is_active or not profile
                    or profile.delegacion_id != self.delegacion_id
                    or self.encargado.groups.filter(name='Cliente').exists()):
                raise ValidationError({'encargado': 'Selecciona un funcionario activo de la misma delegación.'})
