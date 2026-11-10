"""Home previews and RUT presentation must preserve scope and canonical storage."""
from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission, User
from django.urls import reverse
from django.utils import timezone

from gestion.models import Atencion

pytestmark = pytest.mark.django_db


def test_home_preview_shows_three_latest_active_records_from_own_delegation(client, mundo):
    client.force_login(mundo['users']['admin_a'])
    for number in range(5):
        Atencion.objects.create(delegacion=mundo['a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
            responsable=mundo['users']['editor_a'], solicitante_nombre=f'Reciente {number}',
            solicitante_rut='12345678-5', descripcion='Solicitud de prueba',
            created_at=timezone.now() + timedelta(minutes=number + 1))
    Atencion.all_objects.filter(pk=mundo['atn_b'].pk).update(
        solicitante_nombre='Nombre de otra delegación', created_at=timezone.now() + timedelta(days=1))
    Atencion.all_objects.create(delegacion=mundo['a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
        responsable=mundo['users']['editor_a'], solicitante_nombre='Nombre archivado',
        solicitante_rut='12345678-5', descripcion='Archivada', deleted_at=timezone.now())
    response = client.get(reverse('gestion:inicio'))
    section = next(section for section in response.context['stats'] if section['modulo'] == 'atenciones')
    assert section['total'] == 7
    assert [row['nombre'] for row in section['preview']] == ['Reciente 4', 'Reciente 3', 'Reciente 2']
    assert 'Nombre de otra delegación' not in response.content.decode()
    assert 'Nombre archivado' not in response.content.decode()


def test_home_previews_omit_modules_without_permission(client, mundo):
    reader = mundo['users']['lector_a']
    reader.groups.clear()
    reader.user_permissions.add(Permission.objects.get(codename='view_itemmeta'))
    client.force_login(reader)
    response = client.get(reverse('gestion:inicio'))
    assert [section['modulo'] for section in response.context['stats']] == ['metas']


def test_profile_formats_rut_for_display_without_changing_database(client, mundo):
    client.force_login(mundo['users']['admin_a'])
    response = client.get(reverse('cuentas:perfil'))
    assert '11.000.001-4' in response.content.decode()
    assert mundo['users']['admin_a'].perfil.rut == '11000001-4'


def test_attention_formats_saved_rut_and_guides_unpunctuated_input(client, mundo):
    client.force_login(mundo['users']['admin_a'])
    form = client.get(reverse('gestion:crear', args=['atenciones'])).context['form']
    assert 'sin puntos' in form.fields['solicitante_rut'].help_text
    assert 'con guion' in form.fields['solicitante_rut'].help_text
    detail = client.get(reverse('gestion:detalle', args=['atenciones', mundo['atn_a'].pk]))
    assert '12.345.678-5' in detail.content.decode()
    mundo['atn_a'].refresh_from_db()
    assert mundo['atn_a'].solicitante_rut == '12345678-5'
    account_form = client.get(reverse('cuentas:usuario_crear')).context['form']
    assert 'sin puntos' in account_form.fields['rut'].help_text
    assert 'con guion' in account_form.fields['rut'].help_text


def test_saved_user_rut_is_formatted_in_user_list_and_canonical_in_storage(client, mundo):
    client.force_login(mundo['users']['admin_a'])
    response = client.post(reverse('cuentas:usuario_crear'), {
        'username': 'formato_rut', 'first_name': 'Prueba', 'last_name': 'Formato',
        'email': 'formato@example.test', 'rut': '11111111-1', 'role': 'Consultor',
        'new_password': 'Comprobacion#2026-58', 'is_active': 'on',
    })
    assert response.status_code == 302
    assert User.objects.get(username='formato_rut').perfil.rut == '11111111-1'
    assert '11.111.111-1' in client.get(reverse('cuentas:usuarios')).content.decode()
