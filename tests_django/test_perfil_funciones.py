import pytest
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_perfil_social_muestra_funciones_de_todas_las_areas(client, mundo):
    user = mundo['users']['editor_a']
    user.perfil.cargo_sgr = 'social'
    user.perfil.save(update_fields=['cargo_sgr'])
    client.force_login(user)

    response = client.get(reverse('cuentas:perfil'))

    assert response.status_code == 200
    assert response.context['cargo_nombre'] == 'Gestor social'
    assert len(response.context['funciones']) == 15
    html = response.content.decode()
    for text in ('Recepción y evaluación de casos', 'Diagnóstico comunitario',
                 'Gestionar recursos para la atención de casos', 'Capacitación y actualización',
                 'Apoyo a la gestión municipal'):
        assert text in html


def test_delegado_sin_cargo_cargado_ve_todas_sus_funciones(client, mundo):
    user = mundo['users']['admin_a']
    assert not user.perfil.cargo_sgr
    client.force_login(user)

    response = client.get(reverse('cuentas:perfil'))

    assert response.status_code == 200
    assert response.context['cargo_nombre'] == 'Delegado'
    assert len(response.context['funciones']) == 11
    assert 'Visitar periódicamente Juntas de vecinos' in response.content.decode()
    assert 'Ejecutar otras funciones que la ley señale' in response.content.decode()


def test_perfil_sin_cargo_indica_como_asignarlo(client, mundo):
    client.force_login(mundo['users']['editor_a'])

    response = client.get(reverse('cuentas:perfil'))

    assert response.status_code == 200
    assert not response.context['funciones']
    assert 'Sin cargo asignado: pide a administración que lo registre en Usuarios' in response.content.decode()


def test_catalogo_cubre_cada_funcion_de_los_siete_cargos_y_distingue_seguridad():
    from gestion.funcionarios import FUNCIONES
    from gestion.integrado import CARGOS

    assert set(FUNCIONES) == set(dict(CARGOS))
    assert {cargo: len(FUNCIONES[cargo]) for cargo in FUNCIONES if cargo != 'seguridad'} == {
        'delegado': 11, 'social': 15, 'administrativo': 11, 'organizaciones': 8,
        'compras': 5, 'planificacion': 12, 'servicios': 9,
    }


def test_seguridad_informa_que_sus_funciones_provienen_de_la_matriz(client, mundo):
    user = mundo['users']['editor_a']
    user.perfil.cargo_sgr = 'seguridad'
    user.perfil.save(update_fields=['cargo_sgr'])
    client.force_login(user)

    response = client.get(reverse('cuentas:perfil'))

    assert response.status_code == 200
    assert 'Funciones según la matriz SGR (hoja GES SEG)' in response.content.decode()
    assert 'Descriptor de funciones 2026' not in response.content.decode()
