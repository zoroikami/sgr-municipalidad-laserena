import pytest
from django.test import Client
from django.urls import reverse

from gestion.models import Carta

pytestmark = pytest.mark.django_db


def carta(mundo, **changes):
    return Carta.objects.create(**{
        'delegacion': mundo['a'], 'nombre': 'Reunión de prueba',
        'numero_ingreso': 'OP-101', 'remite': 'Organización de prueba',
        'encargado': mundo['users']['editor_a'], 'derivada_a': 'Unidad de apoyo',
        **changes,
    })


def test_tablero_cartas_agrupa_estados_y_excluye_ajenos_y_archivados(client, mundo):
    from django.utils import timezone
    local = carta(mundo)
    carta(mundo, estado='Aprobada')
    carta(mundo, estado='Finalizada')
    carta(mundo, estado='No aplica')
    carta(mundo, nombre='Reservada de otra delegación', delegacion=mundo['b'], encargado=mundo['users']['lector_b'])
    carta(mundo, nombre='Archivada', deleted_at=timezone.now())
    client.force_login(mundo['users']['editor_a'])
    response = client.get('/cartas/tablero/')
    assert response.status_code == 200
    assert [col['cantidad'] for col in response.context['columnas']] == [1, 1, 1, 1]
    assert response.context['total'] == 4
    body = response.content.decode()
    for text in [local.codigo, 'OP-101', 'Delegado', 'Organización de prueba', 'Unidad de apoyo', 'Ver detalle']:
        assert text in body
    assert 'Reservada de otra delegación' not in body and 'Archivada' not in body
    assert '/cartas/tablero/' in client.get('/gestion/cartas/').content.decode()
    assert '/cartas/tablero/' in client.get('/').content.decode()


@pytest.mark.parametrize('alias,status,can_move', [
    ('coordinador', 200, True), ('admin_a', 200, True), ('editor_a', 200, True),
    ('lector_a', 200, False), ('cliente_1', 403, False),
])
def test_tablero_cartas_respeta_permisos(client, mundo, alias, status, can_move):
    obj = carta(mundo)
    client.force_login(mundo['users'][alias])
    response = client.get('/cartas/tablero/')
    assert response.status_code == status
    if status == 200:
        assert ('name="desde"' in response.content.decode()) == can_move
    result = client.post(f'/cartas/{obj.pk}/avanzar/', {'desde': 'En proceso', 'estado': 'Aprobada'})
    assert result.status_code == (302 if can_move else 403)
    obj.refresh_from_db()
    assert obj.estado == ('Aprobada' if can_move else 'En proceso')


@pytest.mark.parametrize('origin,dest,expected', [
    ('En proceso', 'Aprobada', 'Aprobada'), ('Aprobada', 'Finalizada', 'Finalizada'),
    ('En proceso', 'No aplica', 'No aplica'), ('En proceso', 'Finalizada', 'En proceso'),
    ('Finalizada', 'Aprobada', 'Finalizada'), ('No aplica', 'En proceso', 'No aplica'),
    ('Aprobada', 'No aplica', 'Aprobada'),
])
def test_tablero_cartas_transiciones_controladas(client, mundo, origin, dest, expected):
    obj = carta(mundo, estado=origin)
    client.force_login(mundo['users']['editor_a'])
    url = f'/cartas/{obj.pk}/avanzar/'
    assert client.get(url).status_code == 405
    assert client.post(url, {'desde': origin, 'estado': dest}).status_code == 302
    obj.refresh_from_db()
    assert obj.estado == expected


def test_tablero_cartas_rechaza_origen_obsoleto_y_registro_ajeno(client, mundo):
    obj = carta(mundo, estado='Aprobada')
    foreign = carta(mundo, delegacion=mundo['b'], encargado=mundo['users']['lector_b'])
    client.force_login(mundo['users']['editor_a'])
    assert client.post(f'/cartas/{obj.pk}/avanzar/', {'desde': 'En proceso', 'estado': 'No aplica'}).status_code == 302
    assert client.post(f'/cartas/{foreign.pk}/avanzar/', {'desde': 'En proceso', 'estado': 'Aprobada'}).status_code == 404
    obj.refresh_from_db()
    assert obj.estado == 'Aprobada'


def test_tablero_cartas_exige_csrf(mundo):
    obj = carta(mundo)
    client = Client(enforce_csrf_checks=True)
    client.force_login(mundo['users']['editor_a'])
    assert client.post(f'/cartas/{obj.pk}/avanzar/', {'desde': 'En proceso', 'estado': 'Aprobada'}).status_code == 403
    obj.refresh_from_db()
    assert obj.estado == 'En proceso'
