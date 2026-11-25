"""Roles y permisos con la estética del sitio: resumen del rol, nombres de módulo legibles y contadores por módulo."""
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

pytestmark = pytest.mark.django_db


def superadmin():
    return get_user_model().objects.create_superuser('raiz', 'raiz@example.test', 'Ensayo#Privado2026')


def test_resumen_del_rol_y_modulos_con_nombre_legible(client, mundo):
    client.force_login(superadmin())
    cliente = Group.objects.get(name='Cliente')
    respuesta = client.get(reverse('cuentas:roles'), {'grupo': cliente.pk})
    assert respuesta.context['resumen_rol'] == {'permisos': 1, 'modulos': 1, 'total_modulos': len(respuesta.context['permission_sections']),
                                                'cuentas': 2}
    html = respuesta.content.decode()
    assert 'Permisos asignados' in html and 'Módulos con acceso' in html and 'Cuentas activas' in html
    # Cliente solo admite consultar sus atenciones: un módulo, completo.
    atenciones = next(s for s in respuesta.context['permission_sections'] if s['name'] == 'Atenciones ciudadanas')
    assert (atenciones['marcados'], atenciones['total'], atenciones['tono']) == (1, 1, 'verde')
    delegado = Group.objects.get(name='Delegado Municipal')
    respuesta = client.get(reverse('cuentas:roles'), {'grupo': delegado.pk})
    secciones = {s['name']: s for s in respuesta.context['permission_sections']}
    assert [item['label'] for item in secciones['Atenciones ciudadanas']['items']] == ['Consultar', 'Crear', 'Editar', 'Eliminar']
    actividades = secciones['Actividades SGR']
    assert actividades['tono'] == 'ambar' and actividades['items'][-1]['especial']
    html = respuesta.content.decode()
    assert 'Actividades SGR' in html and 'Actividad sgr' not in html


@pytest.mark.django_db(transaction=True)
def test_contadores_siguen_a_las_casillas(client, mundo, live_server):
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    client.force_login(superadmin())
    cliente = Group.objects.get(name='Cliente')
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(locale='es-CL')
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME,
                              'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
        page = context.new_page()
        page.goto(f"{live_server.url}{reverse('cuentas:roles')}?grupo={cliente.pk}")
        modulo = page.locator('.permission-module', has_text='Atenciones ciudadanas')
        api.expect(modulo.locator('.permission-cantidad')).to_have_text('1 de 1')
        modulo.get_by_label('Consultar').uncheck()
        api.expect(modulo.locator('.permission-cantidad')).to_have_text('0 de 1')
        api.expect(modulo).to_have_attribute('data-tono', 'gris')
        api.expect(page.locator('[data-total-permisos]')).to_have_text('0')
        api.expect(page.locator('[data-total-modulos]')).to_have_text('0')
        browser.close()
