"""Excel exportado con identidad municipal: contexto, tabla ordenada, estados con color y texto seguro."""
from io import BytesIO

import pytest
from django.urls import reverse
from openpyxl import load_workbook

from gestion.exportacion import FILA_ENCABEZADO, TONOS_ESTADO
from gestion.models import Carta

pytestmark = pytest.mark.django_db


def test_excel_tiene_franja_contexto_encabezado_y_estados_con_color(client, mundo):
    for numero, estado in enumerate(['En proceso', 'Finalizada', 'No aplica']):
        Carta.objects.create(delegacion=mundo['a'], nombre=f'Carta {numero}', numero_ingreso=f'OP-{numero}',
                             remite='=HYPERLINK("http://ejemplo.test")', encargado=mundo['users']['editor_a'], estado=estado)
    client.force_login(mundo['users']['admin_a'])
    client.get(reverse('gestion:listado', args=['cartas']), {'q': 'Carta'})
    hoja = load_workbook(BytesIO(client.get(reverse('gestion:exportar', args=['cartas'])).content)).active
    assert hoja['A1'].value.startswith('Ilustre Municipalidad de La Serena')
    assert hoja['A1'].fill.fgColor.rgb.endswith('C41230')
    assert hoja['A2'].value == 'Cartas de oficina de partes'
    assert 'Centro · 3 registros · Exportado el' in hoja['A3'].value
    assert hoja['A4'].value == 'Búsqueda «Carta»'
    encabezado = [c.value for c in hoja[FILA_ENCABEZADO]]
    assert encabezado[0] == 'Código' and 'Estado' in encabezado
    assert hoja.freeze_panes == f'A{FILA_ENCABEZADO + 1}'
    assert hoja.auto_filter.ref.startswith(f'A{FILA_ENCABEZADO}:')
    columna_estado = encabezado.index('Estado') + 1
    colores = {hoja.cell(row=f, column=columna_estado).value: hoja.cell(row=f, column=columna_estado).fill.fgColor.rgb
               for f in range(FILA_ENCABEZADO + 1, FILA_ENCABEZADO + 4)}
    assert colores['Finalizada'].endswith(TONOS_ESTADO['verde'][0]) and colores['No aplica'].endswith(TONOS_ESTADO['gris'][0])
    # El texto del usuario sigue siendo texto aunque parezca una fórmula.
    remite = hoja.cell(row=FILA_ENCABEZADO + 1, column=encabezado.index('Remite') + 1)
    assert remite.value.startswith('=HYPERLINK') and remite.data_type == 's'


def test_excel_sin_filtros_lo_indica(client, mundo):
    client.force_login(mundo['users']['admin_a'])
    hoja = load_workbook(BytesIO(client.get(reverse('gestion:exportar', args=['metas'])).content)).active
    assert hoja['A4'].value.startswith('Sin filtros')
