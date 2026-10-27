from django.contrib.auth.models import AbstractUser
from django.db import models

class Catalogo(models.Model):
    codigo = models.CharField(max_length=24, unique=True)
    nombre = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, default='Activo')

    class Meta:
        abstract = True
        ordering = ['id']

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

class Delegacion(Catalogo):
    direccion = models.CharField(max_length=255)
    comuna = models.CharField(max_length=100, default='La Serena')
    estado = models.CharField(max_length=20, default='Activa')
    creado_en = models.DateTimeField(auto_now_add=True)

class Rol(Catalogo):
    descripcion = models.TextField(blank=True)
    permisos = models.CharField(max_length=40, default='lectura')
    alcance = models.CharField(max_length=80, default='Delegación')

class Usuario(AbstractUser):
    nombre = models.CharField(max_length=200)
    rut = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    rol = models.ForeignKey(Rol, to_field='codigo', db_column='rol_codigo', on_delete=models.PROTECT, null=True, blank=True)
    delegacion = models.ForeignKey(Delegacion, to_field='codigo', db_column='delegacion_codigo', on_delete=models.PROTECT, null=True, blank=True)
    estado = models.CharField(max_length=20, default='Activo')

class ItemMeta(Catalogo):
    descripcion = models.TextField(blank=True)
    unidad_medida = models.CharField(max_length=80, default='Atenciones')
    meta_cantidad = models.PositiveIntegerField(default=100)

class TipoAtencion(Catalogo):
    descripcion = models.TextField(blank=True)

class SubAtencion(Catalogo):
    tipo = models.ForeignKey(TipoAtencion, to_field='codigo', db_column='tipo_codigo', on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, default='Activa')

class Atencion(models.Model):
    folio = models.CharField(max_length=32, unique=True)
    solicitante_rut = models.CharField(max_length=20, blank=True)
    solicitante_nombre = models.CharField(max_length=200)
    delegacion = models.ForeignKey(Delegacion, to_field='codigo', db_column='delegacion_codigo', on_delete=models.PROTECT)
    tipo = models.ForeignKey(TipoAtencion, to_field='codigo', db_column='tipo_codigo', on_delete=models.PROTECT)
    subtipo = models.ForeignKey(SubAtencion, to_field='codigo', db_column='subtipo_codigo', on_delete=models.PROTECT)
    descripcion = models.TextField()
    responsable_nombre = models.CharField(max_length=200)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

class Recuperacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    codigo_hash = models.CharField(max_length=256)
    expiracion = models.DateTimeField()
    intentos = models.PositiveSmallIntegerField(default=0)
    verificado = models.BooleanField(default=False)
    usado = models.BooleanField(default=False)

class Secuencia(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    valor = models.PositiveIntegerField(default=0)
