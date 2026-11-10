"""Municipal records. Every business relationship belongs to a delegation."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import connection, models, transaction
from django.db.models.functions import Cast, Substr
from django.utils import timezone


ESTADOS = [('Activo', 'Activo'), ('Inactivo', 'Inactivo')]
ESTADOS_ATENCION = [('Ingresada', 'Ingresada'), ('En proceso', 'En proceso'), ('Resuelta', 'Resuelta')]


class Secuencia(models.Model):
    prefijo = models.CharField(max_length=30, unique=True)
    valor = models.PositiveBigIntegerField(default=0)

    @classmethod
    def siguiente(cls, prefijo, *, model, field='codigo', width=3):
        # Unique prefix and a row lock serialize allocations across ASGI workers.
        with transaction.atomic():
            # Upsert takes an exclusive lock even on the first concurrent use.
            # get_or_create can leave duplicate-insert shared locks that deadlock
            # when several workers subsequently upgrade to SELECT FOR UPDATE.
            table = connection.ops.quote_name(cls._meta.db_table)
            with connection.cursor() as cursor:
                if connection.vendor == 'sqlite':
                    # Local development uses SQLite; acquire its write lock first.
                    cursor.execute(
                        f'INSERT INTO {table} (prefijo, valor) VALUES (%s, 0) '
                        'ON CONFLICT(prefijo) DO UPDATE SET prefijo = excluded.prefijo', [prefijo])
                else:
                    cursor.execute(
                        f'INSERT INTO {table} (prefijo, valor) VALUES (%s, 0) '
                        'ON DUPLICATE KEY UPDATE prefijo = %s', [prefijo, prefijo])
            row = cls.objects.select_for_update().get(prefijo=prefijo)
            # Include archived and explicitly imported codes, even with a stale counter.
            highest = model.all_objects.filter(**{f'{field}__regex': f'^{prefijo}[0-9]+$'}).aggregate(
                number=models.Max(Cast(Substr(field, len(prefijo) + 1), models.PositiveBigIntegerField()))
            )['number'] or 0
            row.valor = max(row.valor, highest) + 1
            row.save(update_fields=['valor'])
            return f'{prefijo}{row.valor:0{width}d}'


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Registro(models.Model):
    codigo = models.CharField('Código', max_length=30, unique=True, blank=True, editable=False)
    codigo_anterior = models.CharField(max_length=30, unique=True, null=True, blank=True, editable=False)
    nombre = models.CharField('Nombre', max_length=140)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='Activo')
    created_at = models.DateTimeField('Fecha de creación', default=timezone.now, editable=False)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    objects = ActiveManager()
    all_objects = models.Manager()
    prefijo = ''
    ancho_codigo = 3

    class Meta:
        abstract = True
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = Secuencia.siguiente(self.prefijo, model=type(self), width=self.ancho_codigo)
        return super().save(*args, **kwargs)


class Delegacion(Registro):
    prefijo = 'DEL'
    ancho_codigo = 2
    direccion = models.CharField('Dirección', max_length=200)
    comuna = models.CharField('Comuna', max_length=100, default='La Serena')

    class Meta(Registro.Meta):
        verbose_name = 'delegación'
        verbose_name_plural = 'delegaciones'


class RegistroDelegacion(Registro):
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT)
    descripcion = models.TextField('Descripción', blank=True, max_length=500)

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
    folio_anterior = models.CharField(max_length=35, unique=True, null=True, blank=True, editable=False)
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT)
    tipo = models.ForeignKey(TipoAtencion, verbose_name='Tipo de atención', on_delete=models.PROTECT)
    subatencion = models.ForeignKey(SubAtencion, verbose_name='Subatención', on_delete=models.PROTECT)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Cliente vinculado',
                                null=True, blank=True, on_delete=models.PROTECT, related_name='atenciones_propias')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='atenciones_registradas')
    solicitante_rut = models.CharField('RUT del solicitante', max_length=12)
    solicitante_nombre = models.CharField('Nombre del solicitante', max_length=140)
    descripcion = models.TextField('Descripción', max_length=500)
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
        from .delegation import has_global_scope
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
            if field == 'responsable' and user and has_global_scope(user):
                continue
            if self.delegacion_id and user and (not hasattr(user, 'perfil') or user.perfil.delegacion_id != self.delegacion_id):
                errors[field] = 'La cuenta debe pertenecer a tu delegación.'
        if self.cliente_id and (not self.cliente.is_active or not self.cliente.groups.filter(name='Cliente').exists()):
            errors['cliente'] = 'Selecciona una cuenta activa con rol Cliente.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.folio:
            year = timezone.localtime(self.created_at).year if timezone.is_aware(self.created_at) else self.created_at.year
            self.folio = Secuencia.siguiente(f'ATN-{year}-', model=type(self), field='folio', width=4)
        return super().save(*args, **kwargs)
