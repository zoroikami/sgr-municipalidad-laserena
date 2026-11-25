"""Verificación integrada con datos ficticios y un servidor/Chromium reales."""
from pathlib import Path

import pytest
from django.conf import settings

from gestion.integrado import CARGOS
from gestion.models import GestionTubo

pytestmark = pytest.mark.django_db(transaction=True)


def chromium_api():
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    return api


def authenticated_context(browser, client, live_server, width):
    context = browser.new_context(viewport={'width': width, 'height': 900}, locale='es-CL')
    context.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': client.cookies[settings.SESSION_COOKIE_NAME].value,
                         'url': live_server.url}])
    return context


def screenshot(page, tmp_path, name):
    notice = page.locator('.rut-aviso')
    if notice.count() and notice.is_visible():
        notice.scroll_into_view_if_needed()
    page.screenshot(path=str(tmp_path / f'{name}.png'), full_page=True)


@pytest.mark.parametrize('path', ['/gestion/tubo/crear/', '/gestion/atenciones/crear/'])
@pytest.mark.parametrize('width', [375, 1280])
def test_avisos_rut_funcionario_delegado_y_vecino(client, mundo, live_server, tmp_path, path, width):
    api = chromium_api()
    worker = mundo['users']['editor_a']
    worker.first_name, worker.last_name = 'Funcionario', 'Verificación'
    worker.save()
    profile = worker.perfil
    profile.cargo_sgr = 'servicios'
    profile.save()
    client.force_login(worker)
    errors = []
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = authenticated_context(browser, client, live_server, width).new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        assert page.goto(live_server.url + path).status == 200
        field, notice = page.locator('[name=solicitante_rut]'), page.locator('.rut-aviso')
        field.fill(worker.perfil.rut)
        field.dispatch_event('change')
        api.expect(notice).to_contain_text('Funcionario Verificación')
        api.expect(notice).to_contain_text('Coordinador de servicios comunitarios')
        api.expect(notice).to_contain_text('Delegación Centro')
        api.expect(notice.locator('.rut-aviso-funciones')).to_be_visible()
        api.expect(notice).not_to_have_class('rut-aviso es-delegado')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        screenshot(page, tmp_path, f'funcionario-{width}')
        field.fill(mundo['users']['admin_a'].perfil.rut)
        field.dispatch_event('change')
        api.expect(notice).to_have_class('rut-aviso es-delegado')
        api.expect(notice).to_contain_text('otra gestión y no suma puntaje')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        screenshot(page, tmp_path, f'delegado-{width}')
        for value in [mundo['users']['cliente_1'].perfil.rut, 'RUT inválido']:
            field.fill(value)
            field.dispatch_event('change')
            api.expect(notice).to_be_hidden()
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize('width', [375, 1280])
def test_insignias_cargos_y_tabla_colaboradores_conservan_arrastre(client, mundo, live_server, tmp_path, width):
    api = chromium_api()
    editor = mundo['users']['editor_a']
    for number, (cargo, _) in enumerate(CARGOS):
        obj = GestionTubo.objects.create(delegacion=mundo['a'], nombre=f'Verificación del cargo {number}',
            solicitante='Funcionario de prueba', responsable=editor, solicitante_rut=editor.perfil.rut,
            solicitante_telefono='912345678')
        # El historial de cargo conserva la etiqueta vigente al identificar al solicitante.
        GestionTubo.objects.filter(pk=obj.pk).update(solicitante_cargo=cargo)
    client.force_login(editor)
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = authenticated_context(browser, client, live_server, width).new_page()
        assert page.goto(live_server.url + '/tubo/').status == 200
        for _, name in CARGOS:
            api.expect(page.get_by_text(f'Funcionario · {name}', exact=True)).to_be_visible()
        api.expect(page.get_by_text('Otra gestión: la solicita el delegado y no suma puntaje.', exact=True)).to_be_visible()
        api.expect(page.get_by_role('heading', name='Avance por colaborador', exact=True)).to_be_visible()
        table = page.locator('.tubo-colaboradores .table-responsive')
        screenshot(page, tmp_path, f'insignias-colaboradores-{width}')
        page.get_by_text('Funcionario · Coordinador de servicios comunitarios', exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(tmp_path / f'insignia-larga-{width}.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert table.evaluate('(el) => el.scrollWidth <= el.clientWidth || ["auto", "scroll"].includes(getComputedStyle(el).overflowX)')
        bounds = page.locator('.tubo-funcionario').evaluate_all('''badges => badges.map(b => ({
            texto: b.textContent, derecha: b.getBoundingClientRect().right,
            limite: b.closest('.tubo-tarjeta').getBoundingClientRect().right
        })).filter(b => b.derecha > b.limite)''')
        assert not bounds, bounds
        if width == 1280:
            first = page.locator('.tubo-tarjeta').first
            first.drag_to(page.locator('.tubo-columna[data-estado="Pendiente"]'), source_position={'x': 10, 'y': 10})
            api.expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='Mover tarjeta', exact=True).click()
            api.expect(page.locator('.tubo-columna[data-estado="Pendiente"] .tubo-tarjeta')).to_have_count(1)
        else:
            page.locator('.tubo-tarjeta').first.get_by_role('button', name='A pendiente', exact=True).click()
            api.expect(page.locator('.tubo-columna[data-estado="Pendiente"] .tubo-tarjeta')).to_have_count(1)
        browser.close()


def test_telefono_obligatorio_y_territorios_sugeridos(client, mundo, live_server, tmp_path):
    api = chromium_api()
    client.force_login(mundo['users']['coordinador'])
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = authenticated_context(browser, client, live_server, 375).new_page()
        assert page.goto(live_server.url + f'/gestion/tubo/crear/?delegacion={mundo["b"].pk}').status == 200
        api.expect(page.locator('[name=solicitante_telefono]')).to_have_attribute('required', '')
        api.expect(page.locator('[name=territorio]')).to_have_attribute('list', 'id_territorio_sugerencias')
        for name in ['Latorre', 'Rukalaf', 'Toqui', 'Zorrilla']:
            api.expect(page.locator(f'#id_territorio_sugerencias option[value="{name}"]')).to_have_count(1)
        screenshot(page, tmp_path, 'telefono-territorios-375')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        browser.close()


def test_respuesta_tardia_no_muestra_funcionario_para_rut_borrado(client, mundo, live_server, tmp_path):
    api = chromium_api()
    client.force_login(mundo['users']['editor_a'])
    pending = []
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = authenticated_context(browser, client, live_server, 375).new_page()

        def delay(route):
            response = route.fetch()
            pending.append((route, response))
            page.evaluate('window.__rutRetained = true')

        page.route('**/funcionarios/rut/', delay)
        page.goto(live_server.url + '/gestion/tubo/crear/')
        page.clock.install()
        field, notice = page.locator('[name=solicitante_rut]'), page.locator('.rut-aviso')
        with page.expect_request('**/funcionarios/rut/'):
            field.fill(mundo['users']['admin_a'].perfil.rut)
            field.dispatch_event('change')
        page.wait_for_function('window.__rutRetained === true')
        field.fill('')
        field.dispatch_event('change')
        page.clock.fast_forward(400)
        api.expect(notice).to_be_hidden()
        assert pending, 'La consulta real quedó retenida por el interceptor de red.'
        route, response = pending.pop()
        route.fulfill(response=response)
        # Esperar la respuesta y un frame del navegador permite aplicar su resultado al DOM.
        page.wait_for_load_state('networkidle')
        screenshot(page, tmp_path, 'respuesta-tardia-rut-vacio')
        api.expect(notice).to_be_hidden()
        browser.close()


def test_tipo_de_gestion_diserco_solo_se_muestra_al_coordinador_de_servicios(client, mundo, live_server):
    api = chromium_api()
    worker = mundo['users']['editor_a']  # sin cargo asignado: el selector de cargo queda habilitado
    client.force_login(worker)
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = authenticated_context(browser, client, live_server, 1280).new_page()
        page.goto(live_server.url + '/sgr/actividad/')
        tipo = page.locator('#id_tipo_gestion')
        api.expect(tipo).to_be_hidden()
        page.select_option('#id_cargo', 'servicios')
        api.expect(tipo).to_be_visible()
        tipo.select_option('podas')
        page.select_option('#id_cargo', 'social')
        api.expect(tipo).to_be_hidden()
        assert tipo.input_value() == ''
        browser.close()
