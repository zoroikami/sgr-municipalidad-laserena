"""Exercise panel navigation and description counters on the local demo app."""
import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
OUTPUT = ROOT / 'output/browser/paneles'


def run():
    account = next(a for a in json.loads((ROOT / '.private/cuentas-demo.json').read_text()) if a['usuario'] == 'admin_a')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, locale='es-CL', reduced_motion='reduce')
        page.set_default_timeout(5000)
        page.goto(BASE + '/cuentas/login/')
        page.locator('[name=username]').fill('admin_a')
        page.locator('[name=password]').fill(account['password'])
        page.locator('[name=password]').press('Enter')
        page.wait_for_url(BASE + '/')

        for width in [320, 375, 768, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            panels = page.locator('.module-previews')
            expect(panels.locator('.module-preview-footer a')).to_have_count(2)
            expect(panels.get_by_role('table')).to_have_count(2)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(OUTPUT / f'inicio-{width}.png'), full_page=True)

        for modulo in ['atenciones', 'metas']:
            page.goto(BASE + '/')
            card = page.locator('.module-previews').locator(f'a[href="/gestion/{modulo}/"]')
            card.focus()
            card.press('Enter')
            page.wait_for_url(BASE + f'/gestion/{modulo}/')
        page.goto(BASE + '/')
        page.locator('.module-previews .record-key').first.click()
        page.wait_for_url(re.compile(re.escape(BASE) + r'/gestion/atenciones/\d+/'))

        for modulo in ['metas', 'atenciones']:
            page.goto(BASE + f'/gestion/{modulo}/crear/')
            field = page.locator('[name=descripcion]')
            expect(field).to_have_attribute('maxlength', '500')
            counter = page.locator('[data-description-counter]')
            expect(counter).to_have_text('0 / 500')
            field.fill('á' * 500)
            expect(counter).to_have_text('500 / 500')
            field.press('End')
            field.press('x')
            expect(field).to_have_value('á' * 500)
            field.fill('Solicitud municipal')
            expect(counter).to_have_text('19 / 500')
        page.screenshot(path=str(OUTPUT / 'descripcion.png'), full_page=True)
        browser.close()
    print('Panels: mini tables, record detail links, Enter navigation, responsive layouts and live 500-character counters passed.')


if __name__ == '__main__':
    run()
