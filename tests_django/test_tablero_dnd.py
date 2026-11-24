"""El arrastre usa las transiciones autorizadas de los formularios del tablero."""
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings

from gestion.models import Carta, GestionTubo, HistorialEstado

pytestmark = pytest.mark.django_db


class BoardCards(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.cards = []
        self.card = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'tubo-tarjeta' in attrs.get('class', '').split():
            self.card = {'attrs': attrs, 'destinations': []}
            self.cards.append(self.card)
        if tag == 'form' and self.card is not None:
            self.card['destinations'].append(attrs.get('data-destino'))

    def handle_endtag(self, tag):
        if tag == 'article':
            self.card = None


def record(mundo, board, state):
    common = dict(delegacion=mundo['a'], nombre='Gestión de arrastre', estado=state)
    if board == 'tubo':
        return GestionTubo.objects.create(**common, solicitante='Vecina de prueba', responsable=mundo['users']['editor_a'])
    return Carta.objects.create(**common, numero_ingreso='OP-DND-1', remite='Organización local', encargado=mundo['users']['editor_a'])


@pytest.mark.parametrize('board,path,state,destinations', [
    ('tubo', '/tubo/', 'Ingresado', ['Pendiente']),
    ('tubo', '/tubo/', 'Pendiente', ['En proceso']),
    ('tubo', '/tubo/', 'En proceso', ['Realizado']),
    ('tubo', '/tubo/', 'Realizado', []),
    ('cartas', '/cartas/tablero/', 'En proceso', ['Aprobada', 'No aplica']),
    ('cartas', '/cartas/tablero/', 'Aprobada', ['Finalizada']),
    ('cartas', '/cartas/tablero/', 'Finalizada', []),
    ('cartas', '/cartas/tablero/', 'No aplica', []),
])
@pytest.mark.parametrize('alias', ['editor_a', 'lector_a'])
def test_arrastre_solo_ofrece_destinos_con_permiso_y_estado(client, mundo, board, path, state, destinations, alias):
    record(mundo, board, state)
    client.force_login(mundo['users'][alias])
    cards = BoardCards(client.get(path).content.decode()).cards
    assert len(cards) == 1
    allowed = destinations if alias == 'editor_a' else []
    assert cards[0]['destinations'] == allowed
    assert (cards[0]['attrs'].get('draggable') == 'true') == bool(allowed)


@pytest.mark.parametrize('board,path,origin,dest', [
    ('tubo', '/tubo/{}/avanzar/', 'Ingresado', 'Pendiente'),
    ('cartas', '/cartas/{}/avanzar/', 'En proceso', 'Aprobada'),
])
def test_post_del_arrastre_conserva_observacion_y_rechaza_reintento(client, mundo, board, path, origin, dest):
    obj = record(mundo, board, origin)
    client.force_login(mundo['users']['editor_a'])
    data = {'desde': origin, 'estado': dest, 'observacion': 'Derivación acordada en la revisión'}
    assert client.post(path.format(obj.pk), data).status_code == 302
    assert client.post(path.format(obj.pk), data).status_code == 302
    obj.refresh_from_db()
    assert obj.estado == dest
    history = HistorialEstado.objects.get()
    assert history.estado_anterior == origin
    assert history.estado_nuevo == dest
    assert history.observacion == data['observacion']
    assert history.autor == mundo['users']['editor_a']


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('board,path,origin,dest,invalid', [
    ('tubo', '/tubo/', 'Ingresado', 'Pendiente', 'Realizado'),
    ('cartas', '/cartas/tablero/', 'En proceso', 'No aplica', 'Finalizada'),
])
def test_arrastre_real_confirmacion_cancelacion_y_responsive(client, mundo, live_server, tmp_path, board, path, origin, dest, invalid):
    playwright = pytest.importorskip('playwright.sync_api')
    expect, sync_playwright = playwright.expect, playwright.sync_playwright

    obj = record(mundo, board, origin)
    client.force_login(mundo['users']['editor_a'])
    errors = []
    with sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Instala Chromium con python -m playwright install chromium para verificar el arrastre real.')
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-CL')
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        assert page.goto(live_server.url + path).status == 200
        card = page.locator('.tubo-tarjeta').filter(has_text=obj.codigo)
        source = page.locator('.tubo-columna').filter(has=card)
        target = page.locator(f'.tubo-columna[data-estado="{dest}"]')
        expect(card).to_have_attribute('draggable', 'true')
        # Invalid columns neither ask for confirmation nor submit a transition.
        card.drag_to(page.locator(f'.tubo-columna[data-estado="{invalid}"]'))
        expect(page.locator('.swal2-popup')).to_have_count(0)
        page.reload()
        expect(page.locator(f'.tubo-columna[data-estado="{origin}"]').locator('.tubo-tarjeta')).to_have_count(1)
        # A cancelled drop leaves state, history and board untouched.
        card.drag_to(target)
        expect(page.get_by_role('dialog')).to_be_visible()
        page.get_by_role('button', name='Cancelar', exact=True).click()
        expect(source.locator('.tubo-tarjeta')).to_have_count(1)
        page.reload()
        expect(page.locator(f'.tubo-columna[data-estado="{origin}"]').locator('.tubo-tarjeta')).to_have_count(1)
        # The existing note is offered and its edited value reaches the real POST.
        form = card.locator(f'form[data-destino="{dest}"]')
        form.locator('[name=observacion]').fill('Nota previa')
        card.drag_to(target)
        expect(page.get_by_role('textbox', name='Observación (opcional)')).to_have_value('Nota previa')
        page.get_by_role('textbox', name='Observación (opcional)').fill('Seguimiento mediante arrastre')
        page.get_by_role('button', name='Mover tarjeta', exact=True).click()
        expect(target.locator('.tubo-tarjeta')).to_have_count(1)
        for width in [375, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(tmp_path / f'{board}-{width}.png'), full_page=True)
        assert not errors, errors
        browser.close()
    obj.refresh_from_db()
    assert obj.estado == dest
    assert HistorialEstado.objects.get().observacion == 'Seguimiento mediante arrastre'


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('board,path,origin,dest,button', [
    ('tubo', '/tubo/', 'En proceso', 'Realizado', 'Realizar'),
    ('cartas', '/cartas/tablero/', 'Aprobada', 'Finalizada', 'Finalizar'),
])
@pytest.mark.parametrize('mode', ['reader', 'no-js', 'no-swal'])
def test_lector_y_botones_sin_dependencias_de_arrastre(client, mundo, live_server, board, path, origin, dest, button, mode):
    playwright = pytest.importorskip('playwright.sync_api')
    expect, sync_playwright = playwright.expect, playwright.sync_playwright

    obj = record(mundo, board, origin)
    client.force_login(mundo['users']['lector_a' if mode == 'reader' else 'editor_a'])
    with sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Instala Chromium con python -m playwright install chromium para verificar el arrastre real.')
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 375, 'height': 900}, java_script_enabled=mode != 'no-js')
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
        page = context.new_page()
        if mode == 'no-swal':
            page.route('**/sweetalert2-*.js', lambda route: route.abort())
        assert page.goto(live_server.url + path).status == 200
        card = page.locator('.tubo-tarjeta').filter(has_text=obj.codigo)
        if mode == 'reader':
            expect(card.locator('form')).to_have_count(0)
            expect(page.locator('[draggable="true"]')).to_have_count(0)
        else:
            if mode == 'no-swal':
                expect(page.locator('[draggable="true"]')).to_have_count(0)
            card.locator('[name=observacion]').fill('Cierre desde el botón')
            card.get_by_role('button', name=button, exact=True).click()
            expect(page.locator(f'.tubo-columna[data-estado="{dest}"]').locator('.tubo-tarjeta')).to_have_count(1)
            # Terminal cards offer neither movement forms nor native dragging.
            expect(card.locator('form')).to_have_count(0)
            expect(card).not_to_have_attribute('draggable', 'true')
        browser.close()
    obj.refresh_from_db()
    assert obj.estado == (origin if mode == 'reader' else dest)
    if mode == 'reader':
        assert not HistorialEstado.objects.exists()
    else:
        assert HistorialEstado.objects.get().observacion == 'Cierre desde el botón'
