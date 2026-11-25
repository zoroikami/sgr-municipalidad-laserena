"""Cambiar el correo exige controlar el buzón y no revela cuentas desde Mi perfil."""
import re
from urllib.parse import urlsplit
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client
from django.urls import reverse

from cuentas.forms import ProfileForm


pytestmark = pytest.mark.django_db


def datos(correo, **extra):
    return {'first_name': 'Camila', 'last_name': 'Rojas', 'email': correo, 'telefono': '912345678', **extra}


def solicitar(client, user, correo='nuevo@example.test'):
    client.force_login(user)
    response = client.post(reverse('cuentas:perfil'), datos(correo))
    assert response.status_code == 302
    assert mail.outbox[-1].to == [correo]
    enlace = re.search(r'https?://\S+', mail.outbox[-1].body).group()
    return response, urlsplit(enlace).path


def test_solicitud_tiene_la_misma_respuesta_y_envio_con_correo_libre_y_ocupado(client, mundo):
    user = mundo['users']['cliente_1']
    original = user.email
    correo = 'propuesto@example.test'
    client.force_login(user)
    respuestas = []
    for ocupado in (False, True):
        if ocupado:
            User.objects.filter(pk=mundo['users']['lector_b'].pk).update(email=correo)
        response = client.post(reverse('cuentas:perfil'), datos(correo), follow=True)
        respuestas.append((response.redirect_chain, [str(m) for m in get_messages(response.wsgi_request)]))
        user.refresh_from_db()
        assert user.email == original
        assert mail.outbox[-1].to == [correo]
    assert respuestas[0] == respuestas[1]
    assert len(mail.outbox) == 2
    assert any('Te enviamos un enlace a propuesto@example.test' in m for m in respuestas[0][1])


@pytest.mark.parametrize('ocupado', [False, True])
def test_otro_campo_invalido_no_permite_consultar_si_el_correo_existe(client, mundo, ocupado):
    user = mundo['users']['cliente_1']
    original = user.email
    correo = mundo['users']['lector_b'].email if ocupado else 'libre@example.test'
    client.force_login(user)
    response = client.post(reverse('cuentas:perfil'), datos(correo, telefono='invalido'))
    assert response.status_code == 200
    assert set(response.context['form'].errors) == {'telefono'}
    assert 'Ya existe una cuenta con este correo' not in response.content.decode()
    user.refresh_from_db()
    assert user.email == original
    assert not mail.outbox


def test_profile_form_save_no_cambia_el_correo_aunque_se_use_fuera_de_la_vista(mundo):
    user = mundo['users']['editor_a']
    original = user.email
    form = ProfileForm(datos('nuevo@example.test'), instance=user)
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.email == original
    assert user.first_name == 'Camila'


def test_get_no_cambia_correo_y_post_confirma_conservando_los_otros_datos(client, mundo):
    user = mundo['users']['editor_a']
    original = user.email
    _, enlace = solicitar(client, user)
    user.refresh_from_db()
    assert user.email == original
    assert user.first_name == 'Camila'
    assert user.perfil.telefono == '912345678'
    response = client.get(enlace)
    assert response.status_code == 200
    assert 'Confirmar cambio de correo' in response.content.decode()
    user.refresh_from_db()
    assert user.email == original
    response = client.post(enlace)
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.email == 'nuevo@example.test'
    assert user.first_name == 'Camila'


def test_confirmacion_exige_la_cuenta_destinataria_y_sesion(client, mundo):
    user = mundo['users']['editor_a']
    original = user.email
    _, enlace = solicitar(client, user)
    anonimo = Client()
    assert anonimo.get(enlace).status_code == 302
    assert anonimo.post(enlace).status_code == 302
    client.force_login(mundo['users']['lector_b'])
    assert client.get(enlace).status_code == 400
    assert client.post(enlace).status_code == 400
    user.refresh_from_db()
    assert user.email == original


def test_confirmacion_rechaza_token_vencido(client, mundo):
    user = mundo['users']['editor_a']
    original = user.email
    with patch('django.core.signing.time.time', return_value=1700000000):
        _, enlace = solicitar(client, user)
    with patch('django.core.signing.time.time', return_value=1700086401):
        assert client.get(enlace).status_code == 400
        assert client.post(enlace).status_code == 400
    user.refresh_from_db()
    assert user.email == original


def test_token_no_se_puede_reutilizar_despues_de_cambiar_el_correo(client, mundo):
    user = mundo['users']['editor_a']
    _, enlace = solicitar(client, user)
    assert client.post(enlace).status_code == 302
    assert client.get(enlace).status_code == 400
    assert client.post(enlace).status_code == 400
    user.refresh_from_db()
    assert user.email == 'nuevo@example.test'


def test_correo_ocupado_solo_se_rechaza_al_confirmar_desde_el_enlace(client, mundo):
    user = mundo['users']['cliente_1']
    original = user.email
    correo = mundo['users']['lector_b'].email.upper()
    _, enlace = solicitar(client, user, correo)
    assert client.get(enlace).status_code == 200
    response = client.post(enlace)
    assert response.status_code == 409
    assert 'correo ya está asociado a otra cuenta' in response.content.decode()
    user.refresh_from_db()
    assert user.email == original


def test_token_alterado_o_correo_actual_modificado_se_rechazan(client, mundo):
    user = mundo['users']['editor_a']
    _, enlace = solicitar(client, user)
    alterado = enlace[:-2] + ('A' if enlace[-2] != 'A' else 'B') + '/'
    assert client.post(alterado).status_code == 400
    User.objects.filter(pk=user.pk).update(email='cambiado@example.test')
    assert client.post(enlace).status_code == 400
    user.refresh_from_db()
    assert user.email == 'cambiado@example.test'


def test_confirmacion_requiere_csrf(client, mundo):
    user = mundo['users']['editor_a']
    original = user.email
    _, enlace = solicitar(client, user)
    protegido = Client(enforce_csrf_checks=True)
    protegido.force_login(user)
    assert protegido.get(enlace).status_code == 200
    assert protegido.post(enlace).status_code == 403
    user.refresh_from_db()
    assert user.email == original


def test_guardar_correo_sin_cambios_no_envia_confirmacion(client, mundo):
    user = mundo['users']['editor_a']
    client.force_login(user)
    response = client.post(reverse('cuentas:perfil'), datos(user.email))
    assert response.status_code == 302
    assert not mail.outbox


def test_correo_actual_con_dominio_en_mayusculas_se_puede_confirmar(client, mundo):
    user = mundo['users']['editor_a']
    user.email = 'editor@EXAMPLE.TEST'
    user.save(update_fields=['email'])
    _, enlace = solicitar(client, user)
    assert client.post(enlace).status_code == 302
    user.refresh_from_db()
    assert user.email == 'nuevo@example.test'


def test_guardar_perfil_no_sobrescribe_un_correo_cambiado_en_otra_sesion(mundo):
    user = mundo['users']['editor_a']
    form = ProfileForm(datos(user.email), instance=user)
    assert form.is_valid(), form.errors
    User.objects.filter(pk=user.pk).update(email='confirmado@example.test')
    form.save()
    user.refresh_from_db()
    assert user.email == 'confirmado@example.test'
