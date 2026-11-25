"""Textos largos: el servidor respeta los límites y las pantallas no se desbordan con palabras sin espacios."""
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from gestion.models import ActividadSGR, Carta, CasoSocial, GestionTubo

LARGO = 'x' * 140  # una «palabra» del máximo del nombre, sin espacios


def test_descripcion_y_observaciones_respetan_su_limite(client, mundo, db):
    client.force_login(mundo['users']['editor_a'])
    datos = {'nombre': 'Poda en pasaje', 'fecha_solicitud': timezone.localdate().isoformat(), 'origen': 'EXT',
             'solicitante': 'Vecina', 'solicitante_telefono': '912345678', 'responsable': mundo['users']['editor_a'].pk}
    errores = client.post(reverse('gestion:crear', args=['tubo']),
                          {**datos, 'descripcion': 'a' * 501, 'observaciones': 'b' * 2001}).context['form'].errors
    assert 'descripcion' in errores and 'observaciones' in errores
    assert client.post(reverse('gestion:crear', args=['tubo']),
                       {**datos, 'descripcion': 'a' * 500, 'observaciones': 'b' * 2000}).status_code == 302
    html = client.get(reverse('gestion:crear', args=['tubo'])).content.decode()
    assert 'maxlength="500"' in html and 'maxlength="2000"' in html


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('ancho', [375, 1280])
def test_palabras_largas_no_desbordan_las_pantallas(client, mundo, live_server, ancho):
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    a, editor = mundo['a'], mundo['users']['editor_a']
    gestion = GestionTubo.objects.create(delegacion=a, nombre=LARGO, descripcion='y' * 500, solicitante='z' * 140,
                                         solicitante_telefono='912345678', responsable=editor, apoyo='w' * 160,
                                         observaciones='v' * 2000)
    Carta.objects.create(delegacion=a, nombre=LARGO, numero_ingreso='n' * 50, remite='r' * 140, encargado=editor,
                         observacion='o' * 2000)
    caso = CasoSocial.objects.create(delegacion=a, nombre=LARGO, responsable=editor, usuario_telefono='912345678',
                                     descripcion='d' * 500)
    ActividadSGR.objects.create(delegacion=a, responsable=editor, item=mundo['meta_a'], cargo='social',
                                descripcion='e' * 500, accion='f' * 200, derivado_a='g' * 140)
    client.force_login(mundo['users']['admin_a'])
    paginas = [reverse('gestion:tablero'), reverse('gestion:cartas_tablero'), reverse('gestion:listado', args=['tubo']),
               reverse('gestion:listado', args=['cartas']), reverse('gestion:listado', args=['casos']),
               reverse('gestion:detalle', args=['tubo', gestion.pk]), reverse('gestion:detalle', args=['casos', caso.pk]),
               f"{reverse('gestion:resultados_sgr')}?anio={timezone.localdate().year}"
               f"&trimestre={(timezone.localdate().month - 1) // 3 + 1}&responsable={editor.pk}"]
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': ancho, 'height': 900}, locale='es-CL')
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME,
                              'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
        page = context.new_page()
        for ruta in paginas:
            page.goto(live_server.url + ruta)
            ancho_pagina = page.evaluate('document.documentElement.scrollWidth')
            assert ancho_pagina <= ancho, f'{ruta} se desborda a {ancho} px ({ancho_pagina} px)'
        browser.close()


@pytest.mark.django_db(transaction=True)
def test_contador_de_caracteres_bajo_la_descripcion(client, mundo, live_server):
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    client.force_login(mundo['users']['editor_a'])  # fuera del bucle asíncrono de Playwright
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(locale='es-CL')
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME,
                              'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
        page = context.new_page()
        page.goto(live_server.url + reverse('gestion:crear', args=['tubo']))
        contador = page.locator('#id_descripcion-contador')
        api.expect(contador).to_have_text('0 de 500 caracteres')
        page.locator('#id_descripcion').fill('a' * 460)
        api.expect(contador).to_have_text('460 de 500 caracteres')
        api.expect(contador).to_have_class('contador-caracteres cerca-del-limite')
        assert 'id_descripcion-contador' in page.locator('#id_descripcion').get_attribute('aria-describedby')
        browser.close()
