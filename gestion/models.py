"""Municipal records. Every business relationship belongs to a delegation."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


ESTADOS = [('Activo', 'Activo'), ('Inactivo', 'Inactivo')]
ESTADOS_ATENCION = [('Ingresada', 'Ingresada'), ('En proceso', 'En proceso'), ('Resuelta', 'Resuelta')]


class Secuencia(models.Model):
    prefijo = models.CharField(max_length=30, unique=True)
    valor = models.PositiveBigIntegerField(default=0)

    @classmethod
    def siguiente(cls, prefijo):
        # Unique prefix and a row lock serialize allocations across ASGI workers.
        with transaction.atomic():
            cls.objects.get_or_create(prefijo=prefijo)
            row = cls.objects.select_for_update().get(prefijo=prefijo)
            row.valor += 1
            row.save(update_fields=['valor'])
            return f'{prefijo}{row.valor:06d}'


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Registro(models.Model):
    codigo = models.CharField('Código', max_length=30, unique=True, blank=True, editable=False)
    nombre = models.CharField('Nombre', max_length=140)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='Activo')
    created_at = models.DateTimeField('Fecha de creación', default=timezone.now, editable=False)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    objects = ActiveManager()
    all_objects = models.Manager()
    prefijo = ''

    class Meta:
        abstract = True
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = Secuencia.siguiente(self.prefijo)
        return super().save(*args, **kwargs)


class Delegacion(Registro):
    prefijo = 'DEL'
    direccion = models.CharField('Dirección', max_length=200)
    comuna = models.CharField('Comuna', max_length=100, default='La Serena')

    class Meta(Registro.Meta):
        verbose_name = 'delegación'
        verbose_name_plural = 'delegaciones'


class RegistroDelegacion(Registro):
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT)
    descripcion = models.TextField('Descripción', blank=True, max_length=3000)

    class Meta(Registro.Meta):
        abstract = True
        constraints = [models.UniqueConstraint(fields=['delegacion', 'nombre'], name='%(class)s_nombre_ambito')]


class TipoAtencion(RegistroDelegacion):
    prefijo = 'TA'

    class Meta(RegistroDelegacion.Meta):
        verbose_name = 'tipo de atención'
        verbose_name_plural = 'tipos de atención'


class SubAtencion(RegistroDelegacion):
    prefijo = 'SA'
    tipo = models.ForeignKey(TipoAtencion, verbose_name='Tipo de atención', on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        if self.tipo_id and self.delegacion_id and self.tipo.delegacion_id != self.delegacion_id:
            raise ValidationError({'tipo': 'El tipo debe pertenecer a tu delegación.'})
        if self.tipo_id and (self.tipo.deleted_at or self.tipo.estado != 'Activo'):
            raise ValidationError({'tipo': 'Selecciona un tipo de atención activo.'})

    class Meta(RegistroDelegacion.Meta):
        verbose_name = 'subatención'
        verbose_name_plural = 'subatenciones'


class ItemMeta(RegistroDelegacion):
    prefijo = 'IT'
    unidad_medida = models.CharField('Unidad de medida', max_length=60)
    meta_cantidad = models.PositiveIntegerField('Cantidad de meta', default=100, validators=[MinValueValidator(0)])

    class Meta(RegistroDelegacion.Meta):
        verbose_name = 'ítem y meta'
        verbose_name_plural = 'ítems y metas'
        constraints = RegistroDelegacion.Meta.constraints + [
            models.CheckConstraint(condition=models.Q(meta_cantidad__gte=0), name='meta_cantidad_no_negativa')
        ]


class Atencion(models.Model):
    folio = models.CharField('Folio', max_length=35, unique=True, blank=True, editable=False)
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT)
    tipo = models.ForeignKey(TipoAtencion, verbose_name='Tipo de atención', on_delete=models.PROTECT)
    subatencion = models.ForeignKey(SubAtencion, verbose_name='Subatención', on_delete=models.PROTECT)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Cliente vinculado',
                                null=True, blank=True, on_delete=models.PROTECT, related_name='atenciones_propias')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='atenciones_registradas')
    solicitante_rut = models.CharField('RUT del solicitante', max_length=12)
    solicitante_nombre = models.CharField('Nombre del solicitante', max_length=140)
    descripcion = models.TextField('Descripción', max_length=3000)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS_ATENCION, default='Ingresada')
    created_at = models.DateTimeField('Fecha de creación', default=timezone.now, editable=False)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'atención'
        verbose_name_plural = 'atenciones'
        indexes = [models.Index(fields=['delegacion', 'deleted_at', 'created_at'])]

    def __str__(self):
        return f'{self.folio} · {self.solicitante_nombre}'

    def clean(self):
        from cuentas.rut import normalize_rut, RutError
        errors = {}
        try:
            self.solicitante_rut = normalize_rut(self.solicitante_rut)
        except RutError as error:
            errors['solicitante_rut'] = str(error)
        for field in ['tipo', 'subatencion']:
            value = getattr(self, field, None) if getattr(self, f'{field}_id', None) else None
            if value and (value.delegacion_id != self.delegacion_id or value.deleted_at or value.estado != 'Activo'):
                errors[field] = 'Selecciona una opción activa de tu delegación.'
        if self.subatencion_id and self.tipo_id and self.subatencion.tipo_id != self.tipo_id:
            errors['subatencion'] = 'La subatención no corresponde al tipo seleccionado.'
        for field in ['cliente', 'responsable']:
            user = getattr(self, field, None) if getattr(self, f'{field}_id', None) else None
            if user and (not hasattr(user, 'perfil') or user.perfil.delegacion_id != self.delegacion_id):
                errors[field] = 'La cuenta debe pertenecer a tu delegación.'
        if self.cliente_id and (not self.cliente.is_active or not self.cliente.groups.filter(name='Cliente').exists()):
            errors['cliente'] = 'Selecciona una cuenta activa con rol Cliente.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = Secuencia.siguiente(f'ATN-{timezone.localdate().year}-')
        return super().save(*args, **kwargs)
