from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from tests_django.test_historial_estados import tubo
from tests_django.test_tablero_cartas import carta

pytestmark = pytest.mark.django_db


def crear(mundo, kind, fecha, **changes):
    if kind == 'cartas':
        return carta(mundo, fecha_actividad=fecha, **changes)
    return tubo(mundo, fecha_compromiso=fecha, **changes)


def tablero(client, kind):
    return client.get('/cartas/tablero/' if kind == 'cartas' else '/tubo/')


def tarjeta(response, obj):
    return next(row for column in response.context['columnas'] for row in column['registros'] if row.pk == obj.pk)


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
@pytest.mark.parametrize('days,label', [(-1, 'Vencido'), (0, 'Vence hoy'),
    (1, 'Vence en 1 día'), (3, 'Vence en 3 días'), (4, ''), (None, '')])
def test_avisa_plazos_cercanos_y_vencidos_con_limites_inclusivos(client, mundo, kind, days, label):
    today = timezone.localdate()
    obj = crear(mundo, kind, today + timedelta(days=days) if days is not None else None)
    client.force_login(mundo['users']['lector_a'])
    response = tablero(client, kind)
    assert response.status_code == 200
    assert response.context['vencidos'] == (1 if days == -1 else 0)
    assert tarjeta(response, obj).plazo == label
    if label:
        assert label in response.content.decode()


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
def test_resumen_vencidos_y_orden_por_fecha_respetan_ambito_y_archivo(client, mundo, kind):
    today = timezone.localdate()
    tomorrow = crear(mundo, kind, today + timedelta(days=1))
    overdue = crear(mundo, kind, today - timedelta(days=1))
    no_date = crear(mundo, kind, None)
    other_person = {'encargado': mundo['users']['lector_b']} if kind == 'cartas' else {'responsable': mundo['users']['lector_b']}
    crear(mundo, kind, today - timedelta(days=1), delegacion=mundo['b'], **other_person)
    crear(mundo, kind, today - timedelta(days=1), deleted_at=timezone.now())
    client.force_login(mundo['users']['lector_a'])
    response = tablero(client, kind)
    assert response.context['vencidos'] == 1
    rows = [row.pk for col in response.context['columnas'] for row in col['registros']]
    assert rows == [overdue.pk, tomorrow.pk, no_date.pk]
    assert 'Vencidos' in response.content.decode()


@pytest.mark.parametrize('kind,closed', [('cartas', 'Finalizada'), ('tubo', 'Realizado')])
def test_cierre_posterior_al_compromiso_usa_historial_no_fecha_de_edicion(client, mundo, kind, closed):
    today = timezone.localdate()
    due = today - timedelta(days=2)
    late = crear(mundo, kind, due, estado=closed)
    on_time = crear(mundo, kind, due, estado=closed)
    unknown = crear(mundo, kind, due, estado=closed)
    for obj, date in [(late, today), (on_time, due)]:
        obj.historial_estados.create(autor=mundo['users']['editor_a'], estado_anterior='En proceso',
            estado_nuevo=closed, fecha=timezone.make_aware(datetime.combine(date, time(10))), fecha_objetivo=due)
    client.force_login(mundo['users']['lector_a'])
    response = tablero(client, kind)
    assert response.context['vencidos'] == 0
    assert tarjeta(response, late).plazo == 'Realizado fuera de plazo'
    assert tarjeta(response, on_time).plazo == ''
    assert tarjeta(response, unknown).plazo == ''
    assert 'Realizado fuera de plazo' in response.content.decode()


def test_carta_aprobada_o_no_aplica_no_se_cuenta_como_pendiente_vencido(client, mundo):
    due = timezone.localdate() - timedelta(days=5)
    approved = carta(mundo, estado='Aprobada', fecha_actividad=due)
    not_applicable = carta(mundo, estado='No aplica', fecha_actividad=due)
    client.force_login(mundo['users']['lector_a'])
    response = tablero(client, 'cartas')
    assert response.context['vencidos'] == 0
    assert tarjeta(response, approved).plazo == tarjeta(response, not_applicable).plazo == ''


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
def test_cambio_de_fecha_posterior_al_cierre_no_borra_el_atraso_historico(client, mundo, kind):
    due = timezone.localdate() - timedelta(days=2)
    obj = crear(mundo, kind, due, estado='Aprobada' if kind == 'cartas' else 'En proceso')
    client.force_login(mundo['users']['editor_a'])
    url = f'/cartas/{obj.pk}/avanzar/' if kind == 'cartas' else f'/tubo/{obj.pk}/avanzar/'
    client.post(url, {'desde': obj.estado, 'estado': 'Finalizada'})
    field = 'fecha_actividad' if kind == 'cartas' else 'fecha_compromiso'
    setattr(obj, field, timezone.localdate() + timedelta(days=4))
    obj.refresh_from_db(fields=['estado'])
    obj.save(update_fields=[field])
    assert tarjeta(tablero(client, kind), obj).plazo == 'Realizado fuera de plazo'
    setattr(obj, field, None)
    obj.save(update_fields=[field])
    assert tarjeta(tablero(client, kind), obj).plazo == 'Realizado fuera de plazo'


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
@pytest.mark.parametrize('original_days', [0, None])
def test_adelantar_fecha_despues_de_cierre_no_inventa_atraso(client, mundo, kind, original_days):
    due = timezone.localdate() if original_days == 0 else None
    obj = crear(mundo, kind, due, estado='Aprobada' if kind == 'cartas' else 'En proceso')
    client.force_login(mundo['users']['editor_a'])
    url = f'/cartas/{obj.pk}/avanzar/' if kind == 'cartas' else f'/tubo/{obj.pk}/avanzar/'
    assert client.post(url, {'desde': obj.estado, 'estado': 'Finalizada'}).status_code == 302
    field = 'fecha_actividad' if kind == 'cartas' else 'fecha_compromiso'
    type(obj).objects.filter(pk=obj.pk).update(**{field:timezone.localdate()-timedelta(days=10)})
    assert tarjeta(tablero(client, kind), obj).plazo == ''
