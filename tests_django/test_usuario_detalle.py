"""Usuarios › Ver: ficha completa con foto privada por ámbito, teléfono del perfil y estados de cartas con color."""
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image

from gestion.models import Carta

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    # Las fotos de prueba no deben quedar en la carpeta media real.
    settings.MEDIA_ROOT = tmp_path


def con_foto(user):
    salida = BytesIO()
    Image.new('RGB', (8, 8), (139, 29, 25)).save(salida, format='PNG')
    user.perfil.foto.save('foto.png', ContentFile(salida.getvalue()), save=True)


def test_delegado_ve_la_ficha_completa_de_su_equipo(client, mundo):
    editor = mundo['users']['editor_a']
    editor.first_name, editor.last_name = 'Ana', 'Rojas'
    editor.save()
    editor.perfil.telefono, editor.perfil.cargo_sgr = '+56 9 1234 5678', 'social'
    editor.perfil.save()
    con_foto(editor)
    client.force_login(mundo['users']['admin_a'])
    listado = client.get(reverse('cuentas:usuarios')).content.decode()
    assert reverse('cuentas:usuario_detalle', args=[editor.pk]) in listado and 'Ver</a>' in listado
    html = client.get(reverse('cuentas:usuario_detalle', args=[editor.pk])).content.decode()
    for dato in ('Ana Rojas', editor.email, '+56 9 1234 5678', 'Gestor social', 'Operador / Funcionario', 'Centro',
                 'Cuenta activa', reverse('cuentas:foto', args=[editor.pk])):
        assert dato in html
    assert '11.000.002' in html  # RUT con formato
    foto = client.get(reverse('cuentas:foto', args=[editor.pk]))
    assert foto.status_code == 200 and foto['Cache-Control'] == 'private, no-store'


def test_ficha_y_foto_respetan_el_ambito(client, mundo):
    externo = mundo['users']['lector_b']
    con_foto(externo)
    con_foto(mundo['users']['admin_a'])
    client.force_login(mundo['users']['admin_a'])
    assert client.get(reverse('cuentas:usuario_detalle', args=[externo.pk])).status_code == 404
    assert client.get(reverse('cuentas:foto', args=[externo.pk])).status_code == 404
    client.force_login(mundo['users']['editor_a'])
    assert client.get(reverse('cuentas:usuario_detalle', args=[mundo['users']['admin_a'].pk])).status_code == 403
    assert client.get(reverse('cuentas:foto', args=[mundo['users']['admin_a'].pk])).status_code == 404


def test_telefono_se_guarda_desde_usuarios_y_desde_mi_perfil(client, mundo):
    editor = mundo['users']['editor_a']
    client.force_login(editor)
    respuesta = client.post(reverse('cuentas:perfil'), {'first_name': 'Ana', 'last_name': 'Rojas', 'email': editor.email,
                                                        'telefono': 'llamar'})
    assert 'telefono' in respuesta.context['form'].errors
    client.post(reverse('cuentas:perfil'), {'first_name': 'Ana', 'last_name': 'Rojas', 'email': editor.email,
                                            'telefono': '+56 9 8765 4321'})
    editor.perfil.refresh_from_db()
    assert editor.perfil.telefono == '+56 9 8765 4321'
    client.force_login(mundo['users']['admin_a'])
    formulario = client.get(reverse('cuentas:usuario_editar', args=[editor.pk])).context['form']
    assert formulario.initial['telefono'] == '+56 9 8765 4321'
    datos = {'username': editor.username, 'first_name': 'Ana', 'last_name': 'Rojas', 'email': editor.email,
             'is_active': 'on', 'rut': editor.perfil.rut, 'role': 'Operador / Funcionario', 'cargo_sgr': '',
             'telefono': '512207884'}
    assert client.post(reverse('cuentas:usuario_editar', args=[editor.pk]), datos).status_code == 302
    editor.perfil.refresh_from_db()
    assert editor.perfil.telefono == '512207884'


def test_estado_de_cartas_tiene_color_en_el_listado(client, mundo):
    for numero, estado in enumerate(['En proceso', 'Aprobada', 'Finalizada', 'No aplica']):
        Carta.objects.create(delegacion=mundo['a'], nombre=f'Carta {numero}', numero_ingreso=f'OP-{numero}',
                             remite='Junta', encargado=mundo['users']['editor_a'], estado=estado)
    client.force_login(mundo['users']['admin_a'])
    html = client.get(reverse('gestion:listado', args=['cartas'])).content.decode()
    for clase, texto in [('en-proceso', 'En proceso'), ('aprobada', 'Aprobada'), ('finalizada', 'Finalizada'),
                         ('no-aplica', 'No aplica')]:
        assert f'<span class="badge-status {clase}">{texto}</span>' in html
