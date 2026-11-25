"""Regresiones de la ronda de QA (Claude + Codex)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from io import BytesIO

from gestion.models import GestionTubo

pytestmark = pytest.mark.django_db


def test_resultados_sgr_no_abre_con_error_para_cuenta_sin_delegacion(client, mundo):
    admin = get_user_model().objects.create_superuser('tecnico', 'tecnico@example.test', 'Ensayo#Privado2026')
    client.force_login(admin)
    response = client.get(reverse('gestion:resultados_sgr'))
    form = response.context['filter_form']
    assert response.status_code == 200 and not form.errors
    assert form.cleaned_data['responsable'] in form.fields['responsable'].queryset
    client.force_login(mundo['users']['editor_a'])
    assert client.get(reverse('gestion:resultados_sgr')).context['filter_form'].cleaned_data['responsable'] == mundo['users']['editor_a']


def test_tubo_rechaza_solicitud_futura_y_compromiso_anterior(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    hoy = timezone.localdate()
    datos = {'nombre': 'Revisión de fechas', 'fecha_solicitud': hoy.isoformat(), 'origen': 'EXT',
             'solicitante': 'Vecina', 'solicitante_telefono': '912345678', 'responsable': mundo['users']['editor_a'].pk}
    errores = client.post(reverse('gestion:crear', args=['tubo']),
                          {**datos, 'fecha_compromiso': (hoy - timedelta(days=1)).isoformat()}).context['form'].errors
    assert 'fecha_compromiso' in errores
    errores = client.post(reverse('gestion:crear', args=['tubo']),
                          {**datos, 'fecha_solicitud': (hoy + timedelta(days=1)).isoformat()}).context['form'].errors
    assert 'fecha_solicitud' in errores
    assert client.post(reverse('gestion:crear', args=['tubo']), {**datos, 'fecha_compromiso': hoy.isoformat()}).status_code == 302


def test_exportacion_del_tubo_incluye_las_columnas_de_la_hoja_tubo(client, mundo):
    GestionTubo.objects.create(delegacion=mundo['a'], nombre='Poda', solicitante='Vecina', solicitante_rut='12345678-5',
                               solicitante_telefono='912345678', responsable=mundo['users']['editor_a'],
                               observaciones='Se coordina con DISERCO')
    client.force_login(mundo['users']['editor_a'])
    response = client.get(reverse('gestion:exportar', args=['tubo']))
    filas = list(load_workbook(BytesIO(response.content)).active.iter_rows(values_only=True))
    encabezado = filas[0]
    for columna in ('Fecha de solicitud', 'RUT solicitante', 'Teléfono solicitante', 'Responsable',
                    'Fecha de compromiso', 'Avance, observaciones', 'Estatus'):
        assert columna in encabezado
    fila = dict(zip(encabezado, filas[1]))
    assert fila['RUT solicitante'] == '12.345.678-5' and fila['Avance, observaciones'] == 'Se coordina con DISERCO'


def test_listado_de_usuarios_muestra_el_cargo_municipal(client, mundo):
    perfil = mundo['users']['editor_a'].perfil
    perfil.cargo_sgr = 'social'
    perfil.save()
    client.force_login(mundo['users']['admin_a'])
    html = client.get(reverse('cuentas:usuarios')).content.decode()
    assert 'Cargo municipal' in html and 'Gestor social' in html and 'Sin cargo asignado' in html


def test_resumen_de_cartas_no_repite_los_conteos_de_las_columnas(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    html = client.get(reverse('gestion:cartas_tablero')).content.decode()
    assert 'Cartas en este estado' not in html and 'Carta en este estado' not in html
    assert 'Cartas en seguimiento' in html and 'Tasa de cierre' in html and 'Vencidos' in html
