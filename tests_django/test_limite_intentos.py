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


def test_cinco_fallos_pausan_la_cuenta_tambien_por_su_correo(client, mundo):
    for numero in range(intentos.LIMITES['login-cuenta']):
        assert ingresar(client, 'admin_a', 'clave-equivocada', ip=f'203.0.113.{numero + 1}').status_code == 200
    # Con la clave correcta tampoco entra, y la respuesta es la de una clave errada (no revela la pausa).
    pausado = ingresar(client, 'admin_a', CLAVE, ip='198.51.100.8')
    assert pausado.status_code == 200 and 'Usuario o contraseña incorrectos' in pausado.content.decode()
    # El correo de la misma cuenta comparte contador: el alias no reinicia los intentos.
    assert ingresar(client, 'ADMIN_A@example.test', CLAVE, ip='198.51.100.9').status_code == 200
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
    bloqueada = ingresar(client, 'editor_a', CLAVE, ip='192.0.2.50')
    assert bloqueada.status_code == 429 and bloqueada['Retry-After'] == str(intentos.VENTANA)
    assert 'demasiados intentos' in bloqueada.content.decode()
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
    with patch('cuentas.intentos._redis', side_effect=ConnectionError):
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


def test_envio_sin_contrasena_no_reinicia_el_contador(client, mundo):
    for _ in range(intentos.LIMITES['login-cuenta'] - 1):
        ingresar(client, 'admin_a', 'clave-equivocada')
    client.post(reverse('cuentas:login'), {'username': 'admin_a', 'password': ''}, REMOTE_ADDR='198.51.100.30')
    client.post(reverse('cuentas:login'), {'username': 'admin_a'}, REMOTE_ADDR='198.51.100.31')
    ingresar(client, 'admin_a', 'clave-equivocada', ip='198.51.100.32')
    assert ingresar(client, 'admin_a', CLAVE, ip='198.51.100.33').status_code == 200
    assert '_auth_user_id' not in client.session


def test_la_pausa_de_una_cuenta_no_revela_su_correo(client, mundo):
    for numero in range(intentos.LIMITES['login-cuenta']):
        ingresar(client, 'admin_a', 'clave-equivocada', ip=f'203.0.113.{numero + 1}')
    # Correo de la cuenta pausada frente a uno inexistente: misma respuesta, sin 429.
    propio = ingresar(client, 'admin_a@example.test', 'otra-clave', ip='198.51.100.40')
    ajeno = ingresar(client, 'nadie@example.test', 'otra-clave', ip='198.51.100.41')
    assert propio.status_code == ajeno.status_code == 200
    assert propio.context['form'].non_field_errors() == ajeno.context['form'].non_field_errors()
    # Sin contraseña no hay intento ni respuesta distinta.
    vacio_propio = client.post(reverse('cuentas:login'), {'username': 'admin_a@example.test', 'password': ''})
    vacio_ajeno = client.post(reverse('cuentas:login'), {'username': 'nadie@example.test', 'password': ''})
    assert vacio_propio.status_code == vacio_ajeno.status_code == 200
    assert vacio_propio.context['form'].errors == vacio_ajeno.context['form'].errors


def test_contador_siempre_tiene_vencimiento(mundo):
    # Aunque una clave haya quedado sin vencimiento, el siguiente intento se lo devuelve.
    cliente, clave = intentos._redis('login-cuenta', 'admin_a')
    cliente.set(clave, 3)
    assert cliente.ttl(clave) == -1
    assert intentos.reservar('login-cuenta', 'admin_a') == 4
    assert 0 < cliente.ttl(clave) <= intentos.VENTANA
    cliente.expire(clave, 100)
    intentos.reservar('login-cuenta', 'admin_a')
    assert cliente.ttl(clave) <= 100  # no alarga una ventana vigente


def test_ingreso_correcto_devuelve_el_lugar_de_la_ip(client, mundo):
    for _ in range(intentos.LIMITES['login-ip'] + 3):
        assert ingresar(client, 'editor_a', CLAVE, ip='192.0.2.70').status_code == 302
        client.post(reverse('cuentas:logout'))


def test_reserva_concurrente_admite_solo_el_limite(mundo):
    import threading
    hilos, admitidos, barrera = 12, [], threading.Barrier(12)

    def intentar():
        barrera.wait()  # todos reservan al mismo tiempo
        admitidos.append(not intentos.excede('login-cuenta', intentos.reservar('login-cuenta', 'concurrente')))

    trabajadores = [threading.Thread(target=intentar) for _ in range(hilos)]
    for hilo in trabajadores:
        hilo.start()
    for hilo in trabajadores:
        hilo.join()
    assert admitidos.count(True) == intentos.LIMITES['login-cuenta']


def test_recuperar_la_contrasena_libera_la_pausa(client, mundo):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    editor = mundo['users']['editor_a']
    for numero in range(intentos.LIMITES['login-cuenta']):
        ingresar(client, 'editor_a', 'clave-equivocada', ip=f'203.0.113.{numero + 1}')
    url = reverse('cuentas:password_reset_confirm',
                  args=[urlsafe_base64_encode(force_bytes(editor.pk)), default_token_generator.make_token(editor)])
    formulario = client.get(url, follow=True)
    nueva = 'Nueva#Clave2026xy'
    client.post(formulario.redirect_chain[-1][0], {'new_password1': nueva, 'new_password2': nueva})
    assert ingresar(client, 'editor_a', nueva, ip='198.51.100.60').status_code == 302
