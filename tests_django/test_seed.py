from io import StringIO
import json
import os

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from gestion.models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion

pytestmark = pytest.mark.django_db


def test_seed_has_required_distribution_six_private_accounts_and_is_idempotent(tmp_path):
    path = tmp_path / 'cuentas.json'
    output = StringIO()
    call_command('seed_demo', credentials_file=str(path), stdout=output)
    assert [model.objects.count() for model in [Delegacion, ItemMeta, TipoAtencion, SubAtencion, Atencion]] == [6, 360, 30, 90, 1800]
    assert get_user_model().objects.filter(is_superuser=True).count() == 0
    credentials = json.loads(path.read_text())
    assert len(credentials) == 6
    # Windows reports synthetic mode bits, not POSIX owner/group permissions.
    if os.name == 'posix':
        assert os.stat(path).st_mode & 0o777 == 0o600
    before = get_user_model().objects.get(username='editor_a').password
    for account in credentials:
        user = get_user_model().objects.get(username=account['usuario'])
        assert user.check_password(account['password'])
        assert account['password'] not in output.getvalue()
    for username in ['cliente_1', 'cliente_2']:
        assert Atencion.objects.filter(cliente__username=username).count() == 30
    target = ItemMeta.objects.first()
    target.nombre = 'Edición conservada'
    target.save()
    call_command('seed_demo', credentials_file=str(path), stdout=output)
    assert Atencion.objects.count() == 1800
    assert ItemMeta.objects.count() == 360
    assert get_user_model().objects.get(username='editor_a').password == before
    assert ItemMeta.objects.get(pk=target.pk).nombre == 'Edición conservada'


def test_update_demo_names_preserves_password_roles_and_edited_records(tmp_path):
    path = tmp_path / 'demo.json'
    call_command('seed_demo', credentials_file=str(path))
    user = get_user_model().objects.get(username='cliente_1')
    user.first_name, user.last_name = 'Nombre anterior', ''
    user.save()
    records = Atencion.objects.filter(cliente=user)
    records.update(solicitante_nombre='Nombre anterior')
    edited = records.first()
    edited.solicitante_nombre = 'Nombre editado manualmente'
    edited.save()
    original_hash, groups = user.password, list(user.groups.values_list('pk', flat=True))
    call_command('seed_demo', credentials_file=str(path), update_names=True)
    user.refresh_from_db()
    edited.refresh_from_db()
    assert user.get_full_name() == 'Javier Ahumada'
    assert user.password == original_hash and not user.is_superuser
    assert list(user.groups.values_list('pk', flat=True)) == groups
    assert edited.solicitante_nombre == 'Nombre editado manualmente'
    assert records.filter(solicitante_nombre='Javier Ahumada').count() == 29
