"""Punto 2 del Nuevo Requerimiento: solicitudes sin nombre/teléfono no dan puntaje."""
from decimal import Decimal

import pytest

from gestion.integrado import resultado_tubo
from gestion.models import GestionTubo, ItemMeta


def gestion(estado, nombre='Vecina ficticia', telefono='912345678', cargo=''):
    return GestionTubo(estado=estado, solicitante=nombre, solicitante_telefono=telefono, solicitante_cargo=cargo)


def meta():
    return ItemMeta(meta_cantidad=80, ponderador=Decimal('100'), indicador='tubo')


@pytest.mark.parametrize('nombre,telefono', [
    ('Vecina ficticia', ''), ('Vecina ficticia', '   '), ('', '912345678'), (' \t ', '912345678'),
])
def test_solicitud_realizada_sin_datos_del_usuario_no_da_puntaje(nombre, telefono):
    resultado = resultado_tubo(meta(), [gestion('Pendiente'), gestion('Realizado', nombre, telefono)])
    assert resultado['cantidad'] == 0
    assert resultado['porcentaje'] == Decimal('0')
    assert resultado['ponderado'] == Decimal('0')


def test_solicitud_completa_conserva_el_calculo_de_puntaje():
    resultado = resultado_tubo(meta(), [gestion('Pendiente'), gestion('Realizado')])
    assert resultado['cantidad'] == 1
    assert resultado['porcentaje'] == Decimal('62.5')


def test_solicitud_del_delegado_con_datos_completos_tampoco_da_puntaje():
    resultado = resultado_tubo(meta(), [gestion('Pendiente'), gestion('Realizado', cargo='delegado')])
    assert resultado['cantidad'] == 0
    assert resultado['porcentaje'] == Decimal('0')
