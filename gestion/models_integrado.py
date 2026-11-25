from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
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
    solicitante_rut = models.CharField('RUT del solicitante', max_length=12, blank=True)
    solicitante_telefono = models.CharField('Teléfono del solicitante', max_length=25, blank=True,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,25}$', 'Ingresa un teléfono válido.')])
    # Identificación por RUT al guardar: conserva el cargo vigente al momento del ingreso.
    solicitante_funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name='gestiones_tubo_solicitadas')
    solicitante_cargo = models.CharField(max_length=30, blank=True, editable=False)
    territorio = models.CharField(max_length=140, blank=True)
    origen = models.CharField(max_length=3, choices=[('INT', 'Interno'), ('EXT', 'Externo')], default='EXT')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='gestiones_tubo')
    fecha_compromiso = models.DateField(null=True, blank=True)
    apoyo = models.CharField('Área o persona de apoyo', max_length=160, blank=True)
    observaciones = models.TextField(max_length=2000, blank=True)
    atencion = models.ForeignKey('gestion.Atencion', null=True, blank=True, on_delete=models.PROTECT)
    organizacion = models.ForeignKey(Organizacion, null=True, blank=True, on_delete=models.PROTECT)

    @property
    def solicitante_es_funcionario(self):
        return bool(self.solicitante_funcionario_id or self.solicitante_cargo)

    @property
    def solicitante_cargo_nombre(self):
        from .funcionarios import nombre_cargo
        return nombre_cargo(self.solicitante_cargo) if self.solicitante_es_funcionario else ''

    @property
    def solicitante_funcionario_texto(self):
        if not self.solicitante_es_funcionario:
            return 'No'
        regla = ' · otra gestión, no suma puntaje' if self.es_otra_gestion else ''
        return f'Sí · {self.solicitante_cargo_nombre}{regla}'

    @property
    def es_otra_gestion(self):
        """Nuevo requerimiento, punto 1: si el solicitante es el delegado no se contabiliza."""
        return self.solicitante_cargo == 'delegado'

    @property
    def titulo_tarjeta(self):
        """Quita un código entre corchetes al inicio cuando ya se muestra en la tarjeta."""
        codigos = {self.codigo}
        if self.atencion_id:
            codigos.add(self.atencion.folio)
        nombre = self.nombre.strip()
        if nombre.startswith('[') and ']' in nombre:
            codigo, resto = nombre[1:].split(']', 1)
            if codigo.strip() in codigos and resto.strip(' -·:'):
                return resto.strip(' -·:')
        return nombre

    def identificar_solicitante(self):
        from .funcionarios import buscar_funcionario, cargo_de
        funcionario = buscar_funcionario(self.solicitante_rut) if self.solicitante_rut else None
        self.solicitante_funcionario = funcionario
        self.solicitante_cargo = cargo_de(funcionario) if funcionario else ''

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'solicitante_rut' in update_fields:
            anterior = (type(self).all_objects.filter(pk=self.pk).values_list('solicitante_rut', flat=True).first()
                        if self.pk else None)
            if self._state.adding or anterior != self.solicitante_rut:
                self.identificar_solicitante()
                if update_fields is not None:
                    kwargs['update_fields'] = {*update_fields, 'solicitante_funcionario', 'solicitante_cargo'}
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errores = {}
        if self.solicitante_rut:
            from cuentas.rut import RutError, normalize_rut
            try:
                self.solicitante_rut = normalize_rut(self.solicitante_rut)
            except RutError as error:
                errores['solicitante_rut'] = str(error)
        if self.fecha_solicitud and self.fecha_solicitud > timezone.localdate():
            errores['fecha_solicitud'] = 'La fecha de solicitud no puede ser futura.'
        if self.fecha_solicitud and self.fecha_compromiso and self.fecha_compromiso < self.fecha_solicitud:
            errores['fecha_compromiso'] = 'La fecha de compromiso no puede ser anterior a la fecha de solicitud.'
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


# Hoja COOR DISERCO, lista de la columna de tipo de gestión.
TIPOS_GESTION_DISERCO = [
    ('alumbrado', 'Alumbrado público'), ('plazas', 'Áreas verdes: plazas'), ('podas', 'Áreas verdes: podas'),
    ('informe_cuadrilla', 'Informe de cuadrilla'), ('informe_tecnico', 'Informe técnico'),
    ('punto_reciclaje', 'Punto de reciclaje'), ('retiro_basuras', 'Retiro de basuras y limpieza'),
    ('salida_terreno', 'Salida a terreno'), ('aguas', 'Aguas y sanitaria'), ('maquinarias', 'Maquinarias'),
    ('obras_civiles', 'Obras civiles'), ('taller_compostaje', 'Taller de compostaje'),
    ('taller_medio_ambiente', 'Taller de medio ambiente'), ('taller_reciclaje', 'Taller de reciclaje'),
    ('tolva', 'Tolva'), ('emergencia', 'Emergencia'), ('sumideros', 'Limpieza de sumideros y drenes'),
    ('otras', 'Otras'),
]


# Hojas G SOC: cada fila es un caso social con hasta tres gestiones; las fechas de visita, informe y beneficio
# salen de las actividades vinculadas. Plazos de la fila 19 de la hoja (informativos: no ponderan).
PLAZOS_CASO_SOCIAL = {'ingreso_programada': 10, 'programada_visita': 0, 'visita_informe': 4,
                      'informe_beneficio': 4, 'ingreso_beneficio': 20}


class CasoSocial(RegistroDelegacion):
    """Caso del gestor social (hojas G SOC). `nombre` es el nombre del usuario atendido."""
    prefijo = 'CS-'
    ancho_codigo = 5
    ESTADOS = [('Abierto', 'Abierto'), ('Cerrado', 'Cerrado')]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Abierto')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Gestor social', on_delete=models.PROTECT,
        related_name='casos_sociales')
    fecha_ingreso = models.DateField('Fecha de ingreso', default=timezone.localdate)
    tipo = models.ForeignKey('gestion.TipoAtencion', verbose_name='Tipo de atención', null=True, blank=True,
        on_delete=models.PROTECT)
    subatencion = models.ForeignKey('gestion.SubAtencion', verbose_name='Subatención', null=True, blank=True,
        on_delete=models.PROTECT)
    usuario_rut = models.CharField('RUT del usuario', max_length=12, blank=True)
    usuario_telefono = models.CharField('Teléfono del usuario', max_length=25,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,25}$', 'Ingresa un teléfono válido.')])
    requiere_visita = models.BooleanField('Requiere visita', default=False)
    fecha_programada_visita = models.DateField('Fecha programada de visita', null=True, blank=True)
    devoluciones = models.PositiveSmallIntegerField('Devoluciones del informe', default=0,
        help_text='Veces que el informe fue devuelto para corregirlo (reingreso 1.ª, 2.ª o 3.ª vez).')
    gestion_tubo = models.ForeignKey('gestion.GestionTubo', null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name='casos_sociales')

    class Meta(RegistroDelegacion.Meta):
        verbose_name = 'caso social'
        verbose_name_plural = 'casos sociales'
        # Un mismo usuario puede tener varios casos: el nombre no es único por delegación.
        constraints = [models.CheckConstraint(condition=models.Q(devoluciones__lte=3), name='caso_social_devoluciones_max_3')]

    def fecha_gestion(self, item):
        """Primera fecha válida de la gestión vinculada de ese ítem del gestor social (VISITA TERRENO, etc.)."""
        from .integrado import titulo_item
        titulo = titulo_item('social', item)
        fechas = [a.fecha for a in self.gestiones.all() if a.item.nombre == titulo and a.verificacion == 'valida']
        return min(fechas) if fechas else None

    @property
    def fecha_visita(self):
        return self.fecha_gestion('VISITA TERRENO')

    @property
    def fecha_informe(self):
        return self.fecha_gestion('ENTREGA INFORME')

    @property
    def fecha_beneficio(self):
        return self.fecha_gestion('ENTREGA BENEFICIO')

    def plazos(self):
        """Tiempos de respuesta de la hoja G SOC: días entre hitos y si cumplen el plazo (None si falta un hito)."""
        visita, informe, beneficio = self.fecha_visita, self.fecha_informe, self.fecha_beneficio
        tramos = [
            ('ingreso_programada', 'Ingreso a visita programada', self.fecha_ingreso, self.fecha_programada_visita),
            ('programada_visita', 'Visita programada a visita realizada', self.fecha_programada_visita, visita),
            ('visita_informe', 'Visita a entrega del informe', visita, informe),
            ('informe_beneficio', 'Informe a entrega del beneficio', informe, beneficio),
            ('ingreso_beneficio', 'Ingreso a entrega del beneficio', self.fecha_ingreso, beneficio),
        ]
        filas = []
        for clave, etiqueta, desde, hasta in tramos:
            if clave in ('ingreso_programada', 'programada_visita') and not self.requiere_visita:
                continue
            dias = (hasta - desde).days if desde and hasta else None
            limite = PLAZOS_CASO_SOCIAL[clave]
            filas.append({'clave': clave, 'etiqueta': etiqueta, 'dias': dias, 'limite': limite,
                          'cumple': None if dias is None else abs(dias) <= limite if limite == 0 else dias <= limite})
        return filas

    def clean(self):
        super().clean()
        errores = {}
        if self.fecha_ingreso and self.fecha_ingreso > timezone.localdate():
            errores['fecha_ingreso'] = 'La fecha de ingreso no puede ser futura.'
        if self.fecha_programada_visita and not self.requiere_visita:
            errores['fecha_programada_visita'] = 'Marca «Requiere visita» o deja la fecha vacía.'
        if self.fecha_programada_visita and self.fecha_ingreso and self.fecha_programada_visita < self.fecha_ingreso:
            errores['fecha_programada_visita'] = 'La visita no puede programarse antes del ingreso.'
        if self.subatencion_id and self.tipo_id and self.subatencion.tipo_id != self.tipo_id:
            errores['subatencion'] = 'La subatención no corresponde al tipo de atención.'
        if self.responsable_id and self.delegacion_id:
            perfil = getattr(self.responsable, 'perfil', None)
            if not perfil or perfil.delegacion_id != self.delegacion_id:
                errores['responsable'] = 'Selecciona un funcionario de la misma delegación.'
        if errores:
            raise ValidationError(errores)


class ActividadSGR(models.Model):
    delegacion = models.ForeignKey('gestion.Delegacion', on_delete=models.PROTECT)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    item = models.ForeignKey('gestion.ItemMeta', on_delete=models.PROTECT)
    cargo = models.CharField(max_length=30, choices=CARGOS)
    fecha = models.DateField(default=timezone.localdate)
    descripcion = models.TextField(max_length=500)
    # Columnas ACCIÓN (hojas T OC), DETALLE y DERIVADO A (hoja AP ADM): informativas, no cambian el puntaje.
    accion = models.CharField('Acción realizada', max_length=200, blank=True)
    derivado_a = models.CharField('Derivado a', max_length=140, blank=True)
    tipo_gestion = models.CharField('Tipo de gestión DISERCO', max_length=30, blank=True, choices=TIPOS_GESTION_DISERCO)
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
    # Hojas de la matriz: «INGRESO A TUBO» (SÍ/NO) crea la gestión en el tubo y la fila de un caso G SOC.
    gestion_tubo = models.ForeignKey(GestionTubo, null=True, blank=True, editable=False, on_delete=models.SET_NULL,
        related_name='actividades_origen')
    caso = models.ForeignKey(CasoSocial, verbose_name='Caso social', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='gestiones')
    # Columnas IMAGEN VERIF y «verificador válido» (1 válida, 0 no válida): la foto se archiva con el código.
    imagen_verificacion = models.BooleanField('Tiene foto de respaldo', default=False)
    VERIFICACION = [('valida', 'Válida'), ('no_valida', 'No válida')]
    verificacion = models.CharField('Verificación', max_length=12, choices=VERIFICACION, default='valida', editable=False)
    verificacion_motivo = models.CharField('Motivo de la verificación', max_length=200, blank=True, editable=False)
    verificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name='actividades_verificadas')
    verificado_en = models.DateTimeField(null=True, blank=True, editable=False)

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
        if self.tipo_gestion and self.cargo != 'servicios':
            raise ValidationError({'tipo_gestion': 'El tipo de gestión DISERCO corresponde al coordinador de servicios comunitarios.'})
        if self.responsable_id:
            perfil = getattr(self.responsable, 'perfil', None)
            if not self.responsable.is_superuser and (not perfil or perfil.delegacion_id != self.delegacion_id):
                # Some forms assign the responsible account without exposing a field.
                raise ValidationError('El responsable debe pertenecer a la misma delegación. Selecciona un funcionario de ella o cambia a tu delegación.')
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
    # Hoja SEMAFORO: licencias, vacaciones, emergencias y compensatorios o administrativos descuentan días.
    motivo = models.CharField(max_length=20, choices=[('libre', 'Día libre'), ('vacaciones', 'Vacaciones'),
        ('administrativo', 'Día administrativo'), ('licencia', 'Licencia'), ('emergencia', 'Emergencia'),
        ('compensatorio', 'Día compensatorio')])
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


class ReclamoSGR(models.Model):
    """Hoja RECLAMOS: reclamo escrito por mala atención de un funcionario; descuenta 20% de su resultado."""
    MEDIOS = [('whatsapp', 'WhatsApp'), ('correo', 'Correo electrónico'), ('libro', 'Libro de observaciones')]
    delegacion = models.ForeignKey('gestion.Delegacion', on_delete=models.PROTECT)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Funcionario involucrado', on_delete=models.PROTECT,
        related_name='reclamos_sgr')
    fecha = models.DateField(default=timezone.localdate)
    usuario_nombre = models.CharField('Usuario que reclama', max_length=140)
    contacto = models.CharField(max_length=25, blank=True,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,25}$', 'Ingresa un teléfono válido.')])
    ubicacion = models.CharField('Ubicación', max_length=160, blank=True)
    situacion = models.TextField('Situación que reclama', max_length=500)
    medio_escrito = models.CharField('Medio escrito', max_length=20, choices=MEDIOS)
    informado_a = models.CharField('Reclamo informado a', max_length=140, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reclamos_registrados',
        editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-fecha', '-pk']
        verbose_name = 'reclamo SGR'
        verbose_name_plural = 'reclamos SGR'

    def __str__(self):
        return f'Reclamo {self.fecha:%d/%m/%Y}: {self.usuario_nombre}'

    def clean(self):
        super().clean()
        if self.fecha and self.fecha > timezone.localdate():
            raise ValidationError({'fecha': 'No puedes registrar reclamos con fecha futura.'})
        if self.responsable_id:
            perfil = getattr(self.responsable, 'perfil', None)
            if not perfil or perfil.delegacion_id != self.delegacion_id:
                raise ValidationError({'responsable': 'Selecciona un funcionario de la misma delegación.'})


class MetaFuncionario(models.Model):
    """Ajuste individual de meta y ponderador (las hojas G SOC2, G SOC3, G SOC5 y T OC 3 difieren de su cargo)."""
    item = models.ForeignKey('gestion.ItemMeta', on_delete=models.CASCADE, related_name='ajustes')
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='metas_individuales')
    meta_cantidad = models.PositiveIntegerField('Meta individual')
    ponderador = models.DecimalField('Ponderador individual (%)', max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'meta individual'
        verbose_name_plural = 'metas individuales'
        constraints = [models.UniqueConstraint(fields=['item', 'funcionario'], name='meta_funcionario_unica')]

    def clean(self):
        super().clean()
        if self.item_id and self.funcionario_id:
            perfil = getattr(self.funcionario, 'perfil', None)
            if not perfil or perfil.delegacion_id != self.item.delegacion_id:
                raise ValidationError({'funcionario': 'El funcionario debe pertenecer a la delegación del ítem.'})
