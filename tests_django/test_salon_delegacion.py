"""Hoja SALON (resultado de la delegación), catálogo social (hoja LISTA) y otros datos de la matriz revisada."""
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from gestion.integrado import SALON, SALON_EMERGENCIA, SALON_PENDIENTES, SALON_TUBO, puntaje_pendientes, resultado_delegacion, titulo_item
from gestion.management.commands.cargar_matriz_sgr import MATRIZ
from gestion.models import ActividadSGR, AusenciaSGR, GestionTubo, ItemMeta, SubAtencion, TipoAtencion


def fila(cargo, nombre, cantidad, ajustada):
    return {'meta': NS(nombre=titulo_item(cargo, nombre), cargo_sgr=cargo), 'cantidad': cantidad, 'ajustada': Decimal(ajustada)}


def gestion(estado, cargo='', telefono='912345678'):
    return NS(estado=estado, solicitante='Vecina', solicitante_telefono=telefono, solicitante_cargo=cargo)


def test_ponderadores_de_salon_suman_uno_y_sus_items_existen_en_la_matriz():
    total = sum(Decimal(p) for _, _, p, _, _ in SALON) + SALON_TUBO + SALON_PENDIENTES + SALON_EMERGENCIA
    assert total == Decimal('1.00')
    for _, _, _, cargo, fuentes in SALON:
        nombres = {nombre for nombre, *_ in MATRIZ[cargo][1]}
        assert set(fuentes) <= nombres


@pytest.mark.parametrize('tasa, puntaje', [(None, None), (0, 100), (10, 100), (Decimal('10.1'), 50), (50, 50),
                                           (Decimal('50.1'), 0), (100, 0)])
def test_pendientes_en_tubo_menor_a_10_por_ciento(tasa, puntaje):
    assert puntaje_pendientes(tasa) == (Decimal(puntaje) if puntaje is not None else None)


def test_resultado_de_la_delegacion_suma_el_equipo_agrupa_items_y_no_pondera_filas_sin_datos():
    metas = [NS(nombre=titulo_item(c, n)) for c, (_, items) in MATRIZ.items() for n, *_ in items]
    metricas = [
        # Dos funcionarios de organizaciones: la fila suma avances y metas (hojas T OC).
        fila('organizaciones', 'ATENCIÓN DE USUARIO TELÉFONO Y PRESENCIAL', 30, 60),
        fila('organizaciones', 'ATENCIÓN DE USUARIO TELÉFONO Y PRESENCIAL', 60, 60),
        # Informes de DISERCO agrupa informes personal e informe trabajo; supera el tope de 120%.
        fila('servicios', 'INFORMES PERSONAL', 10, 3), fila('servicios', 'INFORME TRABAJO', 12, 12),
        fila('servicios', 'EMERGENCIA', 2, 0),
    ]
    gestiones = [gestion('Realizado'), gestion('Realizado'), gestion('Pendiente'), gestion('En proceso'),
                 gestion('Realizado', telefono=''),  # sin teléfono no suma (punto 2)
                 gestion('Pendiente', cargo='delegado')]  # otra gestión (punto 1)
    resultado = resultado_delegacion(metas, metricas, gestiones)
    filas = {(f['area'], f['nombre']): f for f in resultado['filas']}
    atencion = filas[('Organizaciones comunitarias', 'Atención de usuario teléfono y presencial')]
    assert (atencion['avance'], atencion['meta'], atencion['porcentaje']) == (90, Decimal(120), Decimal(75))
    informes = filas[('DISERCO', 'Informes')]
    assert informes['avance'] == 22 and informes['porcentaje'] == Decimal(120)
    tubo = filas[('Tubo de trabajo', 'Soluciones de ingresos al tubo')]
    assert tubo['avance'] == {'realizadas': 2, 'total': 5, 'tasa': Decimal(40)} and tubo['porcentaje'] == Decimal(50)
    pendientes = filas[('Tubo de trabajo', 'Pendientes en tubo menor a 10%')]
    assert pendientes['avance']['tasa'] == Decimal(20) and pendientes['porcentaje'] == Decimal(50)
    assert filas[('Emergencias', 'Emergencia')]['porcentaje'] == Decimal(100)
    social = filas[('Gestión social', 'Entrega informe')]
    assert social['porcentaje'] is None and social['nota'] == 'Sin funcionarios con este cargo.'
    # Peso considerado: atención OO.CC. 5 + informes 3 + tubo 5 + pendientes 5 + emergencia 5.
    assert resultado['peso'] == Decimal(23)
    esperado = (75 * Decimal('0.05') + 120 * Decimal('0.03') + 50 * Decimal('0.05') + 50 * Decimal('0.05')
                + 100 * Decimal('0.05')) * 100 / 23
    assert resultado['total'] == esperado


def test_sin_items_ni_gestiones_las_filas_quedan_sin_datos():
    resultado = resultado_delegacion([], [], [])
    assert resultado['total'] is None and resultado['peso'] == 0
    notas = {f['nombre']: f['nota'] for f in resultado['filas']}
    assert notas['Informes'] == 'La delegación no tiene este ítem activo.'
    assert notas['Soluciones de ingresos al tubo'] == 'Sin gestiones en el tubo.'
    assert notas['Emergencia'].startswith('Sin emergencias')


@pytest.mark.django_db
def test_resultados_sgr_muestra_el_resultado_de_la_delegacion(client, mundo):
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk, aplicar=True, stdout=open('/dev/null', 'w'))
    editor = mundo['users']['editor_a']
    editor.perfil.cargo_sgr = 'administrativo'
    editor.perfil.save()
    item = ItemMeta.objects.get(delegacion=mundo['a'], nombre=titulo_item('administrativo', 'INFORME DE INVENTARIOS'))
    ActividadSGR.objects.create(delegacion=mundo['a'], responsable=editor, item=item, cargo='administrativo',
                                descripcion='Inventario trimestral', solicitante_nombre='Bodega', solicitante_telefono='912345678')
    GestionTubo.objects.create(delegacion=mundo['a'], nombre='Poda', solicitante='Vecina', solicitante_telefono='912345678',
                               responsable=editor, estado='Realizado')
    GestionTubo.objects.create(delegacion=mundo['b'], nombre='Ajena', solicitante='Vecino', solicitante_telefono='912345678',
                               responsable=mundo['users']['lector_b'], estado='Pendiente')
    client.force_login(editor)
    response = client.get(reverse('gestion:resultados_sgr'))
    salon = response.context['salon']
    filas = {f['nombre']: f for f in salon['filas']}
    assert filas['Informe de inventarios']['porcentaje'] == Decimal(100)
    # Solo cuenta el tubo de su delegación: 1 realizada de 1 y ningún pendiente.
    assert filas['Soluciones de ingresos al tubo']['avance']['total'] == 1
    assert filas['Pendientes en tubo menor a 10%']['porcentaje'] == Decimal(100)
    html = response.content.decode()
    assert 'Resultado de la delegación' in html and 'Peso considerado' in html and 'Sin funcionarios con este cargo.' in html


@pytest.mark.django_db
def test_catalogo_social_simula_carga_y_no_duplica(mundo):
    salida = open('/dev/null', 'w')
    TipoAtencion.objects.create(delegacion=mundo['a'], nombre='  INFORMES  sociales ')
    call_command('cargar_catalogo_social', delegacion=mundo['a'].pk, stdout=salida)
    assert not SubAtencion.objects.filter(nombre='PGU').exists()
    call_command('cargar_catalogo_social', todas=True, aplicar=True, stdout=salida)
    call_command('cargar_catalogo_social', todas=True, aplicar=True, stdout=salida)
    for org in (mundo['a'], mundo['b']):
        tipos = TipoAtencion.objects.filter(delegacion=org).exclude(nombre__in=['Social', 'Salud'])
        assert tipos.count() == 5
        assert SubAtencion.objects.filter(delegacion=org, tipo__in=tipos).count() == 13
    subsidio = SubAtencion.objects.get(delegacion=mundo['a'], nombre='SUF')
    assert subsidio.tipo.nombre == 'Gestión de subsidios' and 'aporte' in subsidio.descripcion
    assert TipoAtencion.objects.filter(delegacion=mundo['a'], nombre='  INFORMES  sociales ').count() == 1


@pytest.mark.django_db
def test_archivar_relleno_demo_solo_toca_items_inactivos_sin_actividades(mundo):
    salida = open('/dev/null', 'w')
    editor = mundo['users']['editor_a']
    libre = ItemMeta.objects.create(delegacion=mundo['a'], nombre='Social: meta territorial 01', unidad_medida='Atenciones',
                                    codigo_anterior='IT-DEMO-01-000', estado='Inactivo')
    usado = ItemMeta.objects.create(delegacion=mundo['a'], nombre='Salud: meta territorial 02', unidad_medida='Atenciones',
                                    codigo_anterior='IT-DEMO-01-001')
    ActividadSGR.objects.create(delegacion=mundo['a'], responsable=editor, item=usado, cargo='social', descripcion='Visita')
    usado.estado = 'Inactivo'
    usado.save()
    activo = ItemMeta.objects.create(delegacion=mundo['a'], nombre='Educación: meta territorial 03', unidad_medida='Visitas',
                                     codigo_anterior='IT-DEMO-01-002')
    call_command('archivar_relleno_demo', stdout=salida)
    assert ItemMeta.objects.filter(pk=libre.pk).exists()
    call_command('archivar_relleno_demo', aplicar=True, stdout=salida)
    assert not ItemMeta.objects.filter(pk=libre.pk).exists() and ItemMeta.all_objects.filter(pk=libre.pk).exists()
    assert ItemMeta.objects.filter(pk__in=[usado.pk, activo.pk]).count() == 2
    assert ItemMeta.objects.filter(pk=mundo['meta_a'].pk).exists()


@pytest.mark.django_db
def test_tipo_de_gestion_diserco_solo_para_servicios_y_nuevos_motivos_de_ausencia(mundo):
    editor = mundo['users']['editor_a']
    datos = dict(delegacion=mundo['a'], responsable=editor, item=mundo['meta_a'], descripcion='Operativo de poda',
                 accion='Gestionar poda', derivado_a='DISERCO', tipo_gestion='podas')
    with pytest.raises(ValidationError) as error:
        ActividadSGR(cargo='social', **datos).save()
    assert 'tipo_gestion' in error.value.message_dict
    actividad = ActividadSGR(cargo='servicios', **datos)
    actividad.save()
    assert actividad.get_tipo_gestion_display() == 'Áreas verdes: podas'
    hoy = timezone.localdate()
    for motivo in ('emergencia', 'compensatorio'):
        ausencia = AusenciaSGR(delegacion=mundo['a'], responsable=editor, desde=hoy, hasta=hoy, motivo=motivo,
                               registrado_por=mundo['users']['admin_a'])
        ausencia.full_clean()
