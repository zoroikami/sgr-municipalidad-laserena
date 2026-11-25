from io import BytesIO, StringIO

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from gestion.exportacion import FILA_ENCABEZADO

pytestmark = pytest.mark.django_db


def model():
    return apps.get_model('gestion', 'Carta')


def data(mundo, **changes):
    return {**{'nombre': 'Solicitud de reunión ficticia', 'fecha': '2026-11-17',
        'numero_ingreso': 'OP-2026-12', 'para': 'Delegado', 'remite': 'Remitente ficticio',
        'telefono': '+56900000000', 'fecha_actividad': '',
        'encargado': mundo['users']['editor_a'].pk, 'estado': 'En proceso',
        'pronunciamiento': 'Para conocimiento', 'derivada_a': 'Unidad ficticia',
        'observacion': 'Confirmar disponibilidad'}, **changes}


def carta(mundo, **changes):
    values = data(mundo)
    values.update(fecha=timezone.localdate(), fecha_actividad=None,
                  encargado=mundo['users']['editor_a'], delegacion=mundo['a'])
    return model().objects.create(**{**values, **changes})


def test_cartas_listado_existe_y_ofrece_alta_a_operador(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    response = client.get('/gestion/cartas/')
    assert response.status_code == 200
    assert response.context['can_add']
    assert '/gestion/cartas/crear/' in response.content.decode()


@pytest.mark.parametrize('alias,read,add,edit,archive', [
    ('coordinador', 200, 200, 200, 302), ('admin_a', 200, 200, 200, 302),
    ('editor_a', 200, 200, 200, 403), ('lector_a', 200, 403, 403, 403),
    ('cliente_1', 403, 403, 403, 403),
])
def test_cartas_permisos_por_rol(client, mundo, alias, read, add, edit, archive):
    obj = carta(mundo)
    client.force_login(mundo['users'][alias])
    assert client.get('/gestion/cartas/').status_code == read
    assert client.get('/gestion/cartas/crear/').status_code == add
    assert client.get(f'/gestion/cartas/{obj.pk}/editar/').status_code == edit
    assert client.post(f'/gestion/cartas/{obj.pk}/archivar/').status_code == archive
    obj.refresh_from_db()
    assert bool(obj.deleted_at) == (archive == 302)


def test_cartas_crud_guarda_planilla_y_no_acepta_delegacion_falsificada(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    response = client.post('/gestion/cartas/crear/', data(mundo, delegacion=mundo['b'].pk))
    assert response.status_code == 302
    obj = model().objects.get(numero_ingreso='OP-2026-12')
    assert obj.delegacion == mundo['a'] and obj.codigo.startswith('CAR-')
    assert obj.pronunciamiento == 'Para conocimiento' and obj.fecha_actividad is None
    assert client.post(f'/gestion/cartas/{obj.pk}/editar/', data(mundo, estado='Aprobada',
        observacion='Aprobada para la reunión')).status_code == 302
    obj.refresh_from_db()
    assert obj.estado == 'Aprobada' and obj.observacion == 'Aprobada para la reunión'
    detail = client.get(f'/gestion/cartas/{obj.pk}/')
    assert detail.status_code == 200
    assert 'OP-2026-12' in detail.content.decode() and 'Para conocimiento' in detail.content.decode()


def test_cartas_ambito_excluye_cartas_y_encargados_ajenos(client, mundo):
    local = carta(mundo)
    foreign = carta(mundo, delegacion=mundo['b'], encargado=mundo['users']['lector_b'], nombre='Carta ajena')
    client.force_login(mundo['users']['editor_a'])
    for suffix in ['', 'editar/', 'archivar/']:
        url = f'/gestion/cartas/{foreign.pk}/'+suffix
        response = client.post(url) if suffix == 'archivar/' else client.get(url)
        expected = 403 if suffix == 'archivar/' else 404
        assert response.status_code == expected
    response = client.get('/gestion/cartas/')
    assert list(response.context['page_obj'].object_list) == [local]
    response = client.post('/gestion/cartas/crear/', data(mundo, encargado=mundo['users']['lector_b'].pk))
    assert response.status_code == 200 and 'encargado' in response.context['form'].errors
    assert model().objects.count() == 2


@pytest.mark.parametrize('changes,field', [({'telefono': 'sin teléfono'}, 'telefono'),
    ({'estado': 'Inventado'}, 'estado'), ({'para': 'Inventado'}, 'para')])
def test_cartas_rechaza_datos_invalidos(client, mundo, changes, field):
    client.force_login(mundo['users']['editor_a'])
    response = client.post('/gestion/cartas/crear/', data(mundo, **changes))
    assert response.status_code == 200 and field in response.context['form'].errors
    assert model().objects.count() == 0


def test_cartas_modelo_rechaza_encargado_inactivo_o_ajeno(mundo):
    obj = carta(mundo)
    obj.encargado = mundo['users']['lector_b']
    with pytest.raises(ValidationError): obj.full_clean()
    obj.encargado = mundo['users']['editor_a']
    obj.encargado.is_active = False
    with pytest.raises(ValidationError): obj.full_clean()


def test_cartas_filtros_resumen_y_excel_incluyen_todos_los_campos_autorizados(client, mundo):
    local = carta(mundo)
    carta(mundo, nombre='Actividad finalizada', numero_ingreso='OP-FIN', estado='Finalizada')
    carta(mundo, nombre='Carta ajena', delegacion=mundo['b'], encargado=mundo['users']['lector_b'])
    archived = carta(mundo, nombre='Carta archivada', estado='No aplica', deleted_at=timezone.now())
    client.force_login(mundo['users']['lector_a'])
    response = client.get('/gestion/cartas/', {'estado': 'En proceso', 'q': 'OP-2026'})
    assert list(response.context['page_obj'].object_list) == [local]
    assert [r['cantidad'] for r in response.context['cartas_resumen']] == [1, 0, 1, 0, 2]
    export = client.get('/gestion/cartas/exportar/')
    assert export.status_code == 200
    rows = list(load_workbook(BytesIO(export.content)).active.values)[FILA_ENCABEZADO - 1:]
    assert len(rows) == 2 and 'OP-2026-12' in rows[1]
    assert 'Para conocimiento' in rows[1] and 'Confirmar disponibilidad' in rows[1]
    assert 'Actividad finalizada' not in str(rows) and 'Carta ajena' not in str(rows)
    assert not model().objects.filter(pk=archived.pk).exists()


def test_superadmin_selector_aplica_a_cartas_y_resumen(client, mundo):
    user = get_user_model().objects.create_superuser('cartas_tecnico', password='Ensayo#Privado2026')
    carta(mundo)
    carta(mundo, delegacion=mundo['b'], encargado=mundo['users']['lector_b'], nombre='Carta norte')
    client.force_login(user)
    assert client.get('/gestion/cartas/').context['page_obj'].paginator.count == 2
    client.post(reverse('cuentas:cambiar_delegacion'), {'delegacion': mundo['b'].pk})
    response = client.get('/gestion/cartas/')
    assert response.context['page_obj'].paginator.count == 1
    assert response.context['cartas_resumen'][-1]['cantidad'] == 1
    bad = client.post('/gestion/cartas/crear/', data(mundo))
    assert 'encargado' in bad.context['form'].errors


def test_cartas_semillas_son_ficticias_idempotentes_y_conservan_ediciones(tmp_path):
    path = str(tmp_path/'cuentas.json')
    call_command('seed_demo', credentials_file=path, stdout=StringIO())
    assert model().objects.count() == 12
    assert set(model().objects.values_list('estado', flat=True)) == {'En proceso','Aprobada','Finalizada','No aplica'}
    obj = model().objects.first()
    obj.observacion = 'Revisión conservada'
    obj.save()
    call_command('seed_demo', credentials_file=path, stdout=StringIO())
    obj.refresh_from_db()
    assert model().objects.count() == 12 and obj.observacion == 'Revisión conservada'


def test_cartas_admite_dos_ingresos_distintos_sobre_el_mismo_tema(client, mundo):
    carta(mundo)
    client.force_login(mundo['users']['editor_a'])
    response = client.post('/gestion/cartas/crear/', data(mundo, numero_ingreso='OP-2026-13'))
    assert response.status_code == 302
    assert model().objects.filter(nombre='Solicitud de reunión ficticia').count() == 2
