"""Integration against a locally running, seeded ASGI application.

Uses private .private/cuentas-demo.json, never prints account passwords/tokens.
Run: .venv/bin/python tests_browser/check_flows.py
Optional SGR_BASE_URL and SGR_MAILPIT_URL select another private test environment.
"""
import json
import os
from io import BytesIO
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.request import urlopen

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright, expect
from check_crop import shrink_and_move_crop_left

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
MAILPIT = os.environ.get('SGR_MAILPIT_URL', 'http://127.0.0.1:8025')
ACCOUNTS = {a['usuario']: a for a in json.loads((ROOT / '.private/cuentas-demo.json').read_text())}
OUTPUT = ROOT / 'output/browser'
OUTPUT.mkdir(parents=True, exist_ok=True)


def login(page, alias, password=None):
    page.goto(BASE + '/cuentas/login/')
    page.locator('[name=username]').fill(alias)
    page.locator('[name=password]').fill(password or ACCOUNTS[alias]['password'])
    page.locator('[name=password]').press('Enter')
    page.wait_for_url(lambda url: '/login/' not in str(url))


def read_mail(path):
    with urlopen(MAILPIT + path, timeout=5) as response:
        return json.load(response)


def screenshot(page, name):
    page.screenshot(path=str(OUTPUT / name), full_page=True,
                    mask=[page.locator('input[type=password]')])


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        contexts = {name: browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='es-CL', timezone_id='America/Santiago') for name in ACCOUNTS}
        for context in contexts.values():
            context.add_init_script('''(() => {
              const Native = window.WebSocket;
              window.observedSockets = [];
              window.WebSocket = class extends Native { constructor(...args) { super(...args); window.observedSockets.push(this); } };
              let crop;
              Object.defineProperty(window, 'Croppr', { configurable: true,
                get() { return crop; }, set(Original) { crop = function(...args) {
                  window.observedCrop = new Original(...args); return window.observedCrop;
                }; crop.prototype = Original.prototype; }
              });
            })();''')
        pages = {alias: context.new_page() for alias, context in contexts.items()}
        for alias, page in pages.items():
            login(page, alias)
        print('Browser: six independent sessions authenticated.')

        editor, reader, other, admin = [pages[x] for x in ['editor_a', 'lector_a', 'lector_b', 'admin_a']]
        for page in [reader, other, editor]:
            page.goto(BASE + '/gestion/atenciones/?q=&estado=&tipo=&orden=-created_at&tamano=5&pagina=1')
            expect(page.locator('#realtime-status')).to_have_attribute('data-state', 'connected')
        reader.evaluate('window.noReloadMarker = "kept"')
        frames_b = []
        # Install frame observation on the actual existing B socket before A saves.
        other.evaluate('window.receivedBusinessEvents=[]; window.observedSockets.forEach(s=>s.addEventListener("message", e=>window.receivedBusinessEvents.push(e.data)))')
        first = editor.locator('.records-table tbody tr').first
        edit_url = first.get_by_role('link', name=re.compile('^Editar ')).get_attribute('href')
        original_name = first.locator('td').nth(1).inner_text()
        stamp = 'Verificación WebSocket ' + secrets.token_hex(3)
        editor.goto(BASE + edit_url)
        expect(editor.locator('#record-modal')).to_be_visible()
        editor.locator('[name=solicitante_nombre]').fill(stamp)
        expect(editor.locator('[name=subatencion]')).to_be_enabled()
        editor.get_by_role('button', name='Guardar cambios', exact=True).click()
        expect(reader.locator('#tabla-region')).to_contain_text(stamp)
        assert reader.evaluate('window.noReloadMarker') == 'kept'
        assert other.evaluate('window.receivedBusinessEvents') == []
        assert stamp not in other.locator('#tabla-region').inner_text()
        screenshot(reader, 'lector-a-tiempo-real.png')

        # A change that no longer matches the active filter removes its row.
        reader.locator('#filter-q').fill(stamp)
        reader.get_by_role('button', name='Aplicar filtros').click()
        expect(reader.locator('#realtime-status')).to_have_attribute('data-state', 'connected')
        expect(reader.locator('#tabla-region')).to_contain_text(stamp)
        editor.goto(BASE + edit_url)
        editor.locator('[name=solicitante_nombre]').fill(original_name)
        expect(editor.locator('[name=subatencion]')).to_be_enabled()
        editor.get_by_role('button', name='Guardar cambios', exact=True).click()
        expect(reader.locator('#tabla-region')).to_contain_text('No hay registros que coincidan')
        expect(reader.locator('#filter-q')).to_have_value(stamp)
        reader.evaluate('window.observedSockets.at(-1).close()')
        expect(reader.locator('#realtime-status')).to_have_attribute('data-state', 'disconnected', timeout=800)
        print('Browser: WebSocket changes A only, no reload, active filters and disconnection status passed.')

        admin.goto(BASE + '/gestion/metas/crear/')
        expect(admin.locator('#record-modal')).to_be_visible()
        admin.locator('[name=nombre]').fill('Valor conservado de prueba')
        admin.locator('#record-form').evaluate('(form) => { form.noValidate = true; }')
        admin.get_by_role('button', name='Crear registro', exact=True).click()
        expect(admin.locator('.error-summary')).to_be_visible()
        expect(admin.locator('[name=nombre]')).to_have_value('Valor conservado de prueba')
        for _ in range(15):
            admin.keyboard.press('Tab')
            assert admin.locator('#record-modal').evaluate('(modal) => modal.contains(document.activeElement)')
        admin.get_by_role('link', name='Cancelar', exact=True).click()
        expect(admin.locator('#page-title')).to_have_text('Ítems y Metas')
        admin.goto(BASE + '/gestion/metas/')
        target = admin.locator('.archive-form').first
        archive_url = target.get_attribute('action')
        writes = []
        admin.on('request', lambda req: writes.append(req.url) if req.method == 'POST' and '/archivar/' in req.url else None)
        target.locator('button').click()
        admin.get_by_role('button', name='Cancelar', exact=True).press('Enter')
        assert writes == []
        assert admin.request.get(BASE + archive_url.replace('/archivar/', '/')).status == 200
        print('Browser: invalid ModelForm stays in modal; cancelling SweetAlert sends no archive request.')

        # List state survives navigation using visible menu links.
        admin.locator('#filter-q').fill('meta territorial')
        admin.locator('#filter-tamano').select_option('5')
        admin.get_by_role('button', name='Aplicar filtros').click()
        admin.get_by_role('link', name='Página 2', exact=True).click()
        admin.locator('.module-nav').get_by_role('link', name='Atenciones ciudadanas', exact=True).click()
        admin.locator('.module-nav').get_by_role('link', name='Ítems y metas', exact=True).click()
        expect(admin.locator('#filter-q')).to_have_value('meta territorial')
        expect(admin.locator('[aria-current=page].page-link')).to_have_text('2')
        for width in [375, 768, 1280]:
            admin.set_viewport_size({'width': width, 'height': 900})
            assert admin.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), width
            screenshot(admin, f'metas-{width}.png')
        print('Browser: per-module session restored; layouts 375/768/1280 have no page overflow.')

        one, two = pages['cliente_1'], pages['cliente_2']
        one.goto(BASE + '/portal/')
        two.goto(BASE + '/portal/')
        foreign_url = two.locator('.record-key').first.get_attribute('href')
        own_url = one.locator('.record-key').first.get_attribute('href')
        assert own_url != foreign_url
        assert one.request.get(BASE + foreign_url).status == 404
        assert one.request.get(BASE + own_url).status == 200
        assert one.request.get(BASE + '/gestion/atenciones/').status == 403
        assert two.request.get(BASE + own_url).status == 404
        screenshot(one, 'portal-cliente-1.png')
        print('Browser: both client portals differ; foreign detail and administration rejected.')

        one.goto(BASE + '/cuentas/perfil/')
        source = Image.new('RGB', (640, 480), (30, 30, 230))
        ImageDraw.Draw(source).rectangle((0, 0, 319, 479), fill=(230, 30, 30))
        raw = BytesIO()
        source.save(raw, 'PNG')
        one.locator('[name=foto]').set_input_files({'name': 'recorte.png', 'mimeType': 'image/png', 'buffer': raw.getvalue()})
        expect(one.locator('#crop-apply')).to_be_enabled()
        expect(one.locator('[data-crop-move], [data-crop-scale]')).to_have_count(0)
        shrink_and_move_crop_left(one)
        one.locator('#crop-apply').click()
        expect(one.locator('#crop-preview-panel')).to_be_visible()
        one.locator('#profile-save').click()
        expect(one.locator('#current-photo')).to_be_visible()
        photo_url = one.locator('#current-photo').get_attribute('src')
        saved = one.request.get(BASE + photo_url).body()
        persisted = Image.open(BytesIO(saved))
        assert persisted.width == persisted.height and persisted.width < 320
        assert persisted.convert('RGB').getextrema() == ((230, 230), (30, 30), (30, 30))
        one.reload()
        assert one.request.get(BASE + photo_url).body() == saved
        one.locator('[name=foto]').set_input_files({'name': 'cancelar.png', 'mimeType': 'image/png', 'buffer': raw.getvalue()})
        expect(one.locator('#crop-cancel')).to_be_visible()
        one.locator('#crop-cancel').click()
        one.locator('#profile-save').click()
        assert one.request.get(BASE + photo_url).body() == saved
        assert two.request.get(BASE + photo_url).status == 404
        screenshot(one, 'perfil-recorte-persistente.png')
        print('Browser: recognizable crop saved as real pixels, persists after reload; cancel and photo ownership passed.')

        # Actual SMTP delivery to the local test mailbox; no console email backend.
        one.get_by_role('button', name='Cerrar sesión', exact=True).click()
        one.goto(BASE + '/cuentas/recuperar/')
        one.locator('[name=email]').fill('cliente_1@example.test')
        one.locator('form button[type=submit]').click()
        reset_url = None
        for _ in range(20):
            mailbox = read_mail('/api/v1/messages')
            messages = mailbox.get('messages', [])
            for message in messages:
                body = read_mail('/api/v1/message/' + message['ID'])
                if 'cliente_1@example.test' not in json.dumps(body.get('To', [])):
                    continue
                match = re.search(r'https?://[^\s<>]+/cuentas/recuperar/[^\s<>]+', body.get('Text', ''))
                if match:
                    reset_url = match.group(0)
                    break
            if reset_url:
                break
            time.sleep(0.1)
        assert reset_url, 'No se recibió el correo SMTP en Mailpit.'
        new_password = secrets.token_urlsafe(20)
        one.goto(reset_url)
        one.locator('[name=new_password1]').fill(new_password)
        one.locator('[name=new_password2]').fill(new_password)
        one.get_by_role('button', name='Guardar contraseña', exact=True).click()
        one.goto(BASE + '/cuentas/login/')
        one.locator('[name=username]').fill('cliente_1')
        one.locator('[name=password]').fill(ACCOUNTS['cliente_1']['password'])
        one.get_by_role('button', name='Ingresar', exact=True).click()
        expect(one.locator('.alert-danger')).to_be_visible()
        login(one, 'cliente_1', new_password)
        one.goto(reset_url)
        expect(one.locator('[name=new_password1]')).to_have_count(0)
        # Restore the private test credential through the real current-password flow.
        one.goto(BASE + '/cuentas/clave/')
        one.locator('[name=old_password]').fill(new_password)
        one.locator('[name=new_password1]').fill(ACCOUNTS['cliente_1']['password'])
        one.locator('[name=new_password2]').fill(ACCOUNTS['cliente_1']['password'])
        one.locator('form button[type=submit]').last.click()
        expect(one).to_have_url(re.compile('/cuentas/clave/lista/'))
        one.get_by_role('button', name='Cerrar sesión', exact=True).click()
        one.goto(BASE + '/portal/')
        expect(one).to_have_url(re.compile('/cuentas/login/'))
        print('Browser: SMTP recovery, old-password rejection, single-use token, current-password change and logout passed.')
        browser.close()


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        text = str(error)
        for account in ACCOUNTS.values():
            text = text.replace(account['password'], '[private]')
        text = re.sub(r'(/cuentas/recuperar/)[^\s/]+/[^\s/]+', r'\1[private-token]', text)
        sys.exit('Browser check failed: ' + text)
