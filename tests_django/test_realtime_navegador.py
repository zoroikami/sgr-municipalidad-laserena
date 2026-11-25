"""Dos clientes independientes y un servidor ASGI con la BD de pruebas, nunca el puerto 8001."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path

import pytest
from django.conf import settings
from django.db import close_old_connections
from django.test import Client
from django.utils import timezone

from gestion.integrado import titulo_item
from gestion.models import CasoSocial, GestionTubo, ItemMeta


pytestmark = [pytest.mark.django_db(transaction=True),
              pytest.mark.skipif(os.environ.get('SGR_RUN_REALTIME_QA') != '1', reason='QA ASGI optativo: SGR_RUN_REALTIME_QA=1.')]


def test_refresco_real_de_cuatro_modulos_y_caso_con_foco_y_dialogo(mundo):
    from playwright.sync_api import expect, sync_playwright
    from tests_django.test_qa_navegador import isolated_asgi

    user = mundo['users']['editor_a']
    today = timezone.localdate()
    tube = GestionTubo.objects.create(delegacion=mundo['a'], nombre='Gestión inicial de QA',
        solicitante='Persona ficticia', solicitante_telefono='912345678', responsable=user)
    caso = CasoSocial.objects.create(delegacion=mundo['a'], nombre='Prueba caso inicial', responsable=user,
        usuario_telefono='912345678', requiere_visita=True, fecha_programada_visita=today)
    visit = ItemMeta.objects.create(delegacion=mundo['a'], nombre=titulo_item('social', 'VISITA TERRENO'),
        unidad_medida='Visitas', cargo_sgr='social')
    user_id, caso_id, visit_id, item_id = user.pk, caso.pk, visit.pk, mundo['meta_a'].pk
    reader = Client()
    reader.force_login(user)
    writer = Client()
    writer.force_login(user)
    cookie = reader.cookies[settings.SESSION_COOKIE_NAME].value
    output = Path(os.environ.get('SGR_QA_OUTPUT', '.private/websocket-modulos'))
    output.mkdir(parents=True, exist_ok=True)

    def post(path, data):
        # Playwright síncrono mantiene un event loop: el ORM de Django va en su hilo propio.
        close_old_connections()
        try:
            response = writer.post(path, data)
            assert response.status_code == 302, response.context and response.context['form'].errors
        finally:
            close_old_connections()

    def tube_data(name):
        return {'nombre': name, 'origen': 'EXT', 'solicitante': 'Persona ficticia',
                'solicitante_telefono': '912345678', 'responsable': user_id, 'fecha_solicitud': today.isoformat()}

    with isolated_asgi() as base, ThreadPoolExecutor(max_workers=1) as workers, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-CL')
        context.add_init_script("""(() => {
            const NativeSocket = window.WebSocket;
            window.__liveSockets = [];
            window.WebSocket = class extends NativeSocket {
                constructor(...args) { super(...args); window.__liveSockets.push(this); }
            };
        })();""")
        context.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': cookie, 'url': base}])
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/tubo/')
        status = page.locator('[data-realtime-status]')
        expect(status).to_have_attribute('data-state', 'connected')
        original_card = page.locator('.tubo-tarjeta').filter(has_text=tube.codigo)
        note = original_card.locator('[name=observacion]')
        note.fill('Observación que aún estoy escribiendo')
        workers.submit(post, '/gestion/tubo/crear/', tube_data('Gestión nueva en vivo')).result()
        expect(status).to_contain_text('Hay cambios nuevos')
        expect(status.get_by_role('button', name='Actualizar', exact=True)).to_be_visible()
        expect(page.locator('.tubo-tarjeta').filter(has_text='Gestión nueva en vivo')).to_have_count(0)
        expect(note).to_have_value('Observación que aún estoy escribiendo')
        page.get_by_role('heading', name='Tubo de trabajo', exact=True).click()
        expect(page.locator('.tubo-tarjeta').filter(has_text='Gestión nueva en vivo')).to_have_count(1)
        expect(note).to_have_value('Observación que aún estoy escribiendo')
        # El panel nuevo vuelve a enlazar el arrastre una sola vez.
        page.evaluate("""() => {
            window.__dialogs = 0;
            const fire = Swal.fire.bind(Swal);
            Swal.fire = (...args) => { window.__dialogs++; return fire(...args); };
            document.dispatchEvent(new CustomEvent('sgr:content-updated', {detail:{region:document}}));
            document.dispatchEvent(new CustomEvent('sgr:content-updated', {detail:{region:document}}));
        }""")
        original_card.locator('.tubo-codigos').drag_to(
            page.locator('.tubo-columna[data-estado="Pendiente"]'))
        expect(page.get_by_role('dialog')).to_be_visible()
        workers.submit(post, '/gestion/tubo/crear/', tube_data('Gestión durante confirmación')).result()
        expect(status).to_contain_text('Hay cambios nuevos')
        expect(page.locator('.tubo-tarjeta').filter(has_text='Gestión durante confirmación')).to_have_count(0)
        assert page.evaluate('window.__dialogs') == 1
        page.get_by_role('button', name='Cancelar', exact=True).click()
        expect(page.locator('.tubo-tarjeta').filter(has_text='Gestión durante confirmación')).to_have_count(1)

        # Cartas y casos se refrescan con escrituras hechas por otra sesión.
        page.goto(base + '/cartas/tablero/')
        expect(status).to_have_attribute('data-state', 'connected')
        workers.submit(post, '/gestion/cartas/crear/', {
            'fecha': today.isoformat(), 'numero_ingreso': 'QA-WS-1', 'para': 'Delegado',
            'remite': 'Organización ficticia', 'nombre': 'Carta en tiempo real',
            'encargado': user_id, 'estado': 'En proceso',
        }).result()
        expect(page.locator('.tubo-tarjeta').filter(has_text='Carta en tiempo real')).to_have_count(1)

        page.goto(base + '/gestion/casos/?q=Prueba&estado=Abierto&orden=nombre')
        expect(status).to_have_attribute('data-state', 'connected')
        workers.submit(post, '/gestion/casos/crear/', {
            'nombre': 'Prueba caso creado en vivo', 'usuario_telefono': '912345678',
            'responsable': user_id, 'fecha_ingreso': today.isoformat(), 'devoluciones': 0, 'estado': 'Abierto',
        }).result()
        expect(page.locator('#tabla-region')).to_contain_text('Prueba caso creado en vivo')
        expect(page.locator('#filter-q')).to_have_value('Prueba')
        expect(page).to_have_url(base + '/gestion/casos/?q=Prueba&estado=Abierto&orden=nombre')

        period = (today.month - 1) // 3 + 1
        page.goto(base + f'/sgr/?anio={today.year}&trimestre={period}&responsable={user_id}')
        expect(status).to_have_attribute('data-state', 'connected')
        activity = {'item': item_id, 'cargo': 'social', 'fecha': today.isoformat(),
                    'descripcion': 'Actividad visible sin recargar', 'solicitante_nombre': 'Persona ficticia',
                    'solicitante_telefono': '912345678', 'es_accion': 'on'}
        workers.submit(post, '/sgr/actividad/', activity).result()
        expect(page.locator('[data-realtime-panel]')).to_contain_text('Actividad visible sin recargar')
        expect(page.locator('[name=trimestre]')).to_have_value(str(period))

        page.goto(base + f'/gestion/casos/{caso_id}/')
        expect(status).to_have_attribute('data-state', 'connected')
        workers.submit(post, '/sgr/actividad/', {**activity, 'item': visit_id, 'caso': caso_id,
                                               'descripcion': 'Visita vinculada en vivo'}).result()
        expect(page.get_by_role('region', name='Gestiones del caso social')).to_contain_text(visit.nombre)
        register = page.get_by_role('link', name='Registrar gestión', exact=True)
        register.scroll_into_view_if_needed()
        register.evaluate('el => el.focus({preventScroll: true})')
        previous_scroll = page.evaluate('scrollY')
        workers.submit(post, '/sgr/actividad/', {**activity, 'caso': caso_id,
                                               'descripcion': 'Segunda gestión vinculada en vivo'}).result()
        expect(page.get_by_role('region', name='Gestiones del caso social')).to_contain_text('Cobertura A')
        expect(register).to_be_focused()
        assert abs(page.evaluate('scrollY') - previous_scroll) <= 1
        page.evaluate('window.__liveSockets.at(-1).close()')
        expect(status).to_have_attribute('data-state', 'disconnected')
        expect(status).to_have_attribute('data-state', 'connected')
        assert page.evaluate('window.__liveSockets.length') == 2
        for width in (375, 1280):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / f'caso-en-vivo-{width}.png'), full_page=True)
        assert not errors, errors
        browser.close()
