"""Flujo local: avances con historial y plazos, consulta y capturas responsivas."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8003').rstrip('/')
OUTPUT = ROOT / '.private/tablero/capturas'
PREFIX = os.environ.get('SGR_DEMO_PREFIX', 'DEMO TABLERO')


def login(page, accounts, alias):
    page.goto(BASE + '/cuentas/login/')
    page.locator('[name=username]').fill(alias)
    page.locator('[name=password]').fill(accounts[alias]['password'])
    page.get_by_role('button', name='Ingresar', exact=True).click()
    page.wait_for_url(BASE + '/')


def run():
    if urlsplit(BASE).hostname not in {'127.0.0.1', 'localhost'}:
        raise RuntimeError('Solo se admite el entorno local de pruebas.')
    accounts = {row['usuario']: row for row in json.loads((ROOT / '.private/tablero/demo.json').read_text())}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1280, 'height':900}, locale='es-CL')
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, accounts, 'editor_a')
        for path, title, name, action, note in [
            ('/cartas/tablero/', 'Tubo de cartas', f'{PREFIX} - Carta atrasada', 'Aprobar', 'Revisión local de aprobación'),
            ('/tubo/', 'Tubo de trabajo', f'{PREFIX} - Gestión atrasada', 'Realizar', 'Cierre local verificado'),
        ]:
            assert page.goto(BASE + path).status == 200
            expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
            card = page.locator('.tubo-tarjeta').filter(has=page.get_by_role('heading', name=name, exact=True))
            expect(card.get_by_text('Vencido', exact=True)).to_be_visible()
            for width in [320, 375, 768, 1280]:
                page.set_viewport_size({'width':width, 'height':900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (path,width)
                expect(card.get_by_role('button',name=action,exact=True)).to_be_visible()
                page.screenshot(path=str(OUTPUT/f'{title.lower().replace(" ", "-")}-{width}.png'), full_page=True)
                checks.append({'ruta':path,'ancho':width,'sin_desbordamiento':True})
            form = card.locator('form').filter(has=page.get_by_role('button', name=action, exact=True))
            form.locator('[name=observacion]').fill(note)
            form.get_by_role('button', name=action, exact=True).click()
            page.wait_for_url(BASE+path)
            if path == '/cartas/tablero/':
                form = card.locator('form').filter(has=page.get_by_role('button', name='Finalizar', exact=True))
                form.locator('[name=observacion]').fill('Finalización local verificada')
                form.get_by_role('button', name='Finalizar', exact=True).click()
                page.wait_for_url(BASE+path)
            expect(card.get_by_text('Realizado fuera de plazo', exact=True)).to_be_visible()
            card.get_by_role('link', name='Ver detalle', exact=True).click()
            expect(page.get_by_role('heading', name='Historial de estados', exact=True)).to_be_visible()
            expect(page.get_by_role('cell', name=note, exact=True)).to_be_visible()
            for width in [375,1280]:
                page.set_viewport_size({'width':width,'height':900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(OUTPUT/f'historial-{title.lower().replace(" ", "-")}-{width}.png'),full_page=True)
        reader = browser.new_page(viewport={'width':375,'height':900})
        login(reader, accounts, 'lector_a')
        for path in ['/cartas/tablero/','/tubo/']:
            assert reader.goto(BASE+path).status == 200
            assert reader.locator('.tubo-tarjeta form').count() == 0
        assert not errors, errors
        browser.close()
    (OUTPUT.parent/'navegador.json').write_text(json.dumps({'vistas':checks,'historial_y_cierre_tardio':True,
        'consultor_sin_controles_de_cambio':True,'errores_js':errors},ensure_ascii=False,indent=2))
    print('Tableros verificados: 320/375/768/1280, avances reales, historial, cierre tardío y consultor de solo lectura.')


if __name__ == '__main__':
    run()
