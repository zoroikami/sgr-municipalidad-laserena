from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils import timezone

from .integrado import CARGOS
from .models import RegistroDelegacion


class Organizacion(RegistroDelegacion):
    prefijo = 'ORG-'
    nombre = models.CharField('Nombre', max_length=300)
    familia = models.CharField(max_length=30, choices=[('territorial', 'Territorial'), ('funcional', 'Funcional')], default='funcional')
    subfamilia = models.CharField(max_length=100, blank=True)
    domicilio = models.CharField(max_length=300, blank=True)
    socios_activos = models.PositiveIntegerField(null=True, blank=True)
    fecha_constitucion = models.DateField(null=True, blank=True)
    registro_pj = models.CharField('Registro de personalidad jurídica', max_length=50, blank=True)
    fecha_inscripcion = models.DateField(null=True, blank=True)
    registro_directiva = models.CharField(max_length=50, blank=True)
    verificada = models.BooleanField(default=False)


class GestionTubo(RegistroDelegacion):
    prefijo = 'TUB-'
    ancho_codigo = 5
    ESTADOS = [('Ingresado', 'Ingresado'), ('Pendiente', 'Pendiente'), ('En proceso', 'En proceso'), ('Realizado', 'Realizado')]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Ingresado')
    fecha_solicitud = models.DateField(default=timezone.localdate)
    solicitante = models.CharField(max_length=140)
    territorio = models.CharField(max_length=140, blank=True)
    origen = models.CharField(max_length=3, choices=[('INT', 'Interno'), ('EXT', 'Externo')], default='EXT')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='gestiones_tubo')
    fecha_compromiso = models.DateField(null=True, blank=True)
    apoyo = models.CharField('Área o persona de apoyo', max_length=160, blank=True)
    observaciones = models.TextField(max_length=2000, blank=True)
    atencion = models.ForeignKey('gestion.Atencion', null=True, blank=True, on_delete=models.PROTECT)
    organizacion = models.ForeignKey(Organizacion, null=True, blank=True, on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        errores = {}
        for campo in ('atencion', 'organizacion'):
            obj = getattr(self, campo) if getattr(self, campo + '_id') else None
            if obj and (obj.delegacion_id != self.delegacion_id or obj.deleted_at):
                errores[campo] = 'Selecciona un registro vigente de la misma delegación.'
        if self.responsable_id and not self.responsable.is_superuser:
            perfil = getattr(self.responsable, 'perfil', None)
            if not self.responsable.is_active or not perfil or perfil.delegacion_id != self.delegacion_id:
                errores['responsable'] = 'Selecciona un responsable activo de la misma delegación.'
        if errores:
            raise ValidationError(errores)


class ActividadSGR(models.Model):
    delegacion = models.ForeignKey('gestion.Delegacion', on_delete=models.PROTECT)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    item = models.ForeignKey('gestion.ItemMeta', on_delete=models.PROTECT)
    cargo = models.CharField(max_length=30, choices=CARGOS)
    fecha = models.DateField(default=timezone.localdate)
    descripcion = models.TextField(max_length=500)
    solicitante_nombre = models.CharField(max_length=140, blank=True)
    solicitante_telefono = models.CharField(max_length=25, blank=True,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,25}$', 'Ingresa un teléfono válido.')])
    solicitante_delegado = models.BooleanField('El solicitante es el delegado', default=False)
    es_accion = models.BooleanField('La acción fue realizada (no es una coordinación)', default=True)
    felicitacion = models.BooleanField('Es una felicitación', default=False)
    respaldo_formal = models.CharField('Referencia del respaldo formal al delegado', max_length=300, blank=True)
    informado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
        editable=False, on_delete=models.PROTECT, related_name='felicitaciones_informadas')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-fecha', '-pk']
        permissions = [('validar_delegado', 'Puede informar felicitaciones y registrar ausencias como delegado')]

    @property
    def motivo_puntaje(self):
        if self.solicitante_delegado:
            return 'Otra gestión: el solicitante es el delegado.'
        if not self.solicitante_nombre.strip() or not self.solicitante_telefono.strip():
            return 'Sin puntaje: falta nombre o teléfono del usuario.'
        if not self.es_accion:
            return 'Sin puntaje: coordinación previa a una acción.'
        if self.felicitacion and (not self.respaldo_formal.strip() or not self.informado_por_id):
            return 'Sin puntaje: falta respaldo formal o informe del delegado.'
        return 'Puntuable'

    @property
    def puntuable(self):
        return self.motivo_puntaje == 'Puntuable'

    def clean(self):
        super().clean()
        if self.item_id and (self.item.delegacion_id != self.delegacion_id or self.item.deleted_at or self.item.estado != 'Activo'):
            raise ValidationError({'item': 'Selecciona un ítem activo de la misma delegación.'})
        if self.item_id and self.item.cargo_sgr and self.item.cargo_sgr != self.cargo:
            raise ValidationError({'item': 'El ítem no corresponde al cargo de la actividad.'})
        if self.responsable_id:
            perfil = getattr(self.responsable, 'perfil', None)
            if not self.responsable.is_superuser and (not perfil or perfil.delegacion_id != self.delegacion_id):
                raise ValidationError({'responsable': 'El responsable debe pertenecer a la misma delegación.'})
            if perfil and perfil.cargo_sgr and perfil.cargo_sgr != self.cargo:
                raise ValidationError({'cargo': 'Selecciona el cargo municipal asignado al funcionario.'})

    def save(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        from .integrado import validar_fecha
        with transaction.atomic():
            # Serialize quota checks across workers, including different delegations.
            get_user_model().objects.select_for_update().get(pk=self.responsable_id)
            if self._state.adding:
                validar_fecha(self.fecha)
                registros = type(self).objects.filter(responsable_id=self.responsable_id)
                if registros.filter(fecha=self.fecha).count() >= 7 or registros.filter(created_at__date=timezone.localdate()).count() >= 7:
                    raise ValidationError('El ingreso diario no puede superar siete actividades por funcionario.')
                self.created_at = timezone.now()
            if self.informado_por_id:
                perfil = getattr(self.informado_por, 'perfil', None)
                if not self.informado_por.has_perm('gestion.validar_delegado') or (
                    not self.informado_por.is_superuser and (not perfil or perfil.delegacion_id != self.delegacion_id)):
                    raise ValidationError('La felicitación debe ser informada por el delegado de la misma delegación.')
            self.full_clean()
            return super().save(*args, **kwargs)


class AusenciaSGR(models.Model):
    delegacion = models.ForeignKey('gestion.Delegacion', on_delete=models.PROTECT)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    desde = models.DateField()
    hasta = models.DateField()
    motivo = models.CharField(max_length=20, choices=[('libre', 'Día libre'), ('vacaciones', 'Vacaciones'),
        ('administrativo', 'Día administrativo'), ('licencia', 'Licencia')])
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ausencias_registradas', editable=False)

    class Meta:
        ordering = ['-desde', '-pk']

    def clean(self):
        super().clean()
        if self.desde and self.hasta and self.hasta < self.desde:
            raise ValidationError({'hasta': 'La fecha final debe ser igual o posterior a la inicial.'})
        if self.responsable_id:
            perfil = getattr(self.responsable, 'perfil', None)
            if not perfil or perfil.delegacion_id != self.delegacion_id:
                raise ValidationError({'responsable': 'Selecciona un funcionario de la misma delegación.'})
