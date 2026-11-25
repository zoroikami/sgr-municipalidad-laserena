"""Barrido GET de rutas visibles, geometría y errores; resultados siempre privados."""
import json
from collections import deque
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

WIDTHS = (375, 768, 1280, 1600)
AUDIT_JS = r'''() => {
  const shown = el => {const s=getComputedStyle(el), r=el.getBoundingClientRect(); return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0;};
  const selector = el => el.id ? '#'+el.id : el.tagName.toLowerCase()+'.'+[...el.classList].slice(0,3).join('.');
  const overflow=[];
  for (const el of document.querySelectorAll('h1,h2,h3,button,.btn,.badge-status,.tubo-funcionario,input,select,textarea')) {
    if (!shown(el) || el.closest('.table-responsive,.module-nav,.visually-hidden') || el.type==='hidden') continue;
    const r=el.getBoundingClientRect();
    const p=el.closest('.tubo-tarjeta,.form-field,.module-preview,.content-panel,.page-heading,.form-actions,.modal-content,main');
    if (!p) continue;
    const b=p.getBoundingClientRect();
    if (r.right>b.right+2 || r.left<b.left-2) overflow.push({elemento:selector(el),texto:(el.textContent||el.getAttribute('aria-label')||el.name||'').trim().slice(0,100),izquierda:r.left,derecha:r.right,contenedor:{izquierda:b.left,derecha:b.right}});
  }
  const labels=[];
  for(const el of document.querySelectorAll('input,select,textarea')) {
    if (!shown(el) || ['hidden','submit','button'].includes(el.type)) continue;
    if (!el.labels?.length && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')) labels.push({elemento:selector(el),nombre:el.name});
  }
  const clipped=[];
  for(const el of document.querySelectorAll('h1,h2,h3,button,.btn,.tubo-funcionario')) {
    if(!shown(el) || el.closest('.table-responsive,.module-nav'))continue;
    const s=getComputedStyle(el);
    if(el.scrollWidth>el.clientWidth+3 && ['hidden','clip'].includes(s.overflowX) && s.textOverflow!=='ellipsis')clipped.push({elemento:selector(el),texto:el.textContent.trim().slice(0,100),scroll:el.scrollWidth,ancho:el.clientWidth});
  }
  const selected_clipped=[];
  const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
  for(const el of document.querySelectorAll('select:not([multiple])')) {
    if(!shown(el))continue;
    const s=getComputedStyle(el);ctx.font=s.font;
    const text=el.selectedOptions[0]?.textContent.trim()||'';
    const available=el.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)-12;
    if(ctx.measureText(text).width>available+3)selected_clipped.push({elemento:selector(el),texto:text,disponible:available,requerido:ctx.measureText(text).width});
  }
  return {ancho:innerWidth,documento:document.documentElement.scrollWidth,overflow,labels,clipped,
    selected_clipped,
    alertas:[...document.querySelectorAll('.alert-danger,.error-summary')].filter(shown).map(x=>x.textContent.trim()),
    h1:[...document.querySelectorAll('h1')].map(x=>x.textContent.trim()),
    enlaces:[...document.querySelectorAll('.module-nav a,main a')].map(a=>({url:a.href,texto:a.textContent.trim()}))};
}'''


def allowed_link(base, url):
    target, origin = urlsplit(url), urlsplit(base)
    if (target.scheme,target.netloc)!=(origin.scheme,origin.netloc): return False
    if target.fragment or any(s in target.path for s in ['/exportar/','/foto/','/logout/','correo-consulta']): return False
    return True


def canonical_url(url):
    parsed=urlsplit(url)
    params=[(k,v) for k,v in parse_qsl(parsed.query) if v and (k,v) not in [('pagina','1'),('tamano','15'),('orden','-created_at')]]
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(sorted(params)),''))


def audit_site(browser, base, alias, session, output, max_pages=95, initial_paths=None, link_prefixes=None):
    output = Path(output) / alias
    output.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={'width':1280,'height':900}, locale='es-CL', reduced_motion='reduce')
    if session:
        context.add_cookies([{'name':'sessionid','value':session,'url':base}])
    blocked=[]
    def get_only(route):
        if route.request.method not in ('GET','HEAD'):
            blocked.append({'url':route.request.url,'metodo':route.request.method})
            route.abort()
        else: route.continue_()
    context.route('**/*', get_only)
    page=context.new_page()
    page.set_default_timeout(7000)
    results,errors,resources=[],[],[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.on('response',lambda response: resources.append({'url':response.url,'status':response.status,'tipo':response.request.resource_type}) if response.status>=400 else None)
    pending=deque(initial_paths or ['/','/cuentas/perfil/','/cuentas/clave/','/consulta/','/cuentas/recuperar/','/ruta-qa-inexistente/'])
    seen=set()
    modules=set()
    while pending and len(seen)<max_pages:
        relative=pending.popleft()
        url=canonical_url(urljoin(base+'/',relative))
        if url in seen:continue
        seen.add(url)
        start_errors,start_resources=len(errors),len(resources)
        record={'rol':alias,'solicitada':url,'vistas':[]}
        try:
            response=page.goto(url,wait_until='networkidle')
            record.update(status=response.status if response else None,url=page.url,titulo=page.title())
            if urlsplit(page.url).path=='/cuentas/login/' and urlsplit(url).path!='/cuentas/login/' and alias!='anonimo':
                record['sesion_invalida']=True
            for width in WIDTHS:
                page.set_viewport_size({'width':width,'height':900})
                data=page.evaluate(AUDIT_JS)
                # Discover only visible links, and limit repeated record instances per module/action.
                for link in data.pop('enlaces'):
                    if not allowed_link(base,link['url']):continue
                    parts=urlsplit(link['url'])
                    path=parts.path
                    if link_prefixes and not path.startswith(tuple(link_prefixes)):continue
                    if '/gestion/' in path or '/cuentas/usuarios/' in path or any(part.isdigit() for part in path.split('/')):
                        normalized='/'.join('ID' if part.isdigit() else part for part in path.split('/'))
                        key=(normalized,parts.query if not any(part.isdigit() for part in path.split('/')) else '')
                        if key in modules:continue
                        modules.add(key)
                    page_number=dict(parse_qsl(parts.query)).get('pagina')
                    if page_number and page_number not in ('1','2'):continue
                    candidate=canonical_url(link['url'])
                    if candidate not in seen:pending.append(candidate)
                record['vistas'].append(data)
                if width in (375,1280) or data['overflow'] or data['clipped'] or data['documento']>width+2:
                    filename=f'{len(seen):02}-{width}.png'
                    page.screenshot(path=str(output/filename),full_page=True)
                    data['captura']=str(output/filename)
            # Tab movement exercises navigation without submitting any forms.
            if page.locator('#record-modal.show').count():
                focus=[]
                for _ in range(12):
                    page.keyboard.press('Tab')
                    focus.append(page.evaluate('''() => {const e=document.activeElement,r=e.getBoundingClientRect();return {elemento:e.id||e.tagName,texto:(e.textContent||e.name||'').trim().slice(0,80),x:r.x,y:r.y,ancho:r.width,alto:r.height,dentro:!!e.closest('#record-modal')};}'''))
                record['foco_modal']=focus
            record['errores_js']=errors[start_errors:]
            record['recursos_error']=resources[start_resources:]
        except Exception as error:
            record['error']=str(error)
        results.append(record)
        (output/'resultados.json').write_text(json.dumps({'paginas':results,'peticiones_no_get_bloqueadas':blocked,'pendientes':len(pending)},ensure_ascii=False,indent=2))
    context.close()
    return results

# El barrido se ejecuta desde tests_django/test_qa_navegador.py sobre un servidor ASGI y una base
# desechables (SGR_RUN_FULL_QA=1). No se reutilizan sesiones de personas del servidor de desarrollo.
