"""Verify restored municipal UI behavior against the running demo application.

Private demo credentials stay in memory. Screenshots never capture passwords.
Run: .venv/bin/python tests_browser/check_design.py
"""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
OUTPUT = ROOT / 'output/browser/design'


def no_page_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


def run():
    accounts = {a['usuario']: a for a in json.loads((ROOT / '.private/cuentas-demo.json').read_text())}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, locale='es-CL')
        page.goto(BASE + '/cuentas/login/')
        password = page.locator('[name=password]')
        expect(password).to_have_attribute('type', 'password')
        page.get_by_role('button', name='Mostrar contraseña', exact=True).click()
        expect(password).to_have_attribute('type', 'text')
        expect(page).to_have_url(BASE + '/cuentas/login/')
        page.get_by_role('button', name='Ocultar contraseña', exact=True).click()
        expect(password).to_have_attribute('type', 'password')
        for width in [320, 375, 768, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            no_page_overflow(page)
            page.screenshot(path=str(OUTPUT / f'login-{width}.png'), full_page=True)
        print('Design: password toggle never submits; login fits 320/375/768/1280.')

        page.locator('[name=username]').fill('admin_a')
        password.fill(accounts['admin_a']['password'])
        password.press('Enter')
        page.wait_for_url(BASE + '/')
        page.goto(BASE + '/gestion/metas/')
        expect(page.locator('.module-nav').get_by_role('link', name='Ítems y metas', exact=True)).to_have_attribute('aria-current', 'page')
        for width in [320, 375, 768, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            no_page_overflow(page)
            expect(page.get_by_role('link', name='Exportar Excel', exact=True)).to_be_visible()
            page.screenshot(path=str(OUTPUT / f'metas-{width}.png'), full_page=True)
        page.goto(BASE + '/cuentas/perfil/')
        expect(page.get_by_role('heading', name='Mi perfil', exact=True)).to_be_visible()
        for width in [375, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            no_page_overflow(page)
            page.screenshot(path=str(OUTPUT / f'perfil-{width}.png'), full_page=True)
        print('Design: Enter login, current navigation, Excel access and responsive profile passed.')
        browser.close()


if __name__ == '__main__':
    run()
