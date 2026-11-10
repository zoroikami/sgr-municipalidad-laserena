"""Municipal sign-in must not send users to the technical Django console."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def technician():
    return get_user_model().objects.create_superuser('soporte_prueba', 'soporte@example.test', 'Soporte#Prueba2026!')


def test_superuser_without_delegation_signs_in_and_sees_all_delegations(client, technician, mundo):
    response = client.post(reverse('cuentas:login'), {'username': technician.username, 'password': 'Soporte#Prueba2026!'})
    assert response.status_code == 302
    assert response['Location'] == reverse('gestion:inicio')
    home = client.get(response['Location'])
    assert home.status_code == 200
    assert 'Todas las delegaciones' in home.content.decode()
    for module in ('atenciones', 'metas', 'tipos', 'subatenciones', 'delegaciones'):
        assert client.get(reverse('gestion:listado', args=[module])).context['page_obj'].paginator.count >= 2
    for route in ('usuarios', 'roles', 'perfil'):
        assert client.get(reverse('cuentas:' + route)).status_code == 200


def test_superuser_can_create_an_attention_in_an_explicit_delegation(client, technician, mundo):
    client.force_login(technician)
    url = reverse('gestion:crear', args=['atenciones'])
    fields = {
        'delegacion': mundo['b'].pk, 'tipo': mundo['tipo_b'].pk,
        'subatencion': mundo['sub_b'].pk, 'solicitante_nombre': 'Registro global',
        'solicitante_rut': '12.345.678-5', 'descripcion': 'Prueba', 'estado': 'Ingresada',
    }
    bad = client.post(url, fields | {'subatencion': mundo['sub_a'].pk})
    assert 'subatencion' in bad.context['form'].errors
    response = client.post(url, fields)
    assert response.status_code == 302
    from gestion.models import Atencion
    record = Atencion.objects.get(solicitante_nombre='Registro global')
    assert record.delegacion_id == mundo['b'].pk and record.responsable_id == technician.pk


def test_technical_console_remains_available_at_its_explicit_address(client, technician):
    client.force_login(technician)
    assert client.get(reverse('admin:index')).status_code == 200


def test_municipal_administrator_login_opens_real_frontend(client, mundo):
    response = client.post(reverse('cuentas:login'), {'username': 'admin_a', 'password': 'Ensayo#Privado2026'})
    assert response.status_code == 302
    assert response['Location'] == reverse('gestion:inicio')
    home = client.get(response['Location'])
    assert home.status_code == 200
    assert 'module-previews' in home.content.decode()
    assert 'Gestión municipal' in home.content.decode()


def test_superuser_with_assigned_profile_can_still_use_municipal_frontend(client, mundo):
    user = mundo['users']['admin_a']
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=['is_superuser', 'is_staff'])
    response = client.post(reverse('cuentas:login'), {'username': 'admin_a', 'password': 'Ensayo#Privado2026'})
    assert response.status_code == 302
    assert client.get(response['Location']).status_code == 200
