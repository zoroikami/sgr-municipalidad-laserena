"""Read-only browser checks for the municipal delegation and account controls."""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
OUTPUT = ROOT / 'output/browser/delegaciones-roles'


def sign_in(page, account):
    page.goto(BASE + '/cuentas/login/')
    page.locator('[name=username]').fill(account['usuario'])
    page.locator('[name=password]').fill(account['password'])
    page.locator('[name=password]').press('Enter')
    page.wait_for_url(BASE + '/')


def choose(page, label):
    with page.expect_navigation(wait_until='domcontentloaded'):
        page.locator('#active-delegation').select_option(label=label)


def run():
    account = json.loads((ROOT / '.private/superadmin.json').read_text())[0]
    demo = {row['usuario']: row for row in json.loads((ROOT / '.private/cuentas-demo.json').read_text())}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-CL')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        sign_in(page, account)
        expect(page.locator('#active-delegation option')).to_have_count(7)
        initial_total = page.locator('.module-preview-total').first.inner_text()
        choose(page, 'Las Compañías')
        expect(page.locator('#active-delegation-description')).to_contain_text('DEL02')
        expect(page.get_by_role('heading', name='Registros de Las Compañías')).to_be_visible()
        assert page.locator('.module-preview-total').first.inner_text() != initial_total
        choose(page, 'Centro')
        expect(page.locator('#active-delegation-description')).to_contain_text('DEL01')
        choose(page, 'Todas las delegaciones')
        expect(page.locator('.module-preview-total').first).to_have_text(initial_total)
        page.goto(BASE + '/cuentas/roles/')
        names = page.locator('.role-card strong').all_text_contents()
        assert sorted(names) == sorted(['Superadministrador', 'Coordinador', 'Delegado Municipal',
                                        'Operador / Funcionario', 'Consultor', 'Cliente'])
        page.screenshot(path=str(OUTPUT / 'roles-escritorio.png'), full_page=True)
        page.goto(BASE + '/cuentas/usuarios/nuevo/')
        expect(page.locator('#id_role option')).to_have_count(6)
        checkbox = page.locator('#id_is_active')
        label = page.locator('label[for=id_is_active] span')
        for width in [1280, 768, 375, 320]:
            page.set_viewport_size({'width': width, 'height': 900})
            checkbox.scroll_into_view_if_needed()
            a, b = checkbox.bounding_box(), label.bounding_box()
            assert abs((a['y'] + a['height'] / 2) - (b['y'] + b['height'] / 2)) <= 2
            assert a['x'] + a['width'] < b['x']
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(OUTPUT / f'cuenta-activa-{width}.png'), full_page=True)
        for alias, role in [('admin_a', 'Delegado Municipal'), ('editor_a', 'Operador / Funcionario'), ('lector_a', 'Consultor')]:
            local = browser.new_context(viewport={'width': 1280, 'height': 900})
            local_page = local.new_page()
            sign_in(local_page, demo[alias])
            expect(local_page.locator('#active-delegation')).to_have_count(0)
            expect(local_page.locator('.user-header-role')).to_contain_text(role)
            if alias == 'editor_a':
                expect(local_page.locator('.module-preview')).to_have_count(1)
                assert local_page.goto(BASE + '/gestion/metas/crear/').status == 403
            local.close()
        assert not errors, errors
        browser.close()
    print('Browser: six restored roles, delegation changes, local account isolation and checkbox alignment verified at 1280/768/375/320px.')


if __name__ == '__main__':
    run()
