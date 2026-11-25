from datetime import timedelta
from io import BytesIO

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from gestion.integrado import titulo_item
from gestion.models import ActividadSGR, CasoSocial, GestionTubo, ItemMeta, SubAtencion, TipoAtencion


pytestmark = pytest.mark.django_db


def url(action, obj=None):
    return reverse('gestion:' + action, args=['casos', obj.pk] if obj else ['casos'])


@pytest.fixture
def caso(mundo):
    return CasoSocial.objects.create(delegacion=mundo['a'], nombre='Vecina del caso de prueba',
        responsable=mundo['users']['editor_a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
        usuario_rut='12345678-5', usuario_telefono='+56 9 1234 5678', descripcion='Evaluación social')


def payload(mundo, **changes):
    return dict(nombre='Vecina del caso de prueba', descripcion='Evaluación social',
        fecha_ingreso=timezone.localdate().isoformat(), tipo=mundo['tipo_a'].pk,
        subatencion=mundo['sub_a'].pk, usuario_rut='12.345.678-5', usuario_telefono='+56 9 1234 5678',
        responsable=mundo['users']['editor_a'].pk, devoluciones=0, estado='Abierto', **changes)


def test_consultor_solo_ve_y_cliente_no_accede(client, mundo, caso):
    client.force_login(mundo['users']['lector_a'])
    for action in ('listado', 'tabla', 'exportar', 'detalle'):
        response = client.get(url(action, caso if action == 'detalle' else None))
        assert response.status_code == 200
        if action != 'exportar':
            assert 'Casos sociales' in response.content.decode()
    html = client.get(url('detalle', caso)).content.decode()
    assert 'Registrar gestión' not in html
    assert 'Editar registro' not in html
    for action in ('crear', 'editar', 'archivar'):
        target = url(action, caso if action != 'crear' else None)
        assert client.post(target, payload(mundo)).status_code == 403
    client.force_login(mundo['users']['cliente_1'])
    for action in ('listado', 'tabla', 'exportar', 'crear', 'detalle', 'editar'):
        assert client.get(url(action, caso if action in ('detalle', 'editar') else None)).status_code == 403
    assert client.post(url('archivar', caso)).status_code == 403


def test_aislamiento_delegacion_y_enlace_de_navegacion(client, mundo, caso):
    client.force_login(mundo['users']['lector_b'])
    assert client.get(url('detalle', caso)).status_code == 404
    assert caso.nombre not in client.get(url('listado')).content.decode()
    client.force_login(mundo['users']['editor_a'])
    extranjero = CasoSocial.objects.create(delegacion=mundo['b'], nombre='Caso ajeno',
        responsable=mundo['users']['lector_b'], usuario_telefono='912345678')
    assert client.get(url('editar', extranjero)).status_code == 404
    assert client.post(url('editar', extranjero), payload(mundo)).status_code == 404
    assert 'Casos sociales' in client.get(reverse('gestion:inicio')).content.decode()


def test_alta_al_tubo_y_edicion_no_duplican_el_vinculo(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    response = client.post(url('crear'), payload(mundo, ingresar_tubo='on'))
    assert response.status_code == 302, response.context and response.context['form'].errors
    caso = CasoSocial.objects.get()
    assert caso.usuario_rut == '12345678-5'
    tubo = caso.gestion_tubo
    assert tubo and GestionTubo.objects.count() == 1
    assert (tubo.delegacion, tubo.responsable, tubo.solicitante) == (mundo['a'], mundo['users']['editor_a'], caso.nombre)
    assert (tubo.solicitante_telefono, tubo.solicitante_rut, tubo.fecha_solicitud) == (
        caso.usuario_telefono, caso.usuario_rut, caso.fecha_ingreso)
    html = client.get(url('detalle', caso)).content.decode()
    assert reverse('gestion:detalle', args=['tubo', tubo.pk]) in html
    assert reverse('gestion:actividad_crear') + f'?caso={caso.pk}' in html
    form = client.get(url('editar', caso)).context['form']
    assert 'ingresar_tubo' not in form.fields
    assert client.post(url('editar', caso), payload(mundo, ingresar_tubo='on')).status_code == 302
    assert GestionTubo.objects.count() == 1


def test_pueden_existir_varios_casos_del_mismo_usuario_y_sin_tubo(client, mundo, caso):
    client.force_login(mundo['users']['editor_a'])
    assert client.post(url('crear'), payload(mundo)).status_code == 302
    assert CasoSocial.objects.filter(nombre=caso.nombre).count() == 2
    assert GestionTubo.objects.count() == 0


@pytest.mark.parametrize('field,value', [('usuario_telefono', ''), ('usuario_rut', '12345678-0'),
                                        ('devoluciones', 4), ('devoluciones', -1)])
def test_rechaza_datos_invalidos(client, mundo, field, value):
    client.force_login(mundo['users']['editor_a'])
    data = payload(mundo)
    data[field] = value
    response = client.post(url('crear'), data)
    assert response.status_code == 200
    assert field in response.context['form'].errors
    assert not CasoSocial.objects.exists()


def test_relaciones_filtradas_y_subatencion_de_otro_tipo_rechazada(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    other_type = TipoAtencion.objects.create(delegacion=mundo['a'], nombre='Otra categoría')
    other_sub = SubAtencion.objects.create(delegacion=mundo['a'], tipo=other_type, nombre='Otro trámite')
    form = client.get(url('crear')).context['form']
    assert form['responsable'].value() == mundo['users']['editor_a'].pk
    assert all(field.help_text for field in form.visible_fields())
    for field, value in [('tipo', mundo['tipo_b'].pk), ('subatencion', mundo['sub_b'].pk),
                         ('responsable', mundo['users']['lector_b'].pk), ('subatencion', other_sub.pk)]:
        data = payload(mundo)
        data[field] = value
        response = client.post(url('crear'), data)
        assert response.status_code == 200
        assert field in response.context['form'].errors
    assert not CasoSocial.objects.exists()


def test_caso_y_tubo_se_revierten_juntos_si_falla_la_operacion(client, mundo, monkeypatch):
    from gestion import ingreso_tubo
    original = ingreso_tubo.ingresar_al_tubo
    def fallar(**kwargs):
        original(**kwargs)
        raise IntegrityError('Fallo de prueba tras crear el tubo')
    monkeypatch.setattr(ingreso_tubo, 'ingresar_al_tubo', fallar)
    client.force_login(mundo['users']['editor_a'])
    response = client.post(url('crear'), payload(mundo, ingresar_tubo='on'))
    assert response.status_code == 200
    assert not CasoSocial.objects.exists()
    assert not GestionTubo.objects.exists()


def test_cuenta_global_no_puede_mezclar_catalogos_de_delegaciones(client, mundo):
    client.force_login(mundo['users']['coordinador'])
    data = payload(mundo)
    data.update(delegacion=mundo['a'].pk, tipo=mundo['tipo_b'].pk, subatencion=mundo['sub_b'].pk)
    response = client.post(url('crear'), data)
    assert response.status_code == 200
    assert 'tipo' in response.context['form'].errors
    assert 'subatencion' in response.context['form'].errors
    assert not CasoSocial.objects.exists()
    data.update(tipo=mundo['tipo_a'].pk, subatencion=mundo['sub_a'].pk)
    assert client.post(url('crear'), data).status_code == 302
    assert CasoSocial.objects.get().delegacion == mundo['a']


def test_ingreso_al_tubo_requiere_su_permiso_propio(client, mundo):
    from django.contrib.auth.models import Group, Permission
    Group.objects.get(name='Operador / Funcionario').permissions.remove(
        Permission.objects.get(codename='add_gestiontubo'))
    client.force_login(mundo['users']['editor_a'])
    response = client.post(url('crear'), payload(mundo, ingresar_tubo='on'))
    assert response.status_code == 200
    assert 'ingresar_tubo' in response.context['form'].errors
    assert not CasoSocial.objects.exists()


@pytest.mark.parametrize('offsets,expected', [((8, 8, 12, 16), [True] * 5),
                                           ((11, 12, 17, 22), [False] * 5),
                                           ((8, None, None, None), [True, None, None, None, None])])
def test_plazos_informativos_y_gestiones_del_caso(client, mundo, caso, offsets, expected):
    start = timezone.localdate() - timedelta(days=30)
    caso.fecha_ingreso = start
    caso.requiere_visita = True
    caso.fecha_programada_visita = start + timedelta(days=offsets[0])
    caso.save()
    activities = []
    for item_name, offset in zip(('VISITA TERRENO', 'ENTREGA INFORME', 'ENTREGA BENEFICIO'), offsets[1:]):
        if offset is not None:
            item = ItemMeta.objects.create(delegacion=mundo['a'], nombre=titulo_item('social', item_name),
                unidad_medida='Gestiones', cargo_sgr='social')
            activities.append(ActividadSGR(delegacion=mundo['a'], caso=caso,
                responsable=mundo['users']['editor_a'], item=item, cargo='social', fecha=start + timedelta(days=offset),
                descripcion='Gestión histórica', solicitante_nombre=caso.nombre, solicitante_telefono=caso.usuario_telefono))
    # Registros históricos: su fecha ya no está dentro de la ventana de ingreso semanal actual.
    ActividadSGR.objects.bulk_create(activities)
    client.force_login(mundo['users']['lector_a'])
    response = client.get(url('detalle', caso))
    assert response.status_code == 200
    assert [row['cumple'] for row in response.context['plazos_caso']] == expected
    html = response.content.decode()
    assert 'informativos' in html
    for activity in activities:
        assert activity.item.nombre in html
        assert activity.motivo_puntaje in html
    for state, text in ((True, 'Cumple'), (False, 'Fuera de plazo'), (None, 'Pendiente')):
        if state in expected:
            assert text in html


def test_busqueda_estados_exportacion_y_archivo(client, mundo, caso):
    client.force_login(mundo['users']['admin_a'])
    for search in (caso.codigo, caso.nombre, '12345678-5', '12.345.678-5', mundo['sub_a'].nombre):
        response = client.get(url('listado'), {'q': search})
        assert response.status_code == 200
        assert caso.codigo in response.content.decode()
    response = client.get(url('listado'), {'q': '', 'estado': 'Cerrado'})
    assert caso.codigo not in response.content.decode()
    response = client.get(url('exportar'), {'estado': ''})
    book = load_workbook(BytesIO(response.content), read_only=True)
    rows = list(book.active.values)
    assert 'Teléfono del usuario' in rows[0]
    assert any(caso.codigo in row for row in rows[1:])
    book.close()
    assert client.post(url('archivar', caso)).status_code == 302
    assert not CasoSocial.objects.exists()
    assert client.get(url('detalle', caso)).status_code == 404
