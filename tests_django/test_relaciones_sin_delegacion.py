"""Cuenta global sin delegación elegida: las listas dependientes avisan que primero hay que elegirla."""
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db(transaction=True)


def test_tipo_avisa_que_falta_la_delegacion_y_se_carga_al_elegirla(client, mundo, live_server):
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    client.force_login(get_user_model().objects.create_superuser('raiz', 'raiz@example.test', 'Ensayo#Privado2026'))
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(locale='es-CL')
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME,
                              'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
        page = context.new_page()
        page.goto(live_server.url + reverse('gestion:crear', args=['atenciones']))
        tipo = page.locator('#id_tipo')
        api.expect(tipo).to_be_disabled()
        api.expect(tipo.locator('option').first).to_have_text('Primero elige la delegación')
        with page.expect_navigation():
            page.select_option('#id_delegacion', value=str(mundo['a'].pk))
        api.expect(page.locator('#id_tipo')).to_be_enabled()
        assert page.locator('#id_tipo option').count() > 1
        browser.close()
