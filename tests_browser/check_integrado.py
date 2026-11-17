"""Read-only checks of the integrated municipal modules on a local demo server."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001').rstrip('/')
OUTPUT = ROOT / 'output/browser/integrado'


def run():
    if urlsplit(BASE).hostname not in {'127.0.0.1', 'localhost'}:
        raise RuntimeError('Esta comprobación utiliza únicamente el entorno local de demostración.')
    accounts = {a['usuario']: a for a in json.loads((ROOT / '.private/cuentas-demo.json').read_text())}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, locale='es-CL')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/cuentas/login/')
        page.locator('[name=username]').fill('editor_a')
        page.locator('[name=password]').fill(accounts['editor_a']['password'])
        page.get_by_role('button', name='Ingresar', exact=True).click()
        page.wait_for_url(BASE + '/')
        for path, title, nav in [
            ('/tubo/', 'Tubo de trabajo', 'Tubo de trabajo'),
            ('/sgr/', 'Resultados SGR', 'Resultados SGR'),
            ('/gestion/organizaciones/', 'Organizaciones comunitarias', 'Organizaciones'),
        ]:
            response = page.goto(BASE + path)
            assert response.status == 200
            expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
            expect(page.locator('.module-nav').get_by_role('link', name=nav, exact=True)).to_have_attribute('aria-current', 'page')
            for width in [320, 375, 768, 1280]:
                page.set_viewport_size({'width': width, 'height': 900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (path, width)
                if path == '/sgr/':
                    expect(page.locator('#id_responsable')).to_have_class('form-select')
                    expect(page.locator('#id_anio')).to_have_class('form-control')
                page.screenshot(path=str(OUTPUT / f'{nav.lower().replace(" ", "-")}-{width}.png'), full_page=True)
        for path in ['/gestion/tubo/crear/', '/sgr/actividad/']:
            response = page.goto(BASE + path)
            assert response.status == 200
            expect(page.locator('#record-modal')).to_be_visible()
            for width in [320, 1280]:
                page.set_viewport_size({'width': width, 'height': 900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(OUTPUT / f'{path.strip("/").replace("/", "-")}-{width}.png'), full_page=True)
        admin = json.loads((ROOT / '.private/superadmin.json').read_text())[0]
        global_page = browser.new_page(viewport={'width': 1280, 'height': 900})
        global_page.on('pageerror', lambda error: errors.append(str(error)))
        global_page.goto(BASE + '/cuentas/login/')
        global_page.locator('[name=username]').fill(admin['usuario'])
        global_page.locator('[name=password]').fill(admin['password'])
        global_page.get_by_role('button', name='Ingresar', exact=True).click()
        global_page.wait_for_url(BASE + '/')
        for path, relation in [('/gestion/tubo/crear/', 'responsable'),
                               ('/sgr/actividad/', 'item'), ('/sgr/ausencia/', 'responsable')]:
            assert global_page.goto(BASE + path).status == 200
            assert global_page.locator(f'#id_{relation} option').count() > 1
        assert not errors, errors
        browser.close()
    print('Integrado: módulos, navegación, filtros, formularios locales/globales y diseño a 320/375/768/1280; sin errores JavaScript.')


if __name__ == '__main__':
    run()
