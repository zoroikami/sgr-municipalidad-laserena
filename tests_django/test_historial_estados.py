import pytest

from gestion.models import GestionTubo
from tests_django.test_cartas import data
from tests_django.test_tablero_cartas import carta

pytestmark = pytest.mark.django_db


def tubo(mundo, **changes):
    return GestionTubo.objects.create(**{'delegacion': mundo['a'], 'nombre': f'Gestión de prueba {GestionTubo.all_objects.count() + 1}',
        'solicitante': 'Vecino de prueba', 'responsable': mundo['users']['editor_a'], **changes})


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
def test_transicion_de_tablero_conserva_historial_visible_sin_duplicar_reintento(client, mundo, kind):
    obj = carta(mundo) if kind == 'cartas' else tubo(mundo)
    before, after = ('En proceso', 'Aprobada') if kind == 'cartas' else ('Ingresado', 'Pendiente')
    url = f'/cartas/{obj.pk}/avanzar/' if kind == 'cartas' else f'/tubo/{obj.pk}/avanzar/'
    client.force_login(mundo['users']['editor_a'])
    post = {'desde': before, 'estado': after, 'observacion': 'Verificado por oficina <script>alert(1)</script>'}
    assert client.post(url, post).status_code == 302
    assert client.post(url, post).status_code == 302
    detail = client.get(f'/gestion/{kind}/{obj.pk}/')
    assert 'Historial de estados' in detail.content.decode()
    rows = list(obj.historial_estados.all())
    assert len(rows) == 1
    assert (rows[0].estado_anterior, rows[0].estado_nuevo) == (before, after)
    assert rows[0].autor == mundo['users']['editor_a'] and rows[0].fecha is not None
    body = detail.content.decode()
    assert 'Verificado por oficina &lt;script&gt;' in body
    assert '<script>alert(1)</script>' not in body
    assert before in body and after in body and 'editor_a' in body


def test_editar_carta_registra_cambio_y_no_registra_edicion_sin_transicion(client, mundo):
    obj = carta(mundo)
    client.force_login(mundo['users']['editor_a'])
    url = f'/gestion/cartas/{obj.pk}/editar/'
    payload = data(mundo, estado='Aprobada', observacion_estado='Validación de la carta')
    assert client.post(url, payload).status_code == 302
    body = client.get(f'/gestion/cartas/{obj.pk}/').content.decode()
    assert 'Validación de la carta' in body
    entry = obj.historial_estados.get()
    assert (entry.estado_anterior, entry.estado_nuevo) == ('En proceso', 'Aprobada')
    assert client.post(url, payload).status_code == 302
    assert obj.historial_estados.count() == 1


def test_editar_tubo_permite_avance_y_preserva_su_historial(client, mundo):
    obj = tubo(mundo)
    client.force_login(mundo['users']['editor_a'])
    url = f'/gestion/tubo/{obj.pk}/editar/'
    form = client.get(url).context['form']
    payload = {key: value if value is not None else '' for key, value in form.initial.items()}
    payload.update(estado='Pendiente', observacion_estado='Se asignó revisión')
    assert client.post(url, payload).status_code == 302
    obj.refresh_from_db()
    assert obj.estado == 'Pendiente'
    entry = obj.historial_estados.get()
    assert entry.estado_anterior == 'Ingresado' and entry.observacion == 'Se asignó revisión'


def test_edicion_no_elude_transiciones_controladas_de_cartas(client, mundo):
    obj = carta(mundo)
    client.force_login(mundo['users']['editor_a'])
    response = client.post(f'/gestion/cartas/{obj.pk}/editar/', data(mundo, estado='Finalizada'))
    assert response.status_code == 200
    assert 'estado' in response.context['form'].errors
    obj.refresh_from_db()
    assert obj.estado == 'En proceso'


def test_historial_mantiene_ambito_y_solo_lectura_para_consultor(client, mundo):
    obj = carta(mundo)
    client.force_login(mundo['users']['editor_a'])
    client.post(f'/cartas/{obj.pk}/avanzar/', {'desde': 'En proceso', 'estado': 'Aprobada', 'observacion': 'Nota privada del ámbito'})
    client.force_login(mundo['users']['lector_a'])
    assert 'Nota privada del ámbito' in client.get(f'/gestion/cartas/{obj.pk}/').content.decode()
    assert client.post(f'/cartas/{obj.pk}/avanzar/', {'desde': 'Aprobada', 'estado': 'Finalizada'}).status_code == 403
    client.force_login(mundo['users']['lector_b'])
    assert client.get(f'/gestion/cartas/{obj.pk}/').status_code == 404
    assert obj.historial_estados.count() == 1


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
def test_observacion_demasiado_larga_no_cambia_estado(client, mundo, kind):
    obj = carta(mundo) if kind == 'cartas' else tubo(mundo)
    original = obj.estado
    url = f'/cartas/{obj.pk}/avanzar/' if kind == 'cartas' else f'/tubo/{obj.pk}/avanzar/'
    client.force_login(mundo['users']['editor_a'])
    client.post(url, {'desde': original, 'estado': 'Aprobada', 'observacion': 'x' * 2001})
    obj.refresh_from_db()
    assert obj.estado == original


@pytest.mark.parametrize('kind', ['cartas', 'tubo'])
def test_fallo_de_historial_revierte_el_cambio_de_estado(client, mundo, monkeypatch, kind):
    from gestion.models import HistorialEstado
    obj = carta(mundo) if kind == 'cartas' else tubo(mundo)
    original = obj.estado
    client.force_login(mundo['users']['editor_a'])

    def fallar(**kwargs):
        raise RuntimeError('Fallo de almacenamiento de historial simulado')

    monkeypatch.setattr(HistorialEstado.objects, 'create', fallar)
    url = f'/cartas/{obj.pk}/avanzar/' if kind == 'cartas' else f'/tubo/{obj.pk}/avanzar/'
    with pytest.raises(RuntimeError):
        client.post(url, {'desde': original, 'estado': 'Aprobada'})
    obj.refresh_from_db()
    assert obj.estado == original
    assert obj.historial_estados.count() == 0
