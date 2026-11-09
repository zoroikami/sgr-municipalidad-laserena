from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from openpyxl import load_workbook

from gestion.models import Atencion, ItemMeta

pytestmark = pytest.mark.django_db


def login(client, mundo, alias):
    client.force_login(mundo['users'][alias])


@pytest.mark.parametrize('modulo,objkey', [('metas', 'meta_a'), ('atenciones', 'atn_a')])
def test_reader_cannot_write_by_direct_requests(client, mundo, modulo, objkey):
    login(client, mundo, 'lector_a')
    for route, args in [('crear', [modulo]), ('editar', [modulo, mundo[objkey].pk]), ('archivar', [modulo, mundo[objkey].pk])]:
        assert client.post(reverse('gestion:' + route, args=args), {}).status_code == 403


@pytest.mark.parametrize('modulo,objkey', [('metas', 'meta_b'), ('atenciones', 'atn_b')])
def test_other_scope_objects_hidden_everywhere(client, mundo, modulo, objkey):
    login(client, mundo, 'admin_a')
    pk = mundo[objkey].pk
    for route, method in [('detalle', 'get'), ('editar', 'post'), ('archivar', 'post')]:
        assert getattr(client, method)(reverse('gestion:' + route, args=[modulo, pk])).status_code == 404
    response = client.get(reverse('gestion:listado', args=[modulo]))
    assert response.status_code == 200
    assert str(mundo[objkey]) not in response.content.decode()


def test_editor_creates_meta_and_server_ignores_scope_code_quantity(client, mundo):
    login(client, mundo, 'editor_a')
    response = client.post(reverse('gestion:crear', args=['metas']), {
        'nombre': 'Meta nueva', 'descripcion': 'Persistente', 'unidad_medida': 'Atenciones',
        'estado': 'Activo', 'meta_cantidad': -500, 'delegacion': mundo['b'].pk, 'codigo': 'HACK',
    })
    assert response.status_code == 302
    item = ItemMeta.objects.get(nombre='Meta nueva')
    assert item.delegacion_id == mundo['a'].pk
    assert item.meta_cantidad == 100
    assert item.codigo != 'HACK'


def test_invalid_form_preserves_data_and_does_not_write(client, mundo):
    login(client, mundo, 'editor_a')
    response = client.post(reverse('gestion:crear', args=['metas']), {
        'nombre': 'Valor conservado', 'unidad_medida': '', 'estado': 'Activo',
    })
    assert response.status_code == 200
    assert response.context['form'].errors
    assert response.context['form']['nombre'].value() == 'Valor conservado'
    assert not ItemMeta.objects.filter(nombre='Valor conservado').exists()


def test_attention_cannot_use_foreign_relation(client, mundo):
    login(client, mundo, 'editor_a')
    before = Atencion.objects.count()
    response = client.post(reverse('gestion:crear', args=['atenciones']), {
        'solicitante_nombre': 'No debe guardarse', 'solicitante_rut': '12.345.678-5',
        'descripcion': 'Relación ajena', 'tipo': mundo['tipo_b'].pk,
        'subatencion': mundo['sub_b'].pk, 'estado': 'Ingresada',
    })
    assert response.status_code == 200
    assert response.context['form'].errors
    assert Atencion.objects.count() == before


def test_editor_creates_attention_with_server_responsibility_and_scoped_client(client, mundo):
    login(client, mundo, 'editor_a')
    response = client.post(reverse('gestion:crear', args=['atenciones']), {
        'solicitante_nombre': 'Atención nueva', 'solicitante_rut': '12.345.678-5',
        'descripcion': 'Solicitud persistida', 'tipo': mundo['tipo_a'].pk,
        'subatencion': mundo['sub_a'].pk, 'cliente': mundo['users']['cliente_1'].pk,
        'estado': 'Ingresada', 'responsable': mundo['users']['lector_b'].pk,
        'delegacion': mundo['b'].pk, 'folio': 'MANIPULADO',
    })
    assert response.status_code == 302
    obj = Atencion.objects.get(solicitante_nombre='Atención nueva')
    assert obj.responsable_id == mundo['users']['editor_a'].pk
    assert obj.delegacion_id == mundo['a'].pk
    assert obj.folio != 'MANIPULADO'
    assert obj.solicitante_rut == '12345678-5'


def test_attention_subtype_must_match_selected_type_without_writing(client, mundo):
    from gestion.models import TipoAtencion
    login(client, mundo, 'editor_a')
    another = TipoAtencion.objects.create(delegacion=mundo['a'], nombre='Otros servicios')
    before = Atencion.objects.count()
    response = client.post(reverse('gestion:crear', args=['atenciones']), {
        'solicitante_nombre': 'Relación incoherente', 'solicitante_rut': '12345678-5',
        'descripcion': 'No guardar', 'tipo': another.pk,
        'subatencion': mundo['sub_a'].pk, 'estado': 'Ingresada'})
    assert response.status_code == 200
    assert response.context['form'].errors.get('subatencion')
    assert Atencion.objects.count() == before


def test_editor_cannot_archive_but_admin_can_and_get_never_mutates(client, mundo):
    target = mundo['meta_a']
    url = reverse('gestion:archivar', args=['metas', target.pk])
    login(client, mundo, 'editor_a')
    assert client.post(url).status_code == 403
    login(client, mundo, 'admin_a')
    assert client.get(url).status_code == 405
    assert ItemMeta.objects.filter(pk=target.pk).exists()
    assert client.post(url).status_code == 302
    assert not ItemMeta.objects.filter(pk=target.pk).exists()
    assert ItemMeta.all_objects.get(pk=target.pk).deleted_at


def test_edit_preserves_creation_timestamp(client, mundo):
    login(client, mundo, 'editor_a')
    target = mundo['meta_a']
    created = target.created_at
    response = client.post(reverse('gestion:editar', args=['metas', target.pk]), {
        'nombre': target.nombre, 'descripcion': 'Editada', 'unidad_medida': 'Atenciones', 'estado': 'Activo'})
    assert response.status_code == 302
    target.refresh_from_db()
    assert target.created_at == created
    assert target.descripcion == 'Editada'


def test_list_state_survives_navigation_and_invalid_page_is_clamped(client, mundo):
    login(client, mundo, 'lector_a')
    for i in range(36):
        ItemMeta.objects.create(delegacion=mundo['a'], nombre=f'Busca {i:02}', unidad_medida='Atenciones')
    url = reverse('gestion:listado', args=['metas'])
    client.get(url, {'q': 'Busca', 'tamano': 5, 'orden': 'nombre'})
    response = client.get(url, {'pagina': 3})
    assert response.context['page_obj'].number == 3
    client.get(reverse('gestion:listado', args=['atenciones']))
    response = client.get(url)
    assert response.context['state']['q'] == 'Busca'
    assert response.context['state']['tamano'] == 5
    assert response.context['page_obj'].number == 3
    assert client.get(url, {'pagina': 9999}).context['page_obj'].number == 8
    assert client.get(url, {'q': 'Inexistente'}).context['page_obj'].number == 1
    invalid = client.get(url, {'orden': 'password', 'tamano': -5, 'pagina': 'abc'})
    assert invalid.status_code == 200
    assert invalid.context['state']['orden'] == '-created_at'
    assert invalid.context['state']['tamano'] == 15


def test_export_contains_all_filtered_rows_no_other_scope_or_archived(client, mundo):
    from django.utils import timezone
    login(client, mundo, 'lector_a')
    for i in range(35):
        ItemMeta.objects.create(delegacion=mundo['a'], nombre=f'Exportable {i:02}', unidad_medida='Visitas')
    ItemMeta.objects.create(delegacion=mundo['b'], nombre='Exportable ajeno', unidad_medida='Visitas')
    ItemMeta.all_objects.create(delegacion=mundo['a'], nombre='Exportable archivado', unidad_medida='Visitas', deleted_at=timezone.now())
    client.get(reverse('gestion:listado', args=['metas']), {'q': 'Exportable', 'tamano': 5})
    response = client.get(reverse('gestion:exportar', args=['metas']))
    assert response.status_code == 200
    sheet = load_workbook(BytesIO(response.content)).active
    assert sheet.max_row == 36
    values = str(list(sheet.values))
    assert 'ajeno' not in values and 'archivado' not in values
    assert 'password' not in values


def test_excel_preserves_user_input_as_text_instead_of_executable_formula(client, mundo):
    login(client, mundo, 'lector_a')
    ItemMeta.objects.create(delegacion=mundo['a'], nombre='=1+1', unidad_medida='Visitas')
    response = client.get(reverse('gestion:exportar', args=['metas']), {'q': '=1+1'})
    sheet = load_workbook(BytesIO(response.content)).active
    assert sheet['B2'].value == '=1+1'
    assert sheet['B2'].data_type == 's'


def test_attention_export_is_filtered_unpaginated_and_excludes_archive(client, mundo):
    from django.utils import timezone
    login(client, mundo, 'admin_a')
    for i in range(31):
        Atencion.objects.create(delegacion=mundo['a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
            responsable=mundo['users']['editor_a'], solicitante_rut='12345678-5',
            solicitante_nombre=f'Exportar atención {i}', descripcion='Ficticia', estado='Resuelta')
    target = Atencion.objects.filter(solicitante_nombre='Exportar atención 0').get()
    target.deleted_at = timezone.now()
    target.save(update_fields=['deleted_at'])
    client.get(reverse('gestion:listado', args=['atenciones']), {'q': 'Exportar atención', 'estado': 'Resuelta', 'tamano': 5})
    response = client.get(reverse('gestion:exportar', args=['atenciones']))
    sheet = load_workbook(BytesIO(response.content)).active
    assert sheet.max_row == 31
    assert all(row[3] == 'Resuelta' for row in list(sheet.values)[1:])
    assert 'Bernarda Norte' not in str(list(sheet.values))


def test_attention_date_range_is_shared_by_list_refresh_and_excel(client, mundo):
    login(client, mundo, 'lector_a')
    local = ZoneInfo('America/Santiago')
    start = datetime(2026, 11, 1, tzinfo=local)
    end = datetime(2026, 11, 5, 23, 59, 59, tzinfo=local)

    def create_attention(name, created_at, **overrides):
        fields = dict(delegacion=mundo['a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
                      responsable=mundo['users']['editor_a'], solicitante_rut='12345678-5',
                      solicitante_nombre=name, estado='Resuelta', created_at=created_at)
        return Atencion.objects.create(**(fields | overrides))

    expected = [create_attention(f'Periodo {index}', end if index else start) for index in range(6)]
    create_attention('Periodo anterior', datetime(2026, 10, 31, 23, 59, tzinfo=local))
    create_attention('Periodo posterior', datetime(2026, 11, 6, tzinfo=local))
    create_attention('Periodo pendiente', start, estado='Ingresada')
    create_attention('Periodo archivado', end, deleted_at=end)
    create_attention('Periodo ajeno', end, delegacion=mundo['b'], tipo=mundo['tipo_b'],
                     subatencion=mundo['sub_b'], responsable=mundo['users']['lector_b'])

    args = ['atenciones']
    url = reverse('gestion:listado', args=args)
    filters = {'q': 'Periodo', 'estado': 'Resuelta', 'desde': '2026-11-01', 'hasta': '2026-11-05', 'tamano': 5}
    client.get(url, {'q': 'Periodo', 'estado': 'Resuelta', 'tamano': 5})
    assert client.get(url, {'pagina': 2}).context['page_obj'].number == 2
    result = client.get(url, filters | {'pagina': 2})
    assert result.context['page_obj'].number == 1
    assert result.context['page_obj'].paginator.count == len(expected)
    page_two = client.get(result.context['pagination'][1]['url'])
    assert page_two.context['page_obj'].number == 2
    assert page_two.context['rows'][0]['obj'] == expected[0]
    refresh = client.get(reverse('gestion:tabla', args=args))
    assert refresh.context['page_obj'].number == 2
    assert refresh.context['rows'][0]['obj'] == expected[0]

    client.get(url, {'desde': '2026-11-06', 'hasta': ''})
    response = client.get(page_two.context['export_url'])
    sheet = load_workbook(BytesIO(response.content)).active
    assert {row[0] for row in list(sheet.values)[1:]} == {item.folio for item in expected}


@pytest.mark.parametrize('invalid', [
    {'desde': '2026-11-31'},
    {'desde': '2026-11-06', 'hasta': '2026-11-05'},
])
def test_invalid_attention_date_range_keeps_previous_session_and_rejects_export(client, mundo, invalid):
    login(client, mundo, 'lector_a')
    args = ['atenciones']
    url = reverse('gestion:listado', args=args)
    client.get(url, {'desde': '2026-11-01', 'hasta': '2026-11-05'})
    result = client.get(url, invalid)
    assert result.context['date_form'].errors
    assert result.context['page_obj'].paginator.count == 0
    assert not result.context['export_url']
    assert client.get(reverse('gestion:exportar', args=args), invalid).status_code == 400
    assert client.get(url).context['state']['desde'] == '2026-11-01'
    cleared = client.get(url, {'desde': '', 'hasta': ''})
    assert cleared.context['state']['desde'] == cleared.context['state']['hasta'] == ''


def test_client_only_own_records_and_no_admin_urls(client, mundo):
    login(client, mundo, 'cliente_1')
    portal = client.get(reverse('gestion:portal'))
    assert portal.status_code == 200
    assert b'Alicia Centro' in portal.content
    assert b'Carolina Centro' not in portal.content
    assert client.get(reverse('gestion:portal_detalle', args=[mundo['atn_2'].pk])).status_code == 404
    assert client.get(reverse('gestion:portal_detalle', args=[mundo['atn_a'].pk])).status_code == 200
    for route in ['listado', 'exportar', 'tabla']:
        assert client.get(reverse('gestion:' + route, args=['atenciones'])).status_code == 403
    login(client, mundo, 'cliente_2')
    assert b'Carolina Centro' in client.get(reverse('gestion:portal')).content
    assert client.get(reverse('gestion:portal_detalle', args=[mundo['atn_a'].pk])).status_code == 404


def test_csrf_is_required_for_mutation(client, mundo):
    from django.test import Client
    guarded = Client(enforce_csrf_checks=True)
    guarded.force_login(mundo['users']['admin_a'])
    assert guarded.post(reverse('gestion:archivar', args=['metas', mundo['meta_a'].pk])).status_code == 403
    assert ItemMeta.objects.filter(pk=mundo['meta_a'].pk).exists()
