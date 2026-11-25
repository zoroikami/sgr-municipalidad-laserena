"""Integración del tiempo real: qué cambios avisan a qué paneles y qué páginas los exponen."""
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from gestion import realtime
from gestion.models import (ActividadSGR, AusenciaSGR, Carta, CasoSocial, GestionTubo, ItemMeta, MetaFuncionario,
                            ReclamoSGR)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def avisos(monkeypatch):
    # autouse: se instala antes de `mundo`, cuyos registros también avisan.
    registro = []
    monkeypatch.setattr(realtime, 'notify_after_commit',
                        lambda delegacion_id, modulo='atenciones': registro.append((delegacion_id, modulo)))
    return registro


def test_cada_modelo_avisa_a_su_modulo_fuente(mundo, avisos):
    a, editor = mundo['a'], mundo['users']['editor_a']
    avisos.clear()  # los ítems del escenario también avisaron
    gestion = GestionTubo.objects.create(delegacion=a, nombre='Poda', solicitante='Vecina', responsable=editor)
    Carta.objects.create(delegacion=a, nombre='Carta', numero_ingreso='OP-1', remite='Junta', encargado=editor)
    caso = CasoSocial.objects.create(delegacion=a, nombre='Vecina', responsable=editor, usuario_telefono='912345678')
    assert avisos == [(a.pk, 'tubo'), (a.pk, 'cartas'), (a.pk, 'casos')]
    avisos.clear()
    ActividadSGR.objects.create(delegacion=a, responsable=editor, item=mundo['meta_a'], cargo='social', descripcion='Visita',
                                caso=caso)
    assert avisos == [(a.pk, 'sgr'), (a.pk, 'casos')]
    avisos.clear()
    hoy = timezone.localdate()
    AusenciaSGR.objects.create(delegacion=a, responsable=editor, desde=hoy, hasta=hoy, motivo='libre',
                               registrado_por=mundo['users']['admin_a'])
    ReclamoSGR.objects.create(delegacion=a, responsable=editor, usuario_nombre='Vecino', situacion='Demora',
                              medio_escrito='correo', registrado_por=mundo['users']['admin_a'])
    ajuste = MetaFuncionario.objects.create(item=mundo['meta_a'], funcionario=editor, meta_cantidad=5, ponderador=10)
    ajuste.delete()
    assert avisos == [(a.pk, 'sgr')] * 4
    avisos.clear()
    gestion.estado = 'Pendiente'
    gestion.save()
    ItemMeta.objects.create(delegacion=mundo['b'], nombre='Otra', unidad_medida='Atenciones')
    assert avisos == [(a.pk, 'tubo'), (mundo['b'].pk, 'sgr')]


def test_verificar_actividad_avisa_aunque_use_update(client, mundo, avisos):
    delegado = mundo['users']['admin_a']
    delegado.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    actividad = ActividadSGR.objects.create(delegacion=mundo['a'], responsable=mundo['users']['editor_a'],
                                            item=mundo['meta_a'], cargo='social', descripcion='Taller')
    avisos.clear()
    client.force_login(type(delegado).objects.get(pk=delegado.pk))
    client.post(reverse('gestion:actividad_verificar', args=[actividad.pk]), {'verificacion': 'no_valida', 'motivo': 'Duplicada'})
    assert avisos == [(mundo['a'].pk, 'sgr')]


@pytest.mark.parametrize('nombre, args, modulo', [
    ('gestion:tablero', [], 'tubo'), ('gestion:cartas_tablero', [], 'cartas'), ('gestion:resultados_sgr', [], 'sgr'),
    ('gestion:listado', ['tubo'], 'tubo'), ('gestion:listado', ['cartas'], 'cartas'), ('gestion:listado', ['casos'], 'casos'),
])
def test_paginas_exponen_su_panel_y_el_estado_fuera_de_el(client, mundo, nombre, args, modulo):
    client.force_login(mundo['users']['admin_a'])
    html = client.get(reverse(nombre, args=args)).content.decode()
    assert html.count('data-realtime-panel') == 1 and f'data-realtime-module="{modulo}"' in html
    assert html.index('data-realtime-status') < html.index('data-realtime-panel')
    assert 'sgr/realtime-panel.js' in html


def test_detalle_de_caso_tiene_panel_y_otros_detalles_no(client, mundo):
    caso = CasoSocial.objects.create(delegacion=mundo['a'], nombre='Vecina', responsable=mundo['users']['editor_a'],
                                     usuario_telefono='912345678')
    client.force_login(mundo['users']['admin_a'])
    assert 'data-realtime-module="casos"' in client.get(reverse('gestion:detalle', args=['casos', caso.pk])).content.decode()
    gestion = GestionTubo.objects.create(delegacion=mundo['a'], nombre='Poda', solicitante='Vecina',
                                         responsable=mundo['users']['editor_a'])
    assert 'data-realtime-panel' not in client.get(reverse('gestion:detalle', args=['tubo', gestion.pk])).content.decode()
