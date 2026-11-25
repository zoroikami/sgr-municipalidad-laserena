import logging
from functools import partial

from django.db import transaction

logger = logging.getLogger(__name__)
GLOBAL_SCOPE = 'global'
TEMAS = {
    'atenciones': 'view_atencion', 'tubo': 'view_gestiontubo', 'cartas': 'view_carta',
    'casos': 'view_casosocial', 'sgr': 'view_actividadsgr',
}


def temas_afectados(modulo):
    if modulo not in TEMAS:
        raise ValueError('Módulo de tiempo real desconocido.')
    # El resultado del funcionario incluye la tasa de soluciones del tubo.
    return ('tubo', 'sgr') if modulo == 'tubo' else (modulo,)


def group_for(delegacion_id, modulo='atenciones'):
    if modulo not in TEMAS:
        raise ValueError('Módulo de tiempo real desconocido.')
    return f'{modulo}.delegacion.{delegacion_id}'


def emit_change(delegacion_id, modulo='atenciones'):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer:
            for tema in temas_afectados(modulo):
                for scope in (delegacion_id, GLOBAL_SCOPE):
                    async_to_sync(layer.group_send)(group_for(scope, tema), {'type': 'tabla.cambio'})
    except ImportError:
        return
    except Exception:
        logger.exception('No se pudo notificar el cambio del módulo %s.', modulo)


def notify_after_commit(delegacion_id, modulo='atenciones'):
    # Never broadcast a record payload. The protected HTTP view reapplies scope.
    temas_afectados(modulo)
    transaction.on_commit(partial(emit_change, delegacion_id, modulo), robust=True)
