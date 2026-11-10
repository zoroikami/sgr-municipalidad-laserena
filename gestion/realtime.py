import logging
from functools import partial

from django.db import transaction

logger = logging.getLogger(__name__)
GLOBAL_SCOPE = 'global'


def group_for(delegacion_id):
    return f'atenciones.delegacion.{delegacion_id}'


def emit_change(delegacion_id):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer:
            for scope in (delegacion_id, GLOBAL_SCOPE):
                async_to_sync(layer.group_send)(group_for(scope), {'type': 'tabla.cambio'})
    except ImportError:
        return
    except Exception:
        logger.exception('No se pudo notificar el cambio de atenciones.')


def notify_after_commit(delegacion_id):
    # Never broadcast a record payload. The protected HTTP view reapplies scope.
    transaction.on_commit(partial(emit_change, delegacion_id), robust=True)
