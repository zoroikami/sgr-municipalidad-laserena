import asyncio

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.db import transaction
from django.test import Client

from gestion.realtime import GLOBAL_SCOPE, group_for, notify_after_commit

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def session_headers(mundo):
    headers = {}
    for alias, user in mundo['users'].items():
        client = Client()
        client.force_login(user)
        cookie = f'sessionid={client.cookies["sessionid"].value}'.encode()
        headers[alias] = [(b'origin', b'http://testserver'), (b'cookie', cookie)]
    return headers


async def connection(headers):
    from config.asgi import application
    return WebsocketCommunicator(application, '/ws/atenciones/', headers=headers)


async def test_websocket_rejects_anonymous_bad_origin_and_clients(session_headers):
    for headers in [[(b'origin', b'http://testserver')],
                    [(b'origin', b'https://foreign.invalid')] + session_headers['lector_a'][1:],
                    session_headers['cliente_1']]:
        socket = await connection(headers)
        connected, _ = await socket.connect()
        assert not connected
        await socket.disconnect()


async def test_business_event_reaches_only_reader_in_same_scope(mundo, session_headers):
    layer = get_channel_layer()
    socket_a = await connection(session_headers['lector_a'])
    socket_b = await connection(session_headers['lector_b'])
    assert (await socket_a.connect())[0]
    assert (await socket_b.connect())[0]
    await layer.group_send(group_for(mundo['a'].pk), {'type': 'tabla.cambio'})
    assert await socket_a.receive_json_from() == {'type': 'tabla.cambio'}
    assert await socket_b.receive_nothing(timeout=0.15)
    await socket_a.disconnect()
    await socket_b.disconnect()


async def test_existing_socket_is_closed_when_its_session_is_revoked(mundo, session_headers):
    from channels.db import database_sync_to_async
    from django.contrib.sessions.models import Session
    socket = await connection(session_headers['lector_a'])
    assert (await socket.connect())[0]
    key = session_headers['lector_a'][1][1].decode().split('=', 1)[1]
    await database_sync_to_async(lambda: Session.objects.filter(session_key=key).delete())()
    await get_channel_layer().group_send(group_for(mundo['a'].pk), {'type': 'tabla.cambio'})
    message = await socket.receive_output()
    assert message['type'] == 'websocket.close'
    await socket.disconnect()


async def test_superadmin_socket_uses_selected_scope_and_revalidates_scope_changes(mundo):
    from channels.db import database_sync_to_async
    from django.contrib.auth import get_user_model

    @database_sync_to_async
    def prepare():
        user = get_user_model().objects.create_superuser('scoped_support', password='Scoped-test-key-921!')
        client = Client()
        client.force_login(user)
        assert client.post('/cuentas/delegacion/', {'delegacion': mundo['a'].pk}).status_code == 302
        headers = [(b'origin', b'http://testserver'),
                   (b'cookie', f'sessionid={client.cookies["sessionid"].value}'.encode())]
        return client, headers

    client, headers = await prepare()
    socket = await connection(headers)
    assert (await socket.connect())[0]
    layer = get_channel_layer()
    await layer.group_send(group_for(mundo['b'].pk), {'type': 'tabla.cambio'})
    assert await socket.receive_nothing(timeout=0.15)
    await layer.group_send(group_for(mundo['a'].pk), {'type': 'tabla.cambio'})
    assert await socket.receive_json_from() == {'type': 'tabla.cambio'}
    await database_sync_to_async(client.post)('/cuentas/delegacion/', {'delegacion': mundo['b'].pk})
    await layer.group_send(group_for(mundo['a'].pk), {'type': 'tabla.cambio'})
    assert (await socket.receive_output())['type'] == 'websocket.close'
    await socket.disconnect()
    replacement = await connection(headers)
    assert (await replacement.connect())[0]
    await layer.group_send(group_for(mundo['b'].pk), {'type': 'tabla.cambio'})
    assert await replacement.receive_json_from() == {'type': 'tabla.cambio'}
    await replacement.disconnect()


async def test_notification_is_emitted_after_commit_and_never_on_rollback(mundo):
    from channels.db import database_sync_to_async
    layer = get_channel_layer()
    channel = await layer.new_channel()
    global_channel = await layer.new_channel()
    await layer.group_add(group_for(mundo['a'].pk), channel)
    await layer.group_add(group_for(GLOBAL_SCOPE), global_channel)

    @database_sync_to_async
    def commit():
        with transaction.atomic():
            notify_after_commit(mundo['a'].pk)

    @database_sync_to_async
    def rollback():
        with pytest.raises(ValueError), transaction.atomic():
            notify_after_commit(mundo['a'].pk)
            raise ValueError('rollback controlado')

    await commit()
    result = await layer.receive(channel)
    assert result == {'type': 'tabla.cambio'}
    assert await layer.receive(global_channel) == {'type': 'tabla.cambio'}
    await rollback()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(layer.receive(channel), timeout=0.15)
    await layer.group_discard(group_for(mundo['a'].pk), channel)
    await layer.group_discard(group_for(GLOBAL_SCOPE), global_channel)
