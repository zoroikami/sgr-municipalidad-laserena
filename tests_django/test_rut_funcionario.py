"""Nuevo requerimiento, puntos 1 y 2: aviso de funcionario por RUT y datos del solicitante en el tubo."""
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from cuentas.rut import format_rut
from gestion.funcionarios import buscar_funcionario
from gestion.integrado import resultado_tubo
from gestion.models import GestionTubo, ItemMeta

pytestmark = pytest.mark.django_db
URL = 'gestion:rut_funcionario'


def rut(mundo, alias):
    return mundo['users'][alias].perfil.rut


def gestion(mundo, **datos):
    datos = {'delegacion': mundo['a'], 'nombre': 'Retiro de ramas', 'solicitante': 'Vecina del sector',
             'responsable': mundo['users']['editor_a'], **datos}
    return GestionTubo.objects.create(**datos)


def test_busqueda_reconoce_funcionarios_activos_y_excluye_vecinos(mundo):
    assert buscar_funcionario(format_rut(rut(mundo, 'admin_a'))) == mundo['users']['admin_a']
    assert buscar_funcionario(rut(mundo, 'cliente_1')) is None
    assert buscar_funcionario('12345678-5') is None
    assert buscar_funcionario('no es rut') is None
    editor = mundo['users']['editor_a']
    editor.is_active = False
    editor.save()
    assert buscar_funcionario(rut(mundo, 'editor_a')) is None


def test_aviso_informa_cargo_sin_exponer_datos_de_contacto(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    datos = client.post(reverse(URL), {'rut': format_rut(rut(mundo, 'admin_a'))}).json()
    assert datos['funcionario'] and datos['es_delegado'] and datos['cargo_nombre'] == 'Delegado'
    assert datos['delegacion'] == 'Centro' and datos['funciones']
    assert 'rut' not in datos and 'email' not in datos
    perfil = mundo['users']['lector_a'].perfil
    perfil.cargo_sgr = 'social'
    perfil.save()
    datos = client.post(reverse(URL), {'rut': rut(mundo, 'lector_a')}).json()
    assert datos['cargo_nombre'] == 'Gestor social' and not datos['es_delegado']
    assert client.post(reverse(URL), {'rut': rut(mundo, 'cliente_1')}).json() == {'valido': True, 'funcionario': False}
    assert client.post(reverse(URL), {'rut': '12345678-9'}).json() == {'valido': False, 'funcionario': False}
    assert client.get(reverse(URL), {'rut': rut(mundo, 'admin_a')}).status_code == 405


def test_aviso_solo_para_personal_que_registra_solicitudes(client, mundo):
    assert client.post(reverse(URL), {'rut': rut(mundo, 'admin_a')}).status_code == 302
    for alias in ('cliente_1', 'lector_a'):
        client.force_login(mundo['users'][alias])
        assert client.post(reverse(URL), {'rut': rut(mundo, 'admin_a')}).status_code == 403


def test_gestion_identifica_al_funcionario_y_conserva_su_cargo(mundo):
    obj = gestion(mundo, solicitante_rut=rut(mundo, 'admin_a'))
    assert obj.solicitante_funcionario == mundo['users']['admin_a'] and obj.solicitante_cargo == 'delegado'
    assert obj.es_otra_gestion and obj.solicitante_funcionario_texto.startswith('Sí · Delegado')
    obj.estado = 'Pendiente'
    obj.save(update_fields=['estado', 'updated_at'])
    obj.solicitante_rut = '12345678-5'
    obj.save()
    obj.refresh_from_db()
    assert obj.solicitante_funcionario is None and obj.solicitante_cargo == '' and not obj.es_otra_gestion


def test_indicador_del_tubo_no_cuenta_solicitudes_del_delegado(mundo):
    meta = ItemMeta(meta_cantidad=80, ponderador=Decimal('100'), indicador='tubo')
    gestiones = [gestion(mundo, nombre=f'Gestión {n}', estado=estado)
                 for n, estado in enumerate(['Realizado', 'Ingresado'])]
    gestiones.append(gestion(mundo, nombre='Pedido del delegado', estado='Ingresado', solicitante_rut=rut(mundo, 'admin_a')))
    resultado = resultado_tubo(meta, gestiones)
    assert resultado['ajustada'] == 2 and resultado['cantidad'] == 1


def test_alta_en_tubo_exige_telefono_y_normaliza_rut(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    datos = {'nombre': 'Poda en pasaje', 'fecha_solicitud': timezone.localdate().isoformat(), 'origen': 'EXT',
             'solicitante': 'Delegado del sector', 'solicitante_rut': format_rut(rut(mundo, 'admin_a')),
             'responsable': mundo['users']['editor_a'].pk}
    response = client.post(reverse('gestion:crear', args=['tubo']), datos)
    assert response.status_code == 200 and 'solicitante_telefono' in response.context['form'].errors
    response = client.post(reverse('gestion:crear', args=['tubo']), {**datos, 'solicitante_rut': '12.345.678-9',
                                                                      'solicitante_telefono': '912345678'})
    assert 'solicitante_rut' in response.context['form'].errors
    response = client.post(reverse('gestion:crear', args=['tubo']), {**datos, 'solicitante_telefono': '912345678'})
    assert response.status_code == 302
    obj = GestionTubo.objects.get()
    assert obj.solicitante_rut == rut(mundo, 'admin_a') and obj.solicitante_cargo == 'delegado'
    formulario = client.get(reverse('gestion:editar', args=['tubo', obj.pk])).content.decode()
    assert 'data-rut-funcionario="/funcionarios/rut/"' in formulario and 'sgr/rut-funcionario.js' in formulario
    tablero = client.get(reverse('gestion:tablero')).content.decode()
    assert 'Funcionario · Delegado' in tablero and 'Otra gestión: la solicita el delegado' in tablero


def test_tarjeta_no_repite_el_codigo_que_ya_muestra(mundo):
    obj = gestion(mundo, atencion=mundo['atn_a'])
    obj.nombre = f'[{mundo["atn_a"].folio}] Revisión de luminarias'
    assert obj.titulo_tarjeta == 'Revisión de luminarias'
    obj.nombre = '[Caso Social SOC-00014] Evaluación'
    assert obj.titulo_tarjeta == '[Caso Social SOC-00014] Evaluación'
    obj.nombre = f'[{obj.codigo}]'
    assert obj.titulo_tarjeta == f'[{obj.codigo}]'
