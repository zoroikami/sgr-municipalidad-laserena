import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_limited_administrator_cannot_use_django_admin_even_if_staff_flag_is_set(client, mundo):
    user = mundo['users']['admin_a']
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    client.force_login(user)
    for url in ['/admin/', '/admin/auth/user/', '/admin/gestion/atencion/']:
        assert client.get(url).status_code in [302, 403]


def test_account_manager_requires_real_django_permission(client, mundo):
    user = mundo['users']['admin_a']
    group = Group.objects.get(name='Administrador')
    group.permissions.remove(*Permission.objects.filter(content_type__app_label='cuentas', codename='view_cuentas'))
    client.force_login(user)
    assert client.get(reverse('cuentas:usuarios')).status_code == 403


def test_account_manager_lists_only_own_scope_and_readers_are_denied(client, mundo):
    client.force_login(mundo['users']['admin_a'])
    response = client.get(reverse('cuentas:usuarios'))
    assert response.status_code == 200
    assert 'lector_a' in response.content.decode()
    assert 'lector_b' not in response.content.decode()
    client.force_login(mundo['users']['lector_a'])
    assert client.get(reverse('cuentas:usuarios')).status_code == 403
