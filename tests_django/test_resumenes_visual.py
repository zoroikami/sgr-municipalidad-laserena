"""Resumen compacto compartido: sin desbordes, contraste suficiente en cada tono y apilado en pantallas angostas."""
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from gestion.models import Carta, GestionTubo

pytestmark = pytest.mark.django_db(transaction=True)

CONTRASTE = """() => {
  const canal = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const rgb = color => {
    const ctx = document.createElement('canvas').getContext('2d');
    ctx.fillStyle = color; ctx.fillRect(0, 0, 1, 1);
    return Array.from(ctx.getImageData(0, 0, 1, 1).data).slice(0, 3);
  };
  const luz = color => { const [r, g, b] = rgb(color).map(canal); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const fondo = elemento => {
    for (let e = elemento; e; e = e.parentElement) {
      const c = getComputedStyle(e).backgroundColor;
      if (c && c !== 'transparent' && !/,\\s*0\\)$/.test(c)) return c;
    }
    return 'rgb(255, 255, 255)';
  };
  return [...document.querySelectorAll('.resumen-compacto article[data-tono] strong')].map(e => {
    const a = luz(getComputedStyle(e).color), b = luz(fondo(e));
    return [e.closest('article').dataset.tono, (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)];
  });
}"""


def test_resumen_compacto_se_lee_y_no_desborda(client, mundo, live_server):
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    a, editor = mundo['a'], mundo['users']['editor_a']
    for numero, estado in enumerate(['Ingresado', 'Pendiente', 'En proceso', 'Realizado']):
        GestionTubo.objects.create(delegacion=a, nombre=f'Gestión {numero}', solicitante='Vecina', estado=estado,
                                   solicitante_telefono='912345678', responsable=editor)
    for numero, estado in enumerate(['En proceso', 'Aprobada', 'Finalizada', 'No aplica']):
        Carta.objects.create(delegacion=a, nombre=f'Carta {numero}', numero_ingreso=f'OP-{numero}', remite='Junta',
                             encargado=editor, estado=estado)
    client.force_login(mundo['users']['admin_a'])
    hoy = timezone.localdate()
    paginas = [reverse('gestion:tablero'), reverse('gestion:cartas_tablero'), reverse('gestion:listado', args=['cartas']),
               f"{reverse('gestion:resultados_sgr')}?anio={hoy.year}&trimestre={(hoy.month - 1) // 3 + 1}"
               f"&responsable={editor.pk}", reverse('gestion:inicio')]
    tonos_vistos = set()
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        for ancho in (375, 768, 1280):
            context = browser.new_context(viewport={'width': ancho, 'height': 900}, locale='es-CL')
            context.add_cookies([{'name': settings.SESSION_COOKIE_NAME,
                                  'value': client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': live_server.url}])
            page = context.new_page()
            for ruta in paginas:
                page.goto(live_server.url + ruta)
                assert page.evaluate('document.documentElement.scrollWidth') <= ancho, f'{ruta} desborda a {ancho} px'
                for tono, contraste in page.evaluate(CONTRASTE):
                    tonos_vistos.add(tono)
                    assert contraste >= 4.5, f'{ruta}: tono {tono} con contraste {contraste:.2f} a {ancho} px'
                if ancho == 375:
                    # A 375 px cada resumen se apila: un artículo por fila.
                    columnas = page.evaluate("""() => [...document.querySelectorAll('.resumen-compacto')].map(s =>
                        new Set([...s.children].map(a => Math.round(a.getBoundingClientRect().left))).size)""")
                    assert all(c == 1 for c in columnas), f'{ruta} no se apila a 375 px: {columnas}'
            context.close()
        browser.close()
    assert tonos_vistos >= {'verde', 'ambar', 'azul', 'gris', 'neutro'}
