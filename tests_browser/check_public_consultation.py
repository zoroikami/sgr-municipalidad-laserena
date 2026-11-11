"""Local SMTP → Mailpit → anonymous browser journey, with a disposable attention."""
from pathlib import Path
import json
import os
import re
import sys
from urllib.parse import quote, urlsplit
from urllib.request import urlopen
import uuid

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGR_BASE_URL', 'http://127.0.0.1:8001')
MAILPIT = os.environ.get('SGR_MAILPIT_URL', 'http://127.0.0.1:8025')
OUTPUT = ROOT / 'output/browser/consulta-ciudadana'


def read_mail(recipient):
    with urlopen(MAILPIT + '/api/v1/messages', timeout=5) as response:
        messages = json.load(response)['messages']
    selected = next(message for message in messages if recipient in json.dumps(message.get('To', [])))
    with urlopen(MAILPIT + '/api/v1/message/' + selected['ID'], timeout=5) as response:
        body = json.load(response)['Text']
    folio = re.search(r'Folio: (ATN-[0-9-]+)', body).group(1)
    code = re.search(r'Código privado: ([A-Z2-9-]+)', body).group(1)
    assert BASE + '/consulta/' in body
    return folio, code


def query(page, folio, code):
    page.goto(BASE + '/consulta/')
    page.locator('[name=folio]').fill(folio)
    page.locator('[name=codigo]').fill(code)
    page.get_by_role('button', name='Consultar atención', exact=True).click()


def run():
    if urlsplit(BASE).hostname not in ['localhost', '127.0.0.1']:
        raise RuntimeError('Este recorrido crea una atención temporal y solo se ejecuta en local con Mailpit.')
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from gestion.models import Atencion

    marker = 'Prueba consulta ' + uuid.uuid4().hex[:10]
    recipient = 'consulta-' + uuid.uuid4().hex + '@example.test'
    credentials = json.loads((ROOT / '.private/cuentas-demo.json').read_text())
    employee = next(account for account in credentials if account['usuario'] == 'editor_a')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            staff = browser.new_context(viewport={'width': 1280, 'height': 1000}).new_page()
            citizen = browser.new_context(viewport={'width': 1280, 'height': 1000}, locale='es-CL').new_page()
            errors = []
            citizen.on('pageerror', lambda error: errors.append(str(error)))
            citizen.goto(BASE + '/')
            expect(citizen.get_by_role('heading', name='Consultar mi atención')).to_be_visible()
            for width in [320, 375, 768, 1280]:
                citizen.set_viewport_size({'width': width, 'height': 1000})
                assert citizen.evaluate('document.documentElement.scrollWidth <= innerWidth')
                citizen.screenshot(path=str(OUTPUT / f'entrada-{width}.png'), full_page=True)
            citizen.get_by_role('link', name='Ingreso de funcionarios', exact=True).click()
            expect(citizen).to_have_url(BASE + '/cuentas/login/')

            staff.goto(BASE + '/cuentas/login/')
            staff.locator('[name=username]').fill(employee['usuario'])
            staff.locator('[name=password]').fill(employee['password'])
            staff.locator('[name=password]').press('Enter')
            staff.wait_for_url(BASE + '/')
            staff.goto(BASE + '/gestion/atenciones/crear/')
            staff.locator('[name=solicitante_nombre]').fill(marker)
            staff.locator('[name=solicitante_rut]').fill('12345678-5')
            staff.locator('[name=solicitante_email]').fill(recipient)
            staff.locator('[name=tipo]').select_option(index=1)
            expect(staff.locator('[name=subatencion]')).to_be_enabled()
            staff.locator('[name=subatencion]').select_option(index=1)
            staff.locator('[name=descripcion]').fill('Antecedentes privados que no deben aparecer en la consulta pública.')
            staff.get_by_role('button', name='Crear registro', exact=True).click()
            staff.wait_for_url(BASE + '/gestion/atenciones/')
            expect(staff.locator('.messages')).to_contain_text('Enviamos el folio y el código privado')
            folio, code = read_mail(recipient)
            query(citizen, folio, code)
            expect(citizen.locator('.citizen-result-heading .badge-status')).to_have_text('Ingresada')
            body = citizen.locator('body').inner_text()
            assert marker not in body and recipient not in body and 'Antecedentes privados' not in body
            citizen.screenshot(path=str(OUTPUT / 'estado-consultado.png'), full_page=True)

            staff.goto(BASE + '/gestion/atenciones/?q=' + quote(marker))
            staff.locator('.record-key').first.click()
            staff.get_by_role('button', name='Enviar nuevo código').click()
            expect(staff.locator('.messages')).to_contain_text('Enviamos el folio y el código privado')
            same_folio, renewed = read_mail(recipient)
            assert folio == same_folio and code != renewed
            query(citizen, folio, code)
            expect(citizen.get_by_role('alert')).to_contain_text('No pudimos consultar la atención')
            query(citizen, folio, renewed)
            expect(citizen.locator('.citizen-result-heading .badge-status')).to_have_text('Ingresada')
            assert not errors, errors
            browser.close()
    finally:
        Atencion.all_objects.filter(solicitante_nombre=marker, solicitante_email=recipient).delete()
    print('Consulta pública: registro → SMTP/Mailpit → folio+código sin sesión, datos mínimos, renovación y diseño a 4 anchos verificados. Atención temporal eliminada.')


if __name__ == '__main__':
    run()
