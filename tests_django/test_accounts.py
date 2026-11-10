"""Account boundaries: scope, privilege protection, credentials and private images."""
from io import BytesIO
import re

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from django.core.mail.backends.base import BaseEmailBackend
from smtplib import SMTPException


class UnavailableMailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise SMTPException('Fallo SMTP controlado de prueba')


@pytest.fixture
def accounts(db, tmp_path, settings):
    from cuentas.models import Perfil
    from gestion.models import Delegacion
    from cuentas.roles import configure_groups

    settings.MEDIA_ROOT = tmp_path
    configure_groups()
    a = Delegacion.objects.create(codigo='DEL01', nombre='Centro', direccion='Centro', comuna='La Serena')
    b = Delegacion.objects.create(codigo='DEL02', nombre='Las Compañías', direccion='Norte', comuna='La Serena')
    result = {}
    for name, role, scope, rut in [
        ('admin', 'Administrador', a, '12345678-5'),
        ('editor', 'Editor', a, '11111111-1'),
        ('other', 'Lector', b, '22222222-2'),
        ('cliente', 'Cliente', a, '33333333-3'),
    ]:
        user = User.objects.create_user(name, f'{name}@example.test', 'Valid-test-key-927!')
        user.groups.add(Group.objects.get_or_create(name=role)[0])
        Perfil.objects.create(user=user, delegacion=scope, rut=rut)
        result[name] = user
    result.update(a=a, b=b)
    return result


def photo(fmt='PNG'):
    output = BytesIO()
    Image.new('RGB', (80, 60), 'red').save(output, fmt)
    return SimpleUploadedFile('test.' + fmt.lower(), output.getvalue(), content_type='image/' + fmt.lower())


@pytest.mark.django_db
def test_login_accepts_email_and_logout_requires_post(client, accounts):
    response = client.post(reverse('cuentas:login'), {'username': 'ADMIN@example.test', 'password': 'Valid-test-key-927!'})
    assert response.status_code == 302
    assert int(client.session['_auth_user_id']) == accounts['admin'].pk
    assert client.get(reverse('cuentas:logout')).status_code == 405
    assert client.post(reverse('cuentas:logout')).status_code == 302
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_reset_remains_neutral_when_smtp_is_unavailable(client, accounts, settings):
    settings.EMAIL_BACKEND = 'tests_django.test_accounts.UnavailableMailBackend'
    client.raise_request_exception = False
    known = client.post(reverse('cuentas:password_reset'), {'email': 'editor@example.test'})
    unknown = client.post(reverse('cuentas:password_reset'), {'email': 'unknown@example.test'})
    assert known.status_code == unknown.status_code == 302
    assert known['Location'] == unknown['Location']


@pytest.mark.django_db
def test_own_profile_ignores_protected_fields(client, accounts):
    client.force_login(accounts['editor'])
    response = client.post(reverse('cuentas:perfil'), {
        'first_name': 'Camila', 'last_name': 'Rojas', 'email': 'camila@example.test',
        'is_superuser': '1', 'is_staff': '1', 'groups': accounts['admin'].groups.first().pk,
        'delegacion': accounts['b'].pk, 'rut': '22222222-2', 'user': accounts['other'].pk,
    })
    assert response.status_code == 302
    user = User.objects.get(pk=accounts['editor'].pk)
    assert user.first_name == 'Camila'
    assert not user.is_superuser and not user.is_staff
    assert user.perfil.delegacion_id == accounts['a'].pk
    assert list(user.groups.values_list('name', flat=True)) == ['Editor']


@pytest.mark.django_db
def test_profile_rejects_invalid_large_and_non_jpeg_png_uploads(client, accounts):
    client.force_login(accounts['editor'])
    data = {'first_name': 'Camila', 'last_name': '', 'email': 'camila@example.test'}
    for upload in [SimpleUploadedFile('bad.png', b'not an image', 'image/png'),
                   SimpleUploadedFile('large.png', b'x' * (2 * 1024 * 1024 + 1), 'image/png'), photo('GIF')]:
        response = client.post(reverse('cuentas:perfil'), {**data, 'foto': upload})
        assert response.status_code == 200
        assert response.context['form'].errors.get('foto')
    assert not User.objects.get(pk=accounts['editor'].pk).perfil.foto


@pytest.mark.django_db
def test_photo_only_owner_or_technical_superuser(client, accounts):
    client.force_login(accounts['editor'])
    response = client.post(reverse('cuentas:perfil'), {'first_name': '', 'last_name': '', 'email': 'editor@example.test', 'foto': photo()})
    assert response.status_code == 302
    url = reverse('cuentas:foto', args=[accounts['editor'].pk])
    response = client.get(url)
    assert response.status_code == 200
    assert response['Cache-Control'] == 'private, no-store'
    assert b''.join(response.streaming_content).startswith(b'\x89PNG')
    client.force_login(accounts['admin'])
    assert client.get(url).status_code == 404
    admin = accounts['admin']
    admin.is_superuser = True
    admin.save()
    response = client.get(url)
    assert response.status_code == 200
    assert b''.join(response.streaming_content).startswith(b'\x89PNG')


@pytest.mark.django_db
def test_admin_cannot_manage_other_scope_or_technical_accounts(client, accounts):
    client.force_login(accounts['admin'])
    assert client.get(reverse('cuentas:usuario_editar', args=[accounts['other'].pk])).status_code == 404
    technical = accounts['editor']
    technical.is_staff = True
    technical.save()
    assert client.get(reverse('cuentas:usuario_editar', args=[technical.pk])).status_code == 404
    client.force_login(accounts['cliente'])
    assert client.get(reverse('cuentas:usuarios')).status_code == 403
    assert client.get(reverse('cuentas:roles')).status_code == 403


@pytest.mark.django_db
def test_admin_role_choices_reject_global_privileges(client, accounts):
    client.force_login(accounts['admin'])
    response = client.post(reverse('cuentas:usuario_editar', args=[accounts['editor'].pk]), {
        'username': 'editor', 'first_name': '', 'last_name': '', 'email': 'editor@example.test',
        'rut': '11111111-1', 'role': 'Superusuario', 'is_superuser': '1', 'is_staff': '1',
        'delegacion': accounts['b'].pk, 'is_active': 'on',
    })
    assert response.status_code == 200
    assert response.context['form'].errors.get('role')
    user = User.objects.get(pk=accounts['editor'].pk)
    assert not user.is_superuser and not user.is_staff
    assert user.perfil.delegacion_id == accounts['a'].pk


@pytest.mark.django_db
def test_password_change_requires_current_password(client, accounts):
    client.force_login(accounts['editor'])
    response = client.post(reverse('cuentas:password_change'), {
        'old_password': 'wrong', 'new_password1': 'New-valid-key-972!', 'new_password2': 'New-valid-key-972!',
    })
    assert response.status_code == 200
    assert User.objects.get(pk=accounts['editor'].pk).check_password('Valid-test-key-927!')


@pytest.mark.django_db
def test_reset_neutral_response_and_token_single_use(client, accounts):
    done = reverse('cuentas:password_reset_done')
    assert client.post(reverse('cuentas:password_reset'), {'email': 'unknown@example.test'}).url == done
    assert len(mail.outbox) == 0
    assert client.post(reverse('cuentas:password_reset'), {'email': 'editor@example.test'}).url == done
    assert len(mail.outbox) == 1
    reset_path = re.search(r'https?://[^/]+(/\S+)', mail.outbox[0].body).group(1)
    response = client.get(reset_path)
    assert response.status_code == 302
    set_path = response.url
    response = client.post(set_path, {'new_password1': 'New-valid-key-972!', 'new_password2': 'New-valid-key-972!'})
    assert response.url == reverse('cuentas:password_reset_complete')
    assert User.objects.get(pk=accounts['editor'].pk).check_password('New-valid-key-972!')
    response = client.get(reset_path)
    assert response.status_code == 200
    assert not response.context['validlink']


@pytest.mark.django_db
def test_unknown_login_never_maps_to_a_real_sentinel_user(client, accounts):
    User.objects.create_user('__sgr_unknown_identity__', password='Valid-test-key-927!')
    response = client.post(reverse('cuentas:login'), {'username': 'no-such-user', 'password': 'Valid-test-key-927!'})
    assert response.status_code == 200
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_duplicate_profile_email_is_rejected(client, accounts):
    client.force_login(accounts['editor'])
    response = client.post(reverse('cuentas:perfil'), {'first_name': '', 'last_name': '', 'email': 'ADMIN@example.test'})
    assert response.status_code == 200
    assert response.context['form'].errors.get('email')
    assert User.objects.get(pk=accounts['editor'].pk).email == 'editor@example.test'


@pytest.mark.django_db
def test_admin_valid_edit_ignores_forged_scope_and_privileges(client, accounts):
    client.force_login(accounts['admin'])
    response = client.post(reverse('cuentas:usuario_editar', args=[accounts['editor'].pk]), {
        'username': 'editor', 'first_name': 'Camila', 'last_name': '', 'email': 'editor@example.test',
        'rut': '11.111.111-1', 'role': 'Lector', 'is_active': 'on',
        'delegacion': accounts['b'].pk, 'is_superuser': '1', 'is_staff': '1',
    })
    assert response.status_code == 302
    user = User.objects.get(pk=accounts['editor'].pk)
    assert not user.is_superuser and not user.is_staff
    assert user.perfil.delegacion_id == accounts['a'].pk
    assert user.perfil.rut == '11111111-1'
    assert list(user.groups.values_list('name', flat=True)) == ['Lector']


@pytest.mark.django_db
def test_standard_role_permissions_are_idempotent_and_scoped_to_business(accounts):
    from cuentas.roles import configure_groups
    configure_groups()
    configure_groups()
    assert Group.objects.filter(name__in=['Administrador', 'Editor', 'Lector', 'Cliente']).count() == 4
    assert accounts['admin'].has_perm('gestion.delete_atencion')
    assert accounts['editor'].has_perm('gestion.change_atencion')
    assert not accounts['editor'].has_perm('gestion.delete_atencion')
    assert not accounts['other'].has_perm('gestion.add_atencion')
    assert not accounts['cliente'].has_perm('gestion.view_atencion')
    assert not accounts['admin'].has_perm('auth.change_user')


@pytest.mark.django_db
def test_form_rejects_truncated_image_after_header_validation(accounts):
    from cuentas.forms import ProfileForm
    upload = photo('JPEG')
    damaged = SimpleUploadedFile('truncated.jpg', upload.read()[:-30], 'image/jpeg')
    form = ProfileForm({'first_name': '', 'last_name': '', 'email': 'editor@example.test'}, {'foto': damaged}, instance=accounts['editor'])
    assert not form.is_valid()
    assert form.errors.get('foto')


@pytest.mark.django_db
def test_admin_creation_validates_password_and_forces_own_delegation(client, accounts):
    client.force_login(accounts['admin'])
    data = {
        'username': 'new-editor', 'first_name': 'Camila', 'last_name': 'Rojas',
        'email': 'new-editor@example.test', 'rut': '44.444.444-4', 'role': 'Editor',
        'is_active': 'on', 'delegacion': accounts['b'].pk, 'is_staff': '1', 'is_superuser': '1',
        'new_password': '123',
    }
    response = client.post(reverse('cuentas:usuario_crear'), data)
    assert response.status_code == 200
    assert response.context['form'].errors.get('new_password')
    assert not User.objects.filter(username='new-editor').exists()
    response = client.post(reverse('cuentas:usuario_crear'), {**data, 'new_password': 'Another-valid-key-379!'})
    assert response.status_code == 302
    user = User.objects.get(username='new-editor')
    assert user.check_password('Another-valid-key-379!')
    assert user.perfil.delegacion_id == accounts['a'].pk
    assert not user.is_staff and not user.is_superuser
    assert list(user.groups.values_list('name', flat=True)) == ['Editor']


@pytest.mark.django_db
def test_ordinary_admin_cannot_change_global_role_permissions(client, accounts):
    client.force_login(accounts['admin'])
    group = accounts['editor'].groups.first()
    assert client.post(reverse('cuentas:roles'), {'group': group.pk, 'permissions': []}).status_code == 403


@pytest.mark.django_db
def test_private_photo_is_not_publicly_addressable(client, accounts):
    assert client.get(reverse('cuentas:foto', args=[accounts['editor'].pk])).status_code == 302
    from cuentas.models import Perfil
    profile = Perfil.objects.get(user=accounts['editor'])
    profile.foto = photo()
    profile.save()
    assert profile.foto.name.startswith('perfiles/')
    assert 'test.png' not in profile.foto.name
    with pytest.raises(ValueError):
        _ = profile.foto.url


@pytest.mark.django_db
def test_role_editor_preloads_and_preserves_selected_group(client, accounts):
    superuser = User.objects.create_superuser('roles_support', 'support@example.test', 'Valid-test-key-927!')
    client.force_login(superuser)
    group = Group.objects.get(name='Editor')
    permissions = list(group.permissions.values_list('pk', flat=True))
    url = reverse('cuentas:roles')
    response = client.get(url, {'grupo': group.pk})
    assert response.status_code == 200
    assert response.context['active_group'] == group
    assert set(response.context['form']['permissions'].value()) == set(permissions)
    response = client.post(url, {'group': group.pk, 'permissions': permissions})
    assert response.status_code == 302
    assert response['Location'] == f'{url}?grupo={group.pk}'
    assert set(group.permissions.values_list('pk', flat=True)) == set(permissions)
    response = client.post(url, {'group': group.pk, 'permissions': []})
    assert response.status_code == 302
    assert not group.permissions.exists()
