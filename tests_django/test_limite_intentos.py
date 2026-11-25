"""Límite de intentos de autenticación (hallazgo de seguridad 1) y recuperación sin oráculo de tiempo (hallazgo 2)."""
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.cache import caches
from django.urls import reverse

from cuentas import intentos

pytestmark = pytest.mark.django_db
CLAVE = 'Ensayo#Privado2026'


def ingresar(client, usuario, clave, ip='203.0.113.7'):
    return client.post(reverse('cuentas:login'), {'username': usuario, 'password': clave}, REMOTE_ADDR=ip)


def test_cinco_fallos_bloquean_la_cuenta_tambien_por_su_correo(client, mundo):
    for _ in range(intentos.LIMITES['login-cuenta']):
        assert ingresar(client, 'admin_a', 'clave-equivocada').status_code == 200
    bloqueado = ingresar(client, 'admin_a', CLAVE)
    assert bloqueado.status_code == 429 and bloqueado['Retry-After'] == str(intentos.VENTANA)
    assert 'demasiados intentos' in bloqueado.content.decode()
    # El correo de la misma cuenta comparte contador: el alias no reinicia los intentos.
    assert ingresar(client, 'ADMIN_A@example.test', CLAVE, ip='198.51.100.9').status_code == 429
    assert '_auth_user_id' not in client.session
    # Otra cuenta desde otra IP no se ve afectada.
    assert ingresar(client, 'editor_a', CLAVE, ip='198.51.100.10').status_code == 302


def test_ingreso_correcto_reinicia_el_contador_de_la_cuenta(client, mundo):
    for _ in range(intentos.LIMITES['login-cuenta'] - 1):
        ingresar(client, 'editor_a', 'clave-equivocada')
    assert ingresar(client, 'editor_a', CLAVE).status_code == 302
    client.post(reverse('cuentas:logout'))
    for _ in range(intentos.LIMITES['login-cuenta'] - 1):
        ingresar(client, 'editor_a', 'clave-equivocada')
    assert ingresar(client, 'editor_a', CLAVE).status_code == 302


def test_una_ip_que_prueba_muchas_cuentas_queda_bloqueada(client, mundo):
    for numero in range(intentos.LIMITES['login-ip']):
        ingresar(client, f'cuenta-inventada-{numero}', 'clave-equivocada', ip='192.0.2.50')
    assert ingresar(client, 'editor_a', CLAVE, ip='192.0.2.50').status_code == 429
    assert ingresar(client, 'editor_a', CLAVE, ip='192.0.2.51').status_code == 302


def test_cambiar_clave_limita_la_contrasena_actual(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    datos = {'old_password': 'no-es-la-actual', 'new_password1': 'Otra#Clave2026x', 'new_password2': 'Otra#Clave2026x'}
    for _ in range(intentos.LIMITES['clave-actual']):
        assert 'old_password' in client.post(reverse('cuentas:password_change'), datos).context['form'].errors
    respuesta = client.post(reverse('cuentas:password_change'), {**datos, 'old_password': CLAVE})
    assert respuesta.status_code == 200
    assert 'demasiados intentos' in str(respuesta.context['form'].errors['old_password'])


def test_recuperacion_responde_igual_y_limita_por_ip(client, mundo):
    destino = reverse('cuentas:password_reset_done')
    for _ in range(intentos.LIMITES['recuperacion-ip']):
        assert client.post(reverse('cuentas:password_reset'), {'email': 'editor_a@example.test'},
                           REMOTE_ADDR='203.0.113.20').url == destino
    enviados = len(mail.outbox)
    assert enviados == intentos.LIMITES['recuperacion-ip']
    # Sobre el límite la respuesta es la misma, pero no se envía otro correo.
    assert client.post(reverse('cuentas:password_reset'), {'email': 'editor_a@example.test'},
                       REMOTE_ADDR='203.0.113.20').url == destino
    assert len(mail.outbox) == enviados


def test_recuperacion_envia_fuera_de_la_peticion_con_smtp(mundo, settings):
    from cuentas.forms import MunicipalPasswordResetForm
    settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    form = MunicipalPasswordResetForm({'email': 'editor_a@example.test'})
    assert form.is_valid()
    with patch('cuentas.forms.threading.Thread') as hilo:
        form.save(domain_override='sgr.test', request=None)
    hilo.assert_called_once()
    assert hilo.call_args.kwargs['daemon'] is True


def test_si_redis_no_responde_el_ingreso_sigue_funcionando(client, mundo):
    with patch.object(caches['autenticacion'], 'get', side_effect=ConnectionError), \
         patch.object(caches['autenticacion'], 'add', side_effect=ConnectionError):
        assert ingresar(client, 'editor_a', CLAVE).status_code == 302


def test_consola_tecnica_usa_el_login_municipal(client):
    respuesta = client.get('/admin/login/?next=/admin/')
    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse('cuentas:login')) and 'next=/admin/' in respuesta.url


def test_solicitudes_de_cambio_de_correo_tienen_limite_por_cuenta(client, mundo):
    editor = mundo['users']['editor_a']
    client.force_login(editor)
    for numero in range(intentos.LIMITES['cambio-correo'] + 1):
        respuesta = client.post(reverse('cuentas:perfil'), {'first_name': 'Ana', 'last_name': 'Rojas',
                                                            'email': f'nuevo{numero}@example.test'}, follow=True)
        assert 'Te enviamos un enlace' in respuesta.content.decode()
    # El mensaje es el mismo, pero sobre el límite ya no se envían más enlaces.
    assert len(mail.outbox) == intentos.LIMITES['cambio-correo']
    editor.refresh_from_db()
    assert editor.email == 'editor_a@example.test'
