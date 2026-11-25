"""QA de navegador sobre ASGI y BD desechable. No utiliza el servidor 8001."""
from contextlib import contextmanager
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from urllib.parse import urlsplit,urlunsplit

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from PIL import Image

from cuentas.models import Perfil
from gestion.models import ActividadSGR, Carta, GestionTubo, Organizacion
from tests_browser.qa_completo import audit_site

pytestmark=[pytest.mark.django_db(transaction=True),pytest.mark.skipif(os.environ.get('SGR_RUN_FULL_QA')!='1',reason='QA completo optativo: SGR_RUN_FULL_QA=1.')]
OUTPUT=Path(os.environ.get('SGR_QA_OUTPUT',str(Path(__file__).resolve().parents[1]/'.private/qa-completo/aislado')))


@contextmanager
def isolated_asgi():
    # pytest already selected its disposable schema; share that schema with Daphne.
    if not settings.DATABASES['default']['NAME'].startswith('test_'):
        raise RuntimeError('Este QA requiere una base de pruebas test_.')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    env=os.environ.copy()
    env.update(DB_NAME=settings.DATABASES['default']['NAME'],DJANGO_SETTINGS_MODULE='config.test_settings')
    redis=urlsplit(env.get('REDIS_URL','redis://127.0.0.1:6380/0'))
    env['REDIS_URL']=urlunsplit((redis.scheme,redis.netloc,'/12',redis.query,redis.fragment))
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sgr-qa-asgi-') as temp, (OUTPUT/'servidor.log').open('a') as log:
        Path(temp,'qa_asgi.py').write_text('from config.asgi import application as app\nfrom django.contrib.staticfiles.handlers import ASGIStaticFilesHandler\napplication = ASGIStaticFilesHandler(app)\n')
        Path(temp,'qa_settings.py').write_text(f'from config.test_settings import *\nMEDIA_ROOT = {str(Path(temp,"media"))!r}\nROOT_URLCONF = "qa_urls"\n')
        Path(temp,'qa_urls.py').write_text('from config.urls import *\nfrom django.core.exceptions import SuspiciousOperation\ndef qa500(request):\n    raise RuntimeError("QA 500 controlado")\ndef qa400(request):\n    raise SuspiciousOperation("QA 400 controlado")\nurlpatterns = [path("qa/500/", qa500), path("qa/400/", qa400)] + urlpatterns\n')
        env['DJANGO_SETTINGS_MODULE']='qa_settings'
        env['PYTHONPATH']=os.pathsep.join([temp,str(Path(__file__).resolve().parents[1]),env.get('PYTHONPATH','')])
        process=subprocess.Popen([sys.executable,'-m','daphne','-b','127.0.0.1','-p',str(port),'qa_asgi:application'],cwd=Path(__file__).resolve().parents[1],env=env,stdout=log,stderr=log)
        base=f'http://127.0.0.1:{port}'
        try:
            deadline=time.monotonic()+12
            while True:
                if process.poll() is not None:raise RuntimeError('Daphne terminó antes de iniciar; revisar servidor.log.')
                try:
                    with urlopen(base+'/api/health/',timeout=.5) as r:
                        if r.status==200:break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.1)
            yield base
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)


def data(mundo):
    sa=get_user_model().objects.create_superuser('qa_superadmin','qa-admin@example.test','PruebaAislada#2026')
    Perfil.objects.create(user=sa,rut='11111111-1')
    mundo['users']['qa_superadmin']=sa
    editor=mundo['users']['editor_a']
    profile=editor.perfil
    profile.cargo_sgr='servicios';profile.save()
    for index in range(4):
        Organizacion.objects.create(delegacion=mundo['a'],nombre=f'Organización ficticia {index}: acompañamiento y participación vecinal en actividades de servicios comunitarios',familia='funcional',subfamilia='Centro cultural')
        Carta.objects.create(delegacion=mundo['a'],nombre=f'Carta ficticia de verificación {index}',numero_ingreso=f'QA-{index}',remite='Organización ficticia',encargado=editor,estado=['En proceso','Aprobada','Finalizada','No aplica'][index])
        GestionTubo.objects.create(delegacion=mundo['a'],nombre=f'Gestión de prueba {index}',solicitante='Vecina ficticia',solicitante_telefono='912345678',responsable=editor,estado=['Ingresado','Pendiente','En proceso','Realizado'][index])
    ActividadSGR.objects.create(delegacion=mundo['a'],responsable=editor,item=mundo['meta_a'],cargo='servicios',fecha=timezone.localdate(),descripcion='Acción de verificación',solicitante_nombre='Vecina ficticia',solicitante_telefono='912345678')


def test_qa_lectores_coordinador_y_superadmin(client,mundo):
    from playwright.sync_api import sync_playwright
    data(mundo)
    cookies={}
    aliases=os.environ.get('SGR_QA_ROLES','lector_a,lector_b,coordinador,qa_superadmin').split(',')
    for alias in aliases:
        account_client=Client()
        account_client.force_login(mundo['users'][alias])
        cookies[alias]=account_client.cookies[settings.SESSION_COOKIE_NAME].value
    all_records=[]
    with isolated_asgi() as base, sync_playwright() as p:
        browser=p.chromium.launch()
        for alias,cookie in cookies.items():
            records=audit_site(browser,base,alias,cookie,OUTPUT)
            all_records.extend(records)
            print(alias,len(records),'páginas',flush=True)
        browser.close()
    (OUTPUT/'resumen.json').write_text(json.dumps(all_records,ensure_ascii=False,indent=2))
    # The JSON is the diagnostic artifact; app findings must not stop other routes.
    assert all_records
    assert not any(record.get('sesion_invalida') for record in all_records)


def test_usuarios_cargo_municipal_375(client,mundo):
    from playwright.sync_api import expect,sync_playwright
    data(mundo)
    client.force_login(mundo['users']['qa_superadmin'])
    cookie=client.cookies[settings.SESSION_COOKIE_NAME].value
    with isolated_asgi() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':375,'height':900},locale='es-CL')
        context.add_cookies([{'name':'sessionid','value':cookie,'url':base}])
        page=context.new_page();page.goto(base+'/cuentas/usuarios/')
        expect(page.get_by_role('columnheader',name='Cargo municipal')).to_be_visible()
        expect(page.get_by_role('cell',name='Coordinador de servicios comunitarios')).to_be_visible()
        table=page.locator('.table-responsive')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert table.evaluate('(e)=>e.scrollWidth>e.clientWidth')
        table.evaluate('(e)=>e.scrollLeft=e.scrollWidth')
        assert table.evaluate('(e)=>e.scrollLeft>0')
        page.screenshot(path=str(OUTPUT/'usuarios-cargo-375-derecha.png'),full_page=True)
        table.evaluate('(e)=>e.scrollLeft=0')
        page.screenshot(path=str(OUTPUT/'usuarios-cargo-375-inicio.png'),full_page=True)
        browser.close()


def cookie_for(user):
    account=Client();account.force_login(user)
    return account.cookies[settings.SESSION_COOKIE_NAME].value


def page_for(browser,base,cookie,width=1280):
    context=browser.new_context(viewport={'width':width,'height':900},locale='es-CL')
    context.add_cookies([{'name':'sessionid','value':cookie,'url':base}])
    return context.new_page()


def native_drag(page,card,column):
    # Keep the native drag active while scrolling to a column in another grid row.
    card.locator('.tubo-codigos').scroll_into_view_if_needed()
    source=card.locator('.tubo-codigos').bounding_box()
    x,y=source['x']+10,source['y']+8
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+12,y+8,steps=3)
    heading=column.locator('h2').first
    heading.scroll_into_view_if_needed()
    target=heading.bounding_box()
    page.mouse.move(target['x']+20,target['y']+10,steps=12)
    page.mouse.up()


def test_flujos_escritura_tubo_y_cartas(mundo):
    from playwright.sync_api import expect,sync_playwright
    data(mundo)
    employee=cookie_for(mundo['users']['editor_a'])
    admin=cookie_for(mundo['users']['admin_a'])
    today=timezone.localdate().isoformat()
    with isolated_asgi() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=page_for(browser,base,employee)
        page.goto(base+'/gestion/tubo/crear/')
        page.locator('[name=nombre]').fill('QA solicitud creada y editada')
        page.locator('[name=solicitante]').fill('Vecina de verificación')
        page.locator('[name=responsable]').select_option(str(mundo['users']['editor_a'].pk))
        page.locator('[name=solicitante_rut]').fill(mundo['users']['admin_a'].perfil.rut)
        expect(page.locator('.rut-aviso')).to_contain_text('otra gestión')
        page.get_by_role('button',name='Crear registro',exact=True).click()
        expect(page.locator('[name=solicitante_telefono]')).to_be_focused()
        page.locator('[name=solicitante_telefono]').fill('912345678')
        page.get_by_role('button',name='Crear registro',exact=True).click()
        page.wait_for_url(base+'/gestion/tubo/')
        row=page.locator('tbody tr').filter(has_text='QA solicitud creada y editada')
        code=row.locator('.record-key').inner_text()
        detail=row.locator('.record-key').get_attribute('href')
        row.locator('a[aria-label^="Editar "]').click()
        page.locator('[name=nombre]').fill('QA solicitud editada')
        page.get_by_role('button',name='Guardar cambios',exact=True).click()
        page.wait_for_url(base+'/gestion/tubo/')
        page.goto(base+'/tubo/')
        card=page.locator('.tubo-tarjeta').filter(has_text=code)
        expect(card).to_contain_text('Funcionario · Delegado')
        for destination in ['Pendiente','En proceso','Realizado']:
            card.drag_to(page.locator(f'.tubo-columna[data-estado="{destination}"]'),source_position={'x':10,'y':10})
            dialog=page.get_by_role('dialog')
            expect(dialog).to_be_visible()
            dialog.get_by_role('textbox').fill('Seguimiento QA')
            dialog.get_by_role('button',name='Mover tarjeta',exact=True).click()
            expect(page.locator(f'.tubo-columna[data-estado="{destination}"]').locator('.tubo-tarjeta').filter(has_text=code)).to_have_count(1)
        page.goto(base+detail)
        expect(page.locator('[aria-label="Historial de cambios de estado"] tbody tr')).to_have_count(3)
        admin_page=page_for(browser,base,admin)
        admin_page.goto(base+detail)
        writes=[]
        admin_page.on('request',lambda r:writes.append(r.url) if r.method=='POST' and '/archivar/' in r.url else None)
        admin_page.get_by_role('button',name='Archivar registro',exact=True).click()
        admin_page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click()
        assert not writes
        admin_page.get_by_role('button',name='Archivar registro',exact=True).click()
        admin_page.get_by_role('dialog').get_by_role('button',name='Archivar registro',exact=True).click()
        admin_page.wait_for_url(base+'/gestion/tubo/')
        assert len(writes)==1
        page.goto(base+'/gestion/cartas/crear/')
        for field,value in [('numero_ingreso','QA-CARTA-1'),('remite','Organización ficticia'),('nombre','QA carta creada'),('fecha_actividad',today)]:
            page.locator(f'[name={field}]').fill(value)
        page.locator('[name=encargado]').select_option(str(mundo['users']['editor_a'].pk))
        page.get_by_role('button',name='Crear registro',exact=True).click()
        page.wait_for_url(base+'/gestion/cartas/')
        row=page.locator('tbody tr').filter(has_text='QA carta creada')
        letter=row.locator('.record-key').inner_text()
        page.goto(base+'/cartas/tablero/')
        card=page.locator('.tubo-tarjeta').filter(has_text=letter)
        for destination in ['Aprobada','Finalizada']:
            native_drag(page,card,page.locator(f'.tubo-columna[data-estado="{destination}"]'))
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('dialog').get_by_role('button',name='Mover tarjeta',exact=True).click()
            expect(page.locator(f'.tubo-columna[data-estado="{destination}"]').locator('.tubo-tarjeta').filter(has_text=letter)).to_have_count(1)
        page.screenshot(path=str(OUTPUT/'flujo-cartas-finalizada.png'),full_page=True)
        browser.close()
    assert GestionTubo.all_objects.get(nombre='QA solicitud editada').deleted_at is not None
    assert Carta.objects.get(nombre='QA carta creada').estado=='Finalizada'


def test_flujos_escritura_atenciones_portal_y_consulta(mundo):
    from playwright.sync_api import expect,sync_playwright
    from gestion.consulta import code_digest
    data(mundo)
    employee=cookie_for(mundo['users']['editor_a'])
    citizen=cookie_for(mundo['users']['cliente_1'])
    record=mundo['atn_a'];code='ABCD-EFGH-JKLM-NPQR-STUV'
    record.solicitante_email='consulta-qa@example.test'
    record.consulta_codigo_hash=code_digest(record.pk,record.solicitante_email,code)
    record.consulta_enviado_at=timezone.now()
    record.save(update_fields=['solicitante_email','consulta_codigo_hash','consulta_enviado_at'])
    with isolated_asgi() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=page_for(browser,base,employee)
        page.goto(base+'/gestion/atenciones/crear/')
        page.locator('[name=solicitante_nombre]').fill('QA Atención de prueba')
        page.locator('[name=solicitante_rut]').fill('12345678-5')
        page.locator('[name=tipo]').select_option(str(mundo['tipo_a'].pk))
        expect(page.locator('[name=subatencion]')).to_be_enabled()
        page.locator('[name=subatencion]').select_option(str(mundo['sub_a'].pk))
        page.locator('[name=cliente]').select_option(str(mundo['users']['cliente_1'].pk))
        page.locator('[name=descripcion]').fill('Antecedentes ficticios de prueba')
        page.get_by_role('button',name='Crear registro',exact=True).click()
        page.wait_for_url(base+'/gestion/atenciones/')
        expect(page.locator('tbody')).to_contain_text('QA Atención de prueba')
        portal=page_for(browser,base,citizen,375)
        portal.goto(base+'/portal/')
        expect(portal.locator('tbody')).to_contain_text('QA Atención de prueba')
        assert portal.evaluate('document.documentElement.scrollWidth<=innerWidth')
        public=browser.new_page(viewport={'width':375,'height':900},locale='es-CL')
        public.goto(base+'/consulta/')
        public.locator('[name=folio]').fill(record.folio)
        public.locator('[name=codigo]').fill(code)
        public.get_by_role('button',name='Consultar atención',exact=True).click()
        expect(public.locator('.citizen-result-heading .badge-status')).to_have_text('Ingresada')
        body=public.locator('body').inner_text()
        for private in [record.solicitante_nombre,record.solicitante_rut,record.solicitante_email,record.descripcion]:
            assert private not in body
        public.screenshot(path=str(OUTPUT/'consulta-publica-resultado-375.png'),full_page=True)
        public.goto(base+'/consulta/')
        public.locator('[name=folio]').fill(record.folio)
        public.locator('[name=codigo]').fill('ZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZ')
        public.get_by_role('button',name='Consultar atención',exact=True).click()
        expect(public.get_by_role('alert')).to_contain_text('No pudimos consultar la atención')
        browser.close()


def test_flujos_escritura_foto_persistente(mundo):
    from playwright.sync_api import expect,sync_playwright
    from tests_browser.check_crop import shrink_and_move_crop_left
    data(mundo)
    citizen=cookie_for(mundo['users']['cliente_1'])
    other=cookie_for(mundo['users']['cliente_2'])
    from PIL import ImageDraw
    source=Image.new('RGB',(640,480),(30,30,230))
    ImageDraw.Draw(source).rectangle((0,0,319,479),fill=(230,30,30))
    raw=BytesIO();source.save(raw,'PNG')
    with isolated_asgi() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=page_for(browser,base,citizen,375)
        page.goto(base+'/cuentas/perfil/')
        page.locator('[name=foto]').set_input_files({'name':'qa-foto.png','mimeType':'image/png','buffer':raw.getvalue()})
        expect(page.locator('#crop-apply')).to_be_enabled()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#crop-panel .croppr-image').scroll_into_view_if_needed()
        initial_width=page.locator('#crop-panel .croppr-region').bounding_box()['width']
        shrink_and_move_crop_left(page)
        assert page.locator('#crop-panel .croppr-region').bounding_box()['width']<initial_width
        page.locator('#crop-apply').click()
        expect(page.locator('#crop-preview-panel')).to_be_visible()
        page.locator('#profile-save').click()
        expect(page.locator('#current-photo')).to_be_visible()
        photo=page.locator('#current-photo').get_attribute('src')
        saved=page.request.get(base+photo).body()
        result=Image.open(BytesIO(saved))
        assert result.width==result.height and result.width<320
        page.reload()
        assert page.request.get(base+photo).body()==saved
        page.locator('[name=foto]').set_input_files({'name':'qa-cancelar.png','mimeType':'image/png','buffer':raw.getvalue()})
        expect(page.locator('#crop-cancel')).to_be_visible()
        page.locator('#crop-cancel').click()
        page.locator('#profile-save').click()
        expect(page.locator('#current-photo')).to_be_visible()
        assert page.request.get(base+photo).body()==saved
        stranger=page_for(browser,base,other)
        assert stranger.request.get(base+photo).status==404
        page.screenshot(path=str(OUTPUT/'foto-persistente-375.png'),full_page=True)
        browser.close()


def test_paginas_error_y_descarga_excel(mundo):
    from playwright.sync_api import expect,sync_playwright
    data(mundo)
    citizen=cookie_for(mundo['users']['cliente_1'])
    admin=cookie_for(mundo['users']['qa_superadmin'])
    with isolated_asgi() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        rows=audit_site(browser,base,'errores_controlados',citizen,OUTPUT,
            initial_paths=['/qa/400/','/gestion/atenciones/','/ruta-no-existente/','/qa/500/'],link_prefixes=['/sin-enlaces/'])
        assert [row['status'] for row in rows]==[400,403,404,500]
        assert not [v for row in rows for v in row['vistas'] if v['overflow'] or v['clipped'] or v['documento']>v['ancho']]
        page=page_for(browser,base,admin)
        page.goto(base+'/gestion/tubo/')
        with page.expect_download() as downloading:
            page.get_by_role('link',name='Exportar Excel',exact=True).click()
        download=downloading.value
        assert download.suggested_filename.endswith('.xlsx')
        target=OUTPUT/'exportacion-tubo-ficticio.xlsx'
        download.save_as(target)
        assert target.stat().st_size>1000
        browser.close()
