import datetime

import pytest
from django.urls import reverse
from gestion.models import Atencion

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('filters,expected', [
    ({}, 1), ({'desde': '2026-11-09', 'hasta': '2026-11-09'}, 1),
    ({'desde': '2026-11-10'}, 0), ({'hasta': '2026-11-08'}, 0),
])
def test_dates_use_chilean_day_and_preserve_ownership(client, mundo, filters, expected):
    # UTC Nov 10 01:00 is still Nov 9 in Santiago. Both owners have the same date.
    Atencion.objects.update(created_at=datetime.datetime(2026, 11, 10, 1, tzinfo=datetime.timezone.utc))
    client.force_login(mundo['users']['cliente_1'])
    response = client.get(reverse('gestion:portal'), filters)
    assert response.status_code == 200
    assert response.context['page_obj'].paginator.count == expected
    assert all(row.cliente_id == mundo['users']['cliente_1'].pk for row in response.context['page_obj'])


@pytest.mark.parametrize('filters', [
    {'desde': '2026-11-10', 'hasta': '2026-11-09'}, {'desde': 'invalid'},
])
def test_invalid_dates_show_errors_without_records_or_writes(client, mundo, filters):
    client.force_login(mundo['users']['cliente_1'])
    before = list(Atencion.objects.values())
    response = client.get(reverse('gestion:portal'), filters)
    assert response.context['filter_form'].errors
    assert response.context['page_obj'].paginator.count == 0
    assert list(Atencion.objects.values()) == before


def test_pagination_keeps_date_filters(client, mundo):
    template = mundo['atn_a']
    for i in range(16):
        Atencion.objects.create(delegacion=template.delegacion, tipo=template.tipo,
            subatencion=template.subatencion, responsable=template.responsable,
            cliente=template.cliente, solicitante_nombre=f'Prueba {i}',
            solicitante_rut=template.solicitante_rut, descripcion='Prueba paginación')
    Atencion.objects.update(created_at=datetime.datetime(2026, 11, 10, 12, tzinfo=datetime.timezone.utc))
    client.force_login(mundo['users']['cliente_1'])
    response = client.get(reverse('gestion:portal'), {'desde': '2026-11-10', 'hasta': '2026-11-10'})
    assert response.context['page_obj'].paginator.count == 17
    assert 'desde=2026-11-10&amp;hasta=2026-11-10&amp;pagina=2' in response.content.decode()
