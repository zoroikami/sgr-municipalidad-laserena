from django.conf import settings
from django.db import models
from django.utils import timezone


class HistorialEstado(models.Model):
    """Cada transición pertenece a un único registro; no tiene edición pública."""
    gestion_tubo = models.ForeignKey('gestion.GestionTubo', null=True, blank=True,
        on_delete=models.PROTECT, related_name='historial_estados')
    carta = models.ForeignKey('gestion.Carta', null=True, blank=True,
        on_delete=models.PROTECT, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(default=timezone.now, editable=False)
    fecha_objetivo = models.DateField(null=True, blank=True, editable=False)
    observacion = models.TextField(max_length=2000, blank=True)

    class Meta:
        ordering = ['fecha', 'pk']
        default_permissions = ()
        constraints = [models.CheckConstraint(
            condition=(models.Q(gestion_tubo__isnull=False, carta__isnull=True)
                       | models.Q(gestion_tubo__isnull=True, carta__isnull=False)),
            name='historial_estado_un_registro')]
