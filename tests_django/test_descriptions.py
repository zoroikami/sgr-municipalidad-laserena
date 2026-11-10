"""The 500-character limit must hold even when the browser is bypassed."""
import pytest
from django.urls import reverse

from gestion.models import Atencion, ItemMeta, SubAtencion, TipoAtencion

pytestmark = pytest.mark.django_db
MODULES = [('metas', ItemMeta, 'meta_a'), ('atenciones', Atencion, 'atn_a'),
           ('tipos', TipoAtencion, 'tipo_a'), ('subatenciones', SubAtencion, 'sub_a')]


def payload(mundo, modulo, description):
    if modulo == 'atenciones':
        return {'solicitante_nombre': 'Solicitud de prueba', 'solicitante_rut': '12345678-5',
                'tipo': mundo['tipo_a'].pk, 'subatencion': mundo['sub_a'].pk,
                'descripcion': description, 'estado': 'Ingresada'}
    return {'nombre': 'Registro de prueba', 'descripcion': description, 'estado': 'Activo',
            'unidad_medida': 'Atenciones', 'tipo': mundo['tipo_a'].pk}


@pytest.mark.parametrize('modulo,model,objkey', MODULES)
@pytest.mark.parametrize('length,accepted', [(500, True), (501, False)])
def test_create_description_boundary_without_browser(client, mundo, modulo, model, objkey, length, accepted):
    client.force_login(mundo['users']['admin_a'])
    description = 'á' * length
    before = model.all_objects.count()
    response = client.post(reverse('gestion:crear', args=[modulo]), payload(mundo, modulo, description))
    if accepted:
        assert response.status_code == 302
        assert model.all_objects.count() == before + 1
        assert model.objects.get(descripcion=description).descripcion == description
    else:
        assert response.status_code == 200
        assert 'descripcion' in response.context['form'].errors
        assert response.context['form']['descripcion'].value() == description
        assert model.all_objects.count() == before


@pytest.mark.parametrize('modulo,model,objkey', MODULES)
def test_edit_rejects_long_description_without_altering_saved_record(client, mundo, modulo, model, objkey):
    client.force_login(mundo['users']['admin_a'])
    target = mundo[objkey]
    original_description = target.descripcion
    response = client.post(reverse('gestion:editar', args=[modulo, target.pk]),
                           payload(mundo, modulo, 'ñ' * 501))
    assert response.status_code == 200
    assert 'descripcion' in response.context['form'].errors
    target.refresh_from_db()
    assert target.descripcion == original_description
