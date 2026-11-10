"""Real page/Croppr bounds, useful previews, RUT help and consistent save actions."""
from io import BytesIO
import json
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
OUTPUT = ROOT / 'output/browser/usability'


def run():
    accounts = json.loads((ROOT / '.private/cuentas-demo.json').read_text())
    account = next(account for account in accounts if account['usuario'] == 'admin_a')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, locale='es-CL')
        page.set_default_timeout(5000)
        page.goto(BASE + '/cuentas/login/')
        page.locator('[name=username]').fill('admin_a')
        page.locator('[name=password]').fill(account['password'])
        page.locator('[name=password]').press('Enter')
        page.wait_for_url(BASE + '/')

        for width in [375, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            expect(page.locator('.module-preview table')).to_have_count(4)
            assert all(table.locator('tbody tr').count() == 3 for table in page.locator('.module-preview table').all())
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(OUTPUT / f'inicio-{width}.png'), full_page=True)

        save_colors = []
        for path, button in [('/cuentas/usuarios/nuevo/', 'Guardar usuario'),
                             ('/cuentas/clave/', 'Guardar contraseña'),
                             ('/gestion/metas/crear/', 'Crear registro')]:
            page.goto(BASE + path)
            save_colors.append(page.get_by_role('button', name=button, exact=True).evaluate('(b) => getComputedStyle(b).backgroundColor'))

        page.goto(BASE + '/cuentas/perfil/')
        save_colors.append(page.locator('#profile-save').evaluate('(b) => getComputedStyle(b).backgroundColor'))
        assert len(set(save_colors)) == 1, save_colors
        for width in [375, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            for size in [(6000, 4000), (4000, 6000)]:
                output = BytesIO()
                Image.new('RGB', size, (196, 18, 48)).save(output, 'PNG')
                page.locator('[name=foto]').set_input_files({'name': 'foto-grande.png', 'mimeType': 'image/png', 'buffer': output.getvalue()})
                expect(page.locator('#crop-apply')).to_be_enabled()
                bounds = page.locator('#crop-panel .croppr-image').bounding_box()
                assert bounds['width'] <= 384 and bounds['height'] <= 320, bounds
                assert abs(bounds['width'] / bounds['height'] - size[0] / size[1]) < 0.01, bounds
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                expect(page.locator('#profile-save')).to_be_disabled()
                page.mouse.move(0, 0)
                expect(page.locator('#crop-apply')).to_have_css('background-color', save_colors[0])
                page.evaluate('window.scrollTo(0, 0)')
                page.screenshot(path=str(OUTPUT / f'recorte-{width}-{size[0]}.png'), full_page=True)
                page.locator('#crop-apply').click()
                expect(page.locator('#crop-preview-panel')).to_be_visible()
                expect(page.locator('#crop-preview-panel')).to_be_focused()
                expect(page.locator('#profile-save')).to_be_enabled()
                expect(page.locator('#crop-panel')).not_to_be_visible()
        page.goto(BASE + '/cuentas/perfil/')
        page.get_by_role('button', name='Elegir foto', exact=True).focus()
        assert page.get_by_role('button', name='Elegir foto', exact=True).evaluate('(b) => b === document.activeElement')
        with page.expect_file_chooser() as selection:
            page.get_by_role('button', name='Elegir foto', exact=True).press('Enter')
        selection.value.set_files({'name': 'seleccion-con-teclado.png', 'mimeType': 'image/png', 'buffer': output.getvalue()})
        expect(page.locator('#crop-apply')).to_be_enabled()
        page.locator('#crop-cancel').click()
        expect(page.locator('#crop-panel')).not_to_be_visible()
        expect(page.get_by_role('button', name='Elegir foto', exact=True)).to_be_focused()
        page.goto(BASE + '/gestion/atenciones/crear/')
        expect(page.locator('#id_solicitante_rut_help')).to_contain_text('sin puntos y con guion')
        page.goto(BASE + '/cuentas/usuarios/nuevo/')
        expect(page.locator('#id_rut_helptext')).to_contain_text('sin puntos y con guion')
        browser.close()
    print('Usability: scoped mini tables, bounded landscape/portrait crop, keyboard photo selector, RUT help and uniform save colors passed.')


if __name__ == '__main__':
    run()
