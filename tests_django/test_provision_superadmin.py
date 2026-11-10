import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError

pytestmark = pytest.mark.django_db


def test_provision_creates_global_account_without_password_reset(tmp_path):
    path = tmp_path / 'global.json'
    output = StringIO()
    call_command('provision_superadmin', credentials_file=str(path), stdout=output)
    account = json.loads(path.read_text())[0]
    user = get_user_model().objects.get(username='superadmin')
    assert user.is_superuser and user.is_staff and user.is_active
    assert user.perfil.delegacion_id is None
    assert user.check_password(account['password'])
    assert account['password'] not in output.getvalue()
    original_hash = user.password
    call_command('provision_superadmin', credentials_file=str(path), stdout=output)
    user.refresh_from_db()
    assert user.password == original_hash
    assert json.loads(path.read_text())[0] == account


def test_provision_never_elevates_an_existing_account(tmp_path):
    user = get_user_model().objects.create_user('admin_a', password='PruebaPrivada2026!')
    with pytest.raises(CommandError):
        call_command('provision_superadmin', username='admin_a', credentials_file=str(tmp_path / 'global.json'))
    user.refresh_from_db()
    assert not user.is_superuser and not user.is_staff
