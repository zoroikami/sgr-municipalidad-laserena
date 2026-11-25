import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.test import Client

from gestion import realtime


pytestmark = pytest.mark.django_db(transaction=True)
MODULOS = ('tubo', 'cartas', 'casos', 'sgr')
PERMISOS = {'tubo': 'view_gestiontubo', 'cartas': 'view_carta', 'casos': 'view_casosocial', 'sgr': 'view_actividadsgr'}


@pytest.fixture(autouse=True)
def channel_layer_aislada(settings):
    settings.CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


@pytest.fixture
def headers(mundo):
    result = {}
    for alias, user in mundo['users'].items():
        client = Client()
        client.force_login(user)
        result[alias] = [(b'origin', b'http://testserver'),
                         (b'cookie', f'sessionid={client.cookies["sessionid"].value}'.encode())]
    return result


def socket(modulo, headers):
    from config.asgi import application
    return WebsocketCommunicator(application, f'/ws/modulos/{modulo}/', headers=headers)


@pytest.mark.parametrize('modulo', MODULOS)
async def test_cada_modulo_rechaza_anonimo_cliente_y_falta_de_permiso(mundo, headers, modulo):
    for request_headers, code in (([(b'origin', b'http://testserver')], 4401), (headers['cliente_1'], 4403)):
        ws = socket(modulo, request_headers)
        assert await ws.connect() == (False, code)
        await ws.disconnect()
    @database_sync_to_async
    def quitar_permiso():
        Group.objects.get(name='Consultor').permissions.remove(Permission.objects.get(codename=PERMISOS[modulo]))
    await quitar_permiso()
    ws = socket(modulo, headers['lector_a'])
    assert await ws.connect() == (False, 4403)
    await ws.disconnect()


@pytest.mark.parametrize('modulo', MODULOS)
async def test_cambio_solo_llega_a_su_modulo_delegacion_y_ambito_global(mundo, headers, modulo):
    sockets = [socket(modulo, headers[alias]) for alias in ('lector_a', 'lector_b', 'coordinador')]
    otro = socket('cartas' if modulo != 'cartas' else 'tubo', headers['lector_a'])
    try:
        for ws in [*sockets, otro]:
            assert (await ws.connect())[0]
        await get_channel_layer().group_send(realtime.group_for(mundo['a'].pk, modulo), {'type': 'tabla.cambio'})
        # El ámbito global recibe su propio aviso, emitido por el notificador al confirmar.
        await get_channel_layer().group_send(realtime.group_for(realtime.GLOBAL_SCOPE, modulo), {'type': 'tabla.cambio'})
        assert await sockets[0].receive_json_from() == {'type': 'tabla.cambio'}
        assert await sockets[2].receive_json_from() == {'type': 'tabla.cambio'}
        assert await sockets[1].receive_nothing(timeout=.05)
        assert await otro.receive_nothing(timeout=.05)
    finally:
        for ws in [*sockets, otro]:
            await ws.disconnect()


@pytest.mark.parametrize('modulo', MODULOS)
async def test_sesion_revocada_cierra_tambien_los_nuevos_modulos(mundo, headers, modulo):
    from django.contrib.sessions.models import Session
    ws = socket(modulo, headers['lector_a'])
    assert (await ws.connect())[0]
    key = headers['lector_a'][1][1].decode().split('=', 1)[1]
    await database_sync_to_async(lambda: Session.objects.filter(session_key=key).delete())()
    await get_channel_layer().group_send(realtime.group_for(mundo['a'].pk, modulo), {'type': 'tabla.cambio'})
    assert await ws.receive_output() == {'type': 'websocket.close', 'code': 4403}
    await ws.disconnect()


@pytest.mark.parametrize('modulo', MODULOS)
async def test_notificacion_tras_commit_a_delegacion_y_global_y_nunca_en_rollback(mundo, modulo):
    layer = get_channel_layer()
    topics = ('tubo', 'sgr') if modulo == 'tubo' else (modulo,)
    channels = []
    for topic in topics:
        for scope in (mundo['a'].pk, realtime.GLOBAL_SCOPE):
            channel = await layer.new_channel()
            group = realtime.group_for(scope, topic)
            await layer.group_add(group, channel)
            channels.append((group, channel))
    @database_sync_to_async
    def escribir(rollback=False):
        with transaction.atomic():
            realtime.notify_after_commit(mundo['a'].pk, modulo=modulo)
            if rollback:
                raise ValueError('rollback controlado')
    await escribir()
    for _, channel in channels:
        assert await layer.receive(channel) == {'type': 'tabla.cambio'}
    with pytest.raises(ValueError):
        await escribir(rollback=True)
    for group, channel in channels:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(layer.receive(channel), timeout=.05)
        await layer.group_discard(group, channel)


async def test_modulo_desconocido_origen_ajeno_y_mensajes_del_cliente_no_permitidos(headers):
    ws = socket('desconocido', headers['lector_a'])
    assert await ws.connect() == (False, 4403)
    await ws.disconnect()
    ws = socket('tubo', [(b'origin', b'https://foreign.invalid'), headers['lector_a'][1]])
    assert not (await ws.connect())[0]
    await ws.disconnect()
    ws = socket('tubo', headers['lector_a'])
    assert (await ws.connect())[0]
    await ws.send_json_to({'delegacion': 'global'})
    assert await ws.receive_output() == {'type': 'websocket.close', 'code': 4400}
    await ws.disconnect()
