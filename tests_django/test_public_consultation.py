"""Anonymous access requires an emailed secret and must never expose personal fields."""
from copy import deepcopy
from datetime import timedelta
import re
from unittest.mock import patch
import uuid

import pytest
from django.core import mail
from django.core.cache import caches
from django.core.mail.backends.base import BaseEmailBackend
from django.urls import reverse
from django.utils import timezone
from smtplib import SMTPException

from gestion.models import Atencion

pytestmark = pytest.mark.django_db


class BrokenSMTP(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise SMTPException('SMTP no disponible')


@pytest.fixture(autouse=True)
def isolated_consultation_cache(settings):
    config = deepcopy(settings.CACHES)
    config['consulta_publica'] = {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0],
        'KEY_PREFIX': 'sgr-public-test-' + uuid.uuid4().hex,
        'OPTIONS': {'socket_connect_timeout': 1, 'socket_timeout': 1},
    }
    settings.CACHES = config


def payload(mundo, **extra):
    return {'solicitante_nombre': 'Vecina sin cuenta', 'solicitante_rut': '12345678-5',
            'solicitante_email': 'vecina@example.test', 'tipo': mundo['tipo_a'].pk,
            'subatencion': mundo['sub_a'].pk, 'descripcion': 'Antecedentes privados',
            'estado': 'Ingresada', **extra}


def emailed_code():
    return re.search(r'Código privado: ([A-Z2-9-]+)', mail.outbox[-1].body).group(1)


def give_access(record, address='vecina@example.test'):
    from gestion.consulta import send_consultation_access
    record.solicitante_email = address
    record.save(update_fields=['solicitante_email'])
    send_consultation_access(record.pk, 'http://testserver/consulta/')
    return emailed_code()


def test_anonymous_home_offers_consultation_before_employee_login(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Consultar mi atención' in response.content.decode()
    assert reverse('cuentas:login') in response.content.decode()


def test_public_lookup_does_not_accept_secrets_from_url_query(client, mundo):
    response = client.get('/consulta/', {'folio': mundo['atn_a'].folio, 'codigo': 'DO-NOT-ECHO-ME'})
    assert response.status_code == 200
    assert 'DO-NOT-ECHO-ME' not in response.content.decode()
    assert response.context['result'] is None


def test_creating_attention_emails_access_only_after_commit(client, mundo, django_capture_on_commit_callbacks):
    client.force_login(mundo['users']['editor_a'])
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse('gestion:crear', args=['atenciones']), payload(mundo))
        assert not mail.outbox
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    record = Atencion.objects.get(solicitante_nombre='Vecina sin cuenta')
    code = emailed_code()
    assert mail.outbox[0].to == ['vecina@example.test']
    assert record.folio in mail.outbox[0].body
    assert 'http://testserver/consulta/' in mail.outbox[0].body
    assert 'Antecedentes privados' not in mail.outbox[0].body
    assert '12345678' not in mail.outbox[0].body
    assert record.consulta_codigo_hash and code.replace('-', '') not in record.consulta_codigo_hash
    assert record.consulta_enviado_at is not None


def test_existing_record_without_email_does_not_send_mail(client, mundo, django_capture_on_commit_callbacks):
    client.force_login(mundo['users']['editor_a'])
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse('gestion:crear', args=['atenciones']), payload(mundo, solicitante_email=''))
    assert response.status_code == 302
    assert not mail.outbox


def test_lookup_discloses_only_minimal_status_to_secret_holder(client, mundo):
    record = mundo['atn_a']
    code = give_access(record)
    response = client.post('/consulta/', {'folio': record.folio, 'codigo': code})
    assert response.status_code == 200
    assert set(response.context['result']) == {'folio', 'estado', 'created_at', 'updated_at', 'delegacion'}
    body = response.content.decode()
    for private in [record.solicitante_nombre, record.solicitante_rut, record.descripcion,
                    'vecina@example.test', code, record.cliente.username]:
        assert private not in body
    assert 'no-store' in response['Cache-Control']
    assert response['Referrer-Policy'] == 'same-origin'


@pytest.mark.parametrize('scenario', ['wrong', 'unknown', 'expired', 'archived', 'other_record', 'no_code'])
def test_invalid_lookups_have_same_neutral_response(client, mundo, scenario):
    record = mundo['atn_a']
    code = give_access(record)
    folio = record.folio
    if scenario == 'wrong':
        code = 'AAAA-BBBB-CCCC-DDDD-EEEE'
    elif scenario == 'unknown':
        folio = 'ATN-2026-999999'
    elif scenario == 'expired':
        Atencion.objects.filter(pk=record.pk).update(consulta_enviado_at=timezone.now() - timedelta(days=31))
    elif scenario == 'archived':
        Atencion.all_objects.filter(pk=record.pk).update(deleted_at=timezone.now())
    else:
        folio = mundo['atn_2'].folio
        if scenario == 'other_record':
            give_access(mundo['atn_2'], 'otra@example.test')
    response = client.post('/consulta/', {'folio': folio, 'codigo': code})
    assert response.status_code == 200
    assert response.context['result'] is None
    assert response.context['lookup_error'] == 'No pudimos consultar la atención. Revisa el folio y el código privado. Si necesitas uno nuevo, comunícate con tu delegación.'


def test_renewal_invalidates_previous_code_and_failed_smtp_preserves_current_access(mundo, settings):
    from gestion.consulta import DeliveryError, lookup_consultation, send_consultation_access
    record = mundo['atn_a']
    previous = give_access(record)
    send_consultation_access(record.pk, 'http://testserver/consulta/')
    current = emailed_code()
    assert current != previous
    assert lookup_consultation(record.folio, previous) is None
    assert lookup_consultation(record.folio, current)['folio'] == record.folio
    settings.EMAIL_BACKEND = 'tests_django.test_public_consultation.BrokenSMTP'
    with pytest.raises(DeliveryError):
        send_consultation_access(record.pk, 'http://testserver/consulta/')
    assert lookup_consultation(record.folio, current)['folio'] == record.folio


def test_changing_email_revokes_previous_recipient_and_sends_new_code(client, mundo, django_capture_on_commit_callbacks):
    from gestion.consulta import lookup_consultation
    record = mundo['atn_a']
    previous = give_access(record)
    client.force_login(mundo['users']['editor_a'])
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse('gestion:editar', args=['atenciones', record.pk]),
            payload(mundo, solicitante_email='nuevo@example.test'))
    assert response.status_code == 302
    assert mail.outbox[-1].to == ['nuevo@example.test']
    assert lookup_consultation(record.folio, previous) is None
    assert lookup_consultation(record.folio, emailed_code()) is not None


@pytest.mark.django_db(transaction=True)
def test_smtp_failure_keeps_attention_and_reports_delivery_failure(client, mundo, settings):
    settings.EMAIL_BACKEND = 'tests_django.test_public_consultation.BrokenSMTP'
    client.force_login(mundo['users']['editor_a'])
    response = client.post(reverse('gestion:crear', args=['atenciones']), payload(mundo))
    assert response.status_code == 302
    record = Atencion.objects.get(solicitante_nombre='Vecina sin cuenta')
    assert not record.consulta_codigo_hash
    page = client.get(response['Location'])
    assert 'no pudimos enviar el correo' in page.content.decode()


def test_resend_requires_write_permission_and_authorized_delegation(client, mundo, django_capture_on_commit_callbacks):
    record = mundo['atn_a']
    give_access(record)
    mail.outbox.clear()
    url = f'/gestion/atenciones/{record.pk}/correo-consulta/'
    for alias in ['cliente_1', 'lector_a', 'lector_b']:
        client.force_login(mundo['users'][alias])
        assert client.post(url).status_code == 403
    client.force_login(mundo['users']['admin_a'])
    assert client.post(f'/gestion/atenciones/{mundo["atn_b"].pk}/correo-consulta/').status_code == 404
    assert client.get(url).status_code == 405
    assert not mail.outbox
    with django_capture_on_commit_callbacks(execute=True):
        assert client.post(url).status_code == 302
    assert len(mail.outbox) == 1


def test_lookup_rate_limit_uses_ip_and_fails_closed_when_redis_is_unavailable(client):
    data = {'folio': 'ATN-2026-9999', 'codigo': 'AAAA-BBBB-CCCC-DDDD-EEEE'}
    for _ in range(30):
        assert client.post('/consulta/', data, HTTP_X_REAL_IP=str(uuid.uuid4())).status_code == 200
    limited = client.post('/consulta/', data)
    assert limited.status_code == 429 and limited['Retry-After'] == '900'
    assert client.post('/consulta/', data, REMOTE_ADDR='192.0.2.40').status_code == 200
    from redis.exceptions import ConnectionError
    with patch.object(caches['consulta_publica'], 'add', side_effect=ConnectionError):
        unavailable = client.post('/consulta/', data)
    assert unavailable.status_code == 503


def test_lookup_csrf_and_http_method_restrictions(client):
    from django.test import Client
    assert Client(enforce_csrf_checks=True).post('/consulta/', {'folio': 'ATN-2026-9999', 'codigo': 'secret'}).status_code == 403
    assert client.put('/consulta/').status_code == 405
