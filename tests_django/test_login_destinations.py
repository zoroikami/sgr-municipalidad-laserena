"""Municipal sign-in must not send users to the technical Django console."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def technician():
    return get_user_model().objects.create_superuser('soporte_prueba', 'soporte@example.test', 'Soporte#Prueba2026!')


def test_unscoped_technician_is_not_authenticated_through_municipal_login(client, technician):
    response = client.post(reverse('cuentas:login'), {'username': technician.username, 'password': 'Soporte#Prueba2026!'})
    assert response.status_code == 200
    assert response.context['form'].non_field_errors()
    assert 'delegación' in str(response.context['form'].non_field_errors())
    assert '_auth_user_id' not in client.session


def test_existing_technical_session_returns_to_public_municipal_login(client, technician):
    client.force_login(technician)
    response = client.get(reverse('gestion:inicio'))
    assert response.status_code == 302
    assert response['Location'] == reverse('cuentas:login')
    login = client.get(response['Location'])
    assert login.status_code == 200
    assert 'sgr-public' in login.content.decode()
    assert '<aside' not in login.content.decode()


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
