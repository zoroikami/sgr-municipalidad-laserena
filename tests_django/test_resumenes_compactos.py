"""El resumen conserva los totales del ámbito y el plazo semanal al compartir presentación."""
from datetime import date
from html.parser import HTMLParser

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from gestion.integrado import periodo_actual
from gestion.models import Carta


class Resumen(HTMLParser):
    def __init__(self, contenido):
        super().__init__()
        self.articulos = []
        self.campo = None
        self.feed(contenido)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'data-tono' in attrs:
            self.articulos.append({'tono': attrs['data-tono'], 'h2': '', 'strong': ''})
        if tag in ('h2', 'strong'):
            self.campo = tag

    def handle_endtag(self, tag):
        if tag in ('h2', 'strong'):
            self.campo = None

    def handle_data(self, data):
        if self.campo and self.articulos:
            self.articulos[-1][self.campo] += data


@pytest.mark.django_db
def test_resumen_cartas_conserva_totales_ambito_y_tono_al_filtrar(client, mundo):
    for indice, estado in enumerate(('En proceso', 'Aprobada', 'Finalizada', 'No aplica')):
        Carta.objects.create(delegacion=mundo['a'], nombre=f'Carta {indice}', numero_ingreso=f'OP-{indice}',
                             remite='Organización ficticia', encargado=mundo['users']['editor_a'], estado=estado)
    Carta.objects.create(delegacion=mundo['b'], nombre='Carta de otro ámbito', numero_ingreso='OP-externo',
                         remite='Organización ficticia', encargado=mundo['users']['lector_b'])
    client.force_login(mundo['users']['editor_a'])
    response = client.get(reverse('gestion:listado', args=['cartas']), {'q': 'Carta 0'})
    assert response.context['page_obj'].paginator.count == 1
    contenido = render_to_string('gestion/_cartas_resumen.html', {'cartas_resumen': response.context['cartas_resumen']})
    articulos = Resumen(contenido).articulos
    assert [(a['h2'].strip(), a['strong'].strip(), a['tono']) for a in articulos] == [
        ('En proceso', '1', 'ambar'), ('Aprobada', '1', 'azul'), ('Finalizada', '1', 'verde'),
        ('No aplica', '1', 'gris'), ('Total', '4', 'neutro'),
    ]


def test_periodo_compacto_conserva_alerta_del_lunes_y_barra_con_fecha_correcta():
    contenido = render_to_string('shared/periodo.html', {'periodo_sgr': periodo_actual(date(2026, 11, 23))})
    articulos = Resumen(contenido).articulos
    assert len(articulos) == 3
    assert articulos[-1]['tono'] == 'rojo'
    assert 'Hoy vence la semana del 16/11' in articulos[-1]['strong']
    assert 'Desde mañana solo se aceptan actividades desde el 23/11/2026' in contenido
    assert '<progress' in contenido and 'max="100"' in contenido and 'value="' in contenido
