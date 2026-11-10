"""Session scope and restored roles must be enforced beyond the visible selector."""
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from openpyxl import load_workbook

from cuentas.roles import configure_groups
from gestion.models import Atencion

pytestmark = pytest.mark.django_db


@pytest.fixture
def global_user(db):
    return get_user_model().objects.create_superuser('global_operator', password='Global-test-key-921!')


@pytest.fixture
def coordinator(mundo):
    user = get_user_model().objects.create_user('coordinator', password='Coordinator-test-key-921!')
    user.groups.add(Group.objects.get_or_create(name='Coordinador')[0])
    return user


def select(client, delegation):
    return client.post('/cuentas/delegacion/', {'delegacion': delegation, 'next': '/'})


def test_superadmin_selection_filters_home_lists_details_exports_and_catalog(client, global_user, mundo):
    client.force_login(global_user)
    assert select(client, mundo['b'].pk).status_code == 302
    home = client.get('/')
    atenciones = next(row for row in home.context['stats'] if row['modulo'] == 'atenciones')
    assert atenciones['total'] == 1
    listing = client.get(reverse('gestion:listado', args=['atenciones']))
    assert list(listing.context['page_obj']) == [mundo['atn_b']]
    assert client.get(reverse('gestion:detalle', args=['atenciones', mundo['atn_a'].pk])).status_code == 404
    catalog = client.get('/catalogos/subatenciones/', {'tipo': mundo['tipo_a'].pk})
    assert catalog.json()['results'] == []
    export = client.get(reverse('gestion:exportar', args=['atenciones']))
    rows = list(load_workbook(BytesIO(export.content)).active.values)
    assert len(rows) == 2 and rows[1][1] == 'Bernarda Norte'
    assert select(client, '').status_code == 302
    assert client.get(reverse('gestion:listado', args=['atenciones'])).context['page_obj'].paginator.count == 3


def test_selection_is_session_local_and_clears_previous_filters(client, global_user, mundo):
    from django.test import Client
    client.force_login(global_user)
    other = Client()
    other.force_login(global_user)
    client.get(reverse('gestion:listado', args=['atenciones']), {'q': 'Alicia', 'responsable': mundo['users']['editor_a'].pk})
    assert select(client, mundo['b'].pk).status_code == 302
    listing = client.get(reverse('gestion:listado', args=['atenciones']))
    assert listing.context['page_obj'].paginator.count == 1
    assert other.get(reverse('gestion:listado', args=['atenciones'])).context['page_obj'].paginator.count == 3
    global_user.refresh_from_db()
    assert not hasattr(global_user, 'perfil')


@pytest.mark.parametrize('alias', ['admin_a', 'editor_a', 'lector_a', 'cliente_1'])
def test_local_accounts_cannot_switch_scope_even_with_forged_session(client, mundo, alias):
    client.force_login(mundo['users'][alias])
    assert select(client, mundo['b'].pk).status_code == 403
    session = client.session
    session['active_delegation_id'] = mundo['b'].pk
    session.save()
    url = reverse('gestion:portal') if alias == 'cliente_1' else reverse('gestion:listado', args=['atenciones'])
    response = client.get(url)
    assert all(record.delegacion_id == mundo['a'].pk for record in response.context['page_obj'])


def test_selector_rejects_get_invalid_inactive_scope_and_external_redirect(client, global_user, mundo):
    client.force_login(global_user)
    assert client.get('/cuentas/delegacion/').status_code == 405
    for value in ['abc', '999999999999999999999999999999999999', '999999']:
        assert select(client, value).status_code == 400
    mundo['b'].estado = 'Inactivo'
    mundo['b'].save()
    assert select(client, mundo['b'].pk).status_code == 400
    response = client.post('/cuentas/delegacion/', {'delegacion': mundo['a'].pk, 'next': 'https://foreign.invalid'})
    assert response.status_code == 302 and response['Location'] == '/'


def test_selected_delegation_is_enforced_on_creating_records(client, global_user, mundo):
    client.force_login(global_user)
    assert select(client, mundo['b'].pk).status_code == 302
    url = reverse('gestion:crear', args=['atenciones'])
    data = {'delegacion': mundo['a'].pk, 'tipo': mundo['tipo_b'].pk,
            'subatencion': mundo['sub_b'].pk, 'solicitante_nombre': 'Delegación seleccionada',
            'solicitante_rut': '12345678-5', 'descripcion': 'Prueba', 'estado': 'Ingresada'}
    assert client.post(url, data).status_code == 302
    assert Atencion.objects.get(solicitante_nombre='Delegación seleccionada').delegacion_id == mundo['b'].pk


def test_coordinator_can_switch_scope_without_technical_or_account_privileges(client, coordinator, mundo):
    client.force_login(coordinator)
    assert select(client, mundo['b'].pk).status_code == 302
    listing = client.get(reverse('gestion:listado', args=['atenciones']))
    assert listing.status_code == 200
    assert list(listing.context['page_obj']) == [mundo['atn_b']]
    assert client.get(reverse('gestion:crear', args=['metas'])).status_code == 200
    assert client.get(reverse('cuentas:usuarios')).status_code == 403
    assert client.get(reverse('cuentas:roles')).status_code == 403
    assert client.get('/admin/').status_code in (302, 403)


def test_coordinator_can_record_attention_outside_profile_delegation_and_filter_it(client, mundo):
    client.force_login(mundo['users']['coordinador'])
    assert select(client, mundo['b'].pk).status_code == 302
    response = client.post(reverse('gestion:crear', args=['atenciones']), {
        'tipo': mundo['tipo_b'].pk, 'subatencion': mundo['sub_b'].pk,
        'solicitante_nombre': 'Atención comunal', 'solicitante_rut': '12345678-5',
        'descripcion': 'Prueba', 'estado': 'Ingresada',
    })
    assert response.status_code == 302
    listing = client.get(reverse('gestion:listado', args=['atenciones']), {'responsable': mundo['users']['coordinador'].pk})
    assert not listing.context['filter_form'].errors
    assert listing.context['page_obj'].paginator.count == 1


def test_operator_has_attention_access_without_catalog_or_meta_maintenance(client, mundo):
    operator = mundo['users']['editor_a']
    operator.groups.set([Group.objects.get_or_create(name='Operador / Funcionario')[0]])
    configure_groups()
    client.force_login(operator)
    assert client.get(reverse('gestion:crear', args=['atenciones'])).status_code == 200
    for module in ['metas', 'tipos', 'subatenciones', 'delegaciones']:
        assert client.get(reverse('gestion:crear', args=[module])).status_code == 403
    assert client.post(reverse('gestion:archivar', args=['atenciones', mundo['atn_a'].pk])).status_code == 403


@pytest.mark.parametrize('role', ['Coordinador', 'Superadministrador'])
def test_delegate_cannot_assign_global_role(client, mundo, role):
    client.force_login(mundo['users']['admin_a'])
    response = client.post(reverse('cuentas:usuario_crear'), {
        'username': 'forged_global', 'email': 'forged@example.test', 'rut': '11111111-1',
        'role': role, 'new_password': 'Global-test-key-921!', 'is_active': 'on',
    })
    assert response.status_code == 200
    assert response.context['form'].errors.get('role')
    assert not get_user_model().objects.filter(username='forged_global').exists()


def test_superadmin_can_assign_restored_coordinator_role(client, global_user, mundo):
    client.force_login(global_user)
    response = client.post(reverse('cuentas:usuario_crear'), {
        'username': 'new_coordinator', 'email': 'coord@example.test', 'rut': '11111111-1',
        'role': 'Coordinador', 'delegacion': mundo['a'].pk,
        'new_password': 'Coordinator-test-key-921!', 'is_active': 'on',
    })
    assert response.status_code == 302
    user = get_user_model().objects.get(username='new_coordinator')
    assert not user.is_superuser and not user.is_staff
    assert user.groups.filter(name='Coordinador').exists()


def test_superadmin_selected_scope_filters_managed_users_and_portal(client, global_user, mundo):
    client.force_login(global_user)
    assert select(client, mundo['b'].pk).status_code == 302
    response = client.get(reverse('cuentas:usuarios'))
    assert [u.username for u in response.context['usuarios']] == ['lector_b']
    assert client.get(reverse('gestion:portal')).context['page_obj'].paginator.count == 0


def test_superadmin_role_assignment_sets_real_flags_without_requiring_local_profile(client, global_user):
    client.force_login(global_user)
    response = client.post(reverse('cuentas:usuario_crear'), {
        'username': 'technical_account', 'email': 'technical@example.test', 'rut': '',
        'role': 'Superadministrador', 'new_password': 'Technical-test-key-921!', 'is_active': 'on',
    })
    assert response.status_code == 302
    user = get_user_model().objects.get(username='technical_account')
    assert user.is_superuser and user.is_staff and user.is_active
    assert user.check_password('Technical-test-key-921!')
    assert user.perfil.delegacion_id is None


def test_superadmin_group_name_alone_does_not_grant_global_scope(client, mundo):
    user = mundo['users']['lector_a']
    user.groups.add(Group.objects.get(name='Superadministrador'))
    client.force_login(user)
    assert select(client, mundo['b'].pk).status_code == 403
    assert client.get(reverse('cuentas:roles')).status_code == 403


def test_role_migration_merges_memberships_preserves_password_and_is_idempotent(mundo):
    from importlib import import_module
    from types import SimpleNamespace
    from django.apps import apps
    from django.db import connection
    migration = import_module('cuentas.migrations.0004_restore_municipal_roles')
    user = mundo['users']['editor_a']
    old = Group.objects.create(name='Editor')
    user.groups.set([old])
    original_password = user.password
    for _ in range(2):
        migration.forwards(apps, SimpleNamespace(connection=connection))
    user.refresh_from_db()
    assert user.password == original_password
    assert list(user.groups.values_list('name', flat=True)) == ['Operador / Funcionario']
    assert not Group.objects.filter(name__in=['Administrador', 'Editor', 'Lector']).exists()
    assert user.has_perm('gestion.add_atencion')
    assert not user.has_perm('gestion.add_itemmeta')
