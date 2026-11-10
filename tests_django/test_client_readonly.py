"""Client role configuration must match the owner-only citizen portal."""
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def support(db):
    return get_user_model().objects.create_superuser('client_role_support', password='Support-test-key-942!')


def test_client_has_read_permission_without_business_write_privileges(mundo):
    user = mundo['users']['cliente_1']
    assert user.has_perm('gestion.view_atencion')
    for action in ['add', 'change', 'delete']:
        assert not user.has_perm(f'gestion.{action}_atencion')
    assert not user.has_perm('cuentas.view_cuentas')


def test_common_scope_cannot_include_another_clients_records(mundo):
    from gestion.access import scoped
    from gestion.models import Atencion, ItemMeta
    user = mundo['users']['cliente_1']
    assert list(scoped(user, Atencion)) == [mundo['atn_a']]
    assert not scoped(user, ItemMeta).exists()


def test_client_reads_only_owned_records_even_with_extra_group_permissions(client, mundo):
    user = mundo['users']['cliente_1']
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label='gestion'))
    client.force_login(user)
    page = client.get(reverse('gestion:portal'))
    assert page.status_code == 200
    assert list(page.context['page_obj']) == [mundo['atn_a']]
    assert client.get(reverse('gestion:portal_detalle', args=[mundo['atn_a'].pk])).status_code == 200
    for key in ['atn_2', 'atn_b']:
        assert client.get(reverse('gestion:portal_detalle', args=[mundo[key].pk])).status_code == 404
    for route, args in [('crear', ['atenciones']), ('editar', ['atenciones', mundo['atn_a'].pk]),
                        ('archivar', ['atenciones', mundo['atn_a'].pk])]:
        assert client.post(reverse('gestion:' + route, args=args), {}).status_code == 403
    for module in ['atenciones', 'metas', 'tipos', 'subatenciones', 'delegaciones']:
        assert client.get(reverse('gestion:exportar', args=[module])).status_code == 403
    for route in ['usuarios', 'roles']:
        assert client.get(reverse('cuentas:' + route)).status_code == 403


def test_roles_editor_offers_only_reading_atenciones_for_client(client, support, mundo):
    client.force_login(support)
    group = Group.objects.get(name='Cliente')
    response = client.get(reverse('cuentas:roles'), {'grupo': group.pk})
    assert response.status_code == 200
    form = response.context['form']
    assert list(form.fields['permissions'].queryset.values_list('codename', flat=True)) == ['view_atencion']
    assert list(form.initial['permissions'].values_list('codename', flat=True)) == ['view_atencion']
    assert len(response.context['permission_sections']) == 1
    assert response.context['permission_sections'][0]['items'][0]['label'] == 'Consultar'


@pytest.mark.parametrize('codename', ['add_atencion', 'change_atencion', 'delete_atencion', 'view_user', 'view_itemmeta'])
def test_roles_editor_rejects_forged_permissions_for_client(client, support, mundo, codename):
    client.force_login(support)
    group = Group.objects.get(name='Cliente')
    forbidden = Permission.objects.get(codename=codename)
    response = client.post(reverse('cuentas:roles'), {'group': group.pk, 'permissions': [forbidden.pk]})
    assert response.status_code == 200
    assert response.context['form'].errors.get('permissions')
    assert list(group.permissions.values_list('codename', flat=True)) == ['view_atencion']


def test_removing_client_read_permission_revokes_portal_access(client, support, mundo):
    client.force_login(support)
    group = Group.objects.get(name='Cliente')
    assert client.post(reverse('cuentas:roles'), {'group': group.pk, 'permissions': []}).status_code == 302
    client.force_login(mundo['users']['cliente_1'])
    assert client.get(reverse('gestion:portal')).status_code == 403
    assert client.get(reverse('gestion:portal_detalle', args=[mundo['atn_a'].pk])).status_code == 403


def test_client_permission_migration_preserves_accounts_and_membership(mundo):
    migration = import_module('cuentas.migrations.0005_client_readonly')
    user = mundo['users']['cliente_1']
    password = user.password
    group = user.groups.get(name='Cliente')
    group.permissions.add(Permission.objects.get(codename='change_atencion'))
    for _ in range(2):
        migration.forwards(apps, SimpleNamespace(connection=connection))
    user.refresh_from_db()
    assert user.password == password and user.groups.filter(pk=group.pk).exists()
    assert list(group.permissions.values_list('codename', flat=True)) == ['view_atencion']
