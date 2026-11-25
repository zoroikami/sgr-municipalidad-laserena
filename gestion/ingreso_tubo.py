"""Columna «INGRESO A TUBO» de las hojas de la matriz: la actividad o el caso pasa al tubo sin volver a escribirla.

En la matriz revisada las filas marcadas SÍ se copiaban a mano en la hoja TUBO (por ejemplo, la solicitud de
maquinaria pesada de COOR DISERCO es la gestión 8 del TUBO). Aquí se crea la gestión en estado Ingresado.
"""
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import GestionTubo


def nombre_disponible(delegacion, base, sufijo):
    """El nombre de la gestión es único por delegación: si ya existe, se distingue con el código de origen."""
    base = ' '.join((base or '').split())[:120] or 'Gestión ingresada desde la matriz'
    if not GestionTubo.all_objects.filter(delegacion=delegacion, nombre=base).exists():
        return base
    return f'{base[:120]} ({sufijo})'[:140]


def ingresar_al_tubo(*, delegacion, responsable, descripcion, solicitante, telefono, fecha, sufijo,
                     rut='', solicitante_delegado=False, observaciones=''):
    """Crea la gestión del tubo. Exige nombre y teléfono del usuario, como el formulario del tubo (punto 2)."""
    if not (solicitante or '').strip() or not (telefono or '').strip():
        raise ValidationError('Para ingresar al tubo escribe el nombre y el teléfono del usuario.')
    with transaction.atomic():
        gestion = GestionTubo(delegacion=delegacion, responsable=responsable, fecha_solicitud=fecha,
                              nombre=nombre_disponible(delegacion, descripcion, sufijo), solicitante=solicitante.strip(),
                              solicitante_telefono=telefono.strip(), solicitante_rut=rut or '', origen='EXT',
                              observaciones=observaciones)
        gestion.full_clean(exclude=['codigo'])
        gestion.save()
        # Punto 1: si la actividad declara que el solicitante es el delegado, la gestión es «otra gestión»
        # aunque el RUT no lo identifique (save() identifica solo por RUT).
        if solicitante_delegado and gestion.solicitante_cargo != 'delegado':
            GestionTubo.objects.filter(pk=gestion.pk).update(solicitante_cargo='delegado')
            gestion.solicitante_cargo = 'delegado'
    return gestion
