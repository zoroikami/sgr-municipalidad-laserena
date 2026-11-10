from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.contrib.sessions.backends.db import SessionStore
from django.utils.crypto import constant_time_compare

from .access import delegation_id, is_cliente
from .delegation import SESSION_KEY, has_global_scope, session_delegation
from .realtime import GLOBAL_SCOPE, group_for


@database_sync_to_async
def viewer_scope(user_id, session_key):
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if not user or is_cliente(user) or not user.has_perm('gestion.view_atencion'):
        return None
    session = SessionStore(session_key=session_key).load() if session_key else {}
    if (str(session.get('_auth_user_id')) != str(user.pk)
            or not constant_time_compare(session.get('_auth_user_hash', ''), user.get_session_auth_hash())):
        return None
    if has_global_scope(user):
        selected = session_delegation(session)
        return selected.pk if selected else GLOBAL_SCOPE
    try:
        return delegation_id(user)
    except PermissionDenied:
        return None


class AtencionesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_id = user.pk
        self.session_key = self.scope['session'].session_key
        self.org_id = await viewer_scope(self.user_id, self.session_key)
        if not self.org_id:
            await self.close(code=4403)
            return
        self.group_name = group_for(self.org_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Clients cannot choose groups, scopes or request record payloads.
        await self.close(code=4400)

    async def tabla_cambio(self, event):
        if await viewer_scope(self.user_id, self.session_key) != self.org_id:
            await self.close(code=4403)
            return
        await self.send_json({'type': 'tabla.cambio'})
