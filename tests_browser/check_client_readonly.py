"""Check the read-only Cliente role and cross-client privacy without changing records."""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
DEMO = Path(os.environ.get('SGR_DEMO_CREDENTIALS', ROOT / '.private/cuentas-demo.json'))
SUPPORT = Path(os.environ.get('SGR_SUPPORT_CREDENTIALS', ROOT / '.private/superadmin.json'))
OUTPUT = ROOT / 'output/browser/cliente-solo-lectura'


def login(page, account, destination):
    page.goto(BASE + '/cuentas/login/')
    page.locator('[name=username]').fill(account['usuario'])
    page.locator('[name=password]').fill(account['password'])
    page.locator('[name=password]').press('Enter')
    page.wait_for_url(BASE + destination)


def run():
    demo = {row['usuario']: row for row in json.loads(DEMO.read_text())}
    support = json.loads(SUPPORT.read_text())[0]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        contexts = [browser.new_context(viewport={'width': 1280, 'height': 900}) for _ in range(3)]
        admin, one, two = [context.new_page() for context in contexts]
        login(admin, support, '/')
        admin.goto(BASE + '/cuentas/roles/')
        admin.locator('.role-card').filter(has=admin.get_by_text('Cliente', exact=True)).click()
        options = admin.locator('.permission-options input[type=checkbox]')
        expect(options).to_have_count(1)
        expect(options).to_be_checked()
        expect(admin.locator('.permission-options')).to_have_text('Consultar')
        expect(admin.locator('.roles-editor-heading')).to_contain_text('atenciones asociadas a su cuenta')
        admin.screenshot(path=str(OUTPUT / 'rol-cliente.png'), full_page=True)
        for page, alias in [(one, 'cliente_1'), (two, 'cliente_2')]:
            login(page, demo[alias], '/portal/')
            expect(page.locator('.module-nav a')).to_have_count(1)
            expect(page.locator('.module-nav a')).to_have_text('Mis atenciones')
            assert page.locator('.record-key').count() > 0
        first = one.locator('.record-key').first.get_attribute('href')
        second = two.locator('.record-key').first.get_attribute('href')
        assert first != second
        assert one.request.get(BASE + first).status == 200
        assert two.request.get(BASE + second).status == 200
        assert one.request.get(BASE + second).status == 404
        assert two.request.get(BASE + first).status == 404
        for page in (one, two):
            assert page.request.get(BASE + '/gestion/atenciones/crear/').status == 403
            assert page.request.get(BASE + '/cuentas/roles/').status == 403
        browser.close()
    print('Cliente: Roles solo ofrece Consultar; dos clientes ven registros distintos y reciben 404 al consultar los del otro. Sin cambios de negocio.')


if __name__ == '__main__':
    run()
