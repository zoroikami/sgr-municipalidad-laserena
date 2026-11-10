import logging
from functools import partial

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def group_for(delegacion_id):
    return f'atenciones.delegacion.{delegacion_id}'


def emit_change(delegacion_id):
    async_to_sync(get_channel_layer().group_send)(
        group_for(delegacion_id), {'type': 'tabla.cambio'})


def notify_after_commit(delegacion_id):
    # Never broadcast a record payload. The protected HTTP view reapplies scope.
    transaction.on_commit(partial(emit_change, delegacion_id), robust=True)
