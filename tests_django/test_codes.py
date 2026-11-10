"""Legacy section prefixes with safe allocation and existing-record conversion."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import threading
from types import SimpleNamespace

from django.apps import apps
from django.db import connections
from django.utils import timezone
import pytest

from gestion.models import Atencion, Delegacion, ItemMeta, Secuencia, SubAtencion, TipoAtencion

pytestmark = pytest.mark.django_db(transaction=True)


def test_section_codes_match_previous_format_and_continue_existing_numbers(mundo):
    assert Delegacion.objects.create(nombre='Nueva oficina', direccion='Dirección de prueba').codigo == 'DEL03'
    assert ItemMeta.objects.create(delegacion=mundo['a'], nombre='Nueva meta', unidad_medida='Atenciones').codigo == 'IT003'
    assert TipoAtencion.objects.create(delegacion=mundo['a'], nombre='Nuevo tipo').codigo == 'TA003'
    assert SubAtencion.objects.create(delegacion=mundo['a'], tipo=mundo['tipo_a'], nombre='Nueva subatención').codigo == 'SA003'
    attention = Atencion.objects.create(delegacion=mundo['a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
        responsable=mundo['users']['editor_a'], solicitante_nombre='Solicitud nueva',
        solicitante_rut='12345678-5', descripcion='Solicitud de prueba')
    assert attention.folio == f'ATN-{timezone.localdate().year}-0004'


def test_codes_never_reuse_archived_or_explicit_high_numbers(mundo):
    ItemMeta.all_objects.create(codigo='IT999', delegacion=mundo['a'], nombre='Archivada',
                               unidad_medida='Visitas', deleted_at=timezone.now())
    Secuencia.objects.filter(prefijo='IT').update(valor=0)
    item = ItemMeta.objects.create(delegacion=mundo['a'], nombre='Después del archivo', unidad_medida='Visitas')
    assert item.codigo == 'IT1000'


def test_parallel_creations_receive_distinct_ascending_codes(mundo):
    delegation_id = mundo['a'].pk
    Secuencia.objects.filter(prefijo='IT').delete()
    start = threading.Barrier(4)

    def create(number):
        try:
            connections['default'].ensure_connection()
            start.wait(timeout=5)
            return ItemMeta.objects.create(delegacion_id=delegation_id, nombre=f'Paralela {number}',
                                           unidad_medida='Visitas').codigo
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as executor:
        codes = list(executor.map(create, range(4)))
    assert sorted(codes) == ['IT003', 'IT004', 'IT005', 'IT006']


def test_existing_codes_convert_reversibly_without_changing_relationships(mundo):
    migration = importlib.import_module('gestion.migrations.0003_restore_section_codes')
    item = mundo['meta_a']
    ItemMeta.all_objects.filter(pk=item.pk).update(codigo='IT-DEMO-01-000')
    attention = mundo['atn_a']
    Atencion.all_objects.filter(pk=attention.pk).update(folio='ATN-2026-DEMO-01-0000')
    original = (attention.delegacion_id, attention.tipo_id, attention.subatencion_id, attention.cliente_id)
    schema_editor = SimpleNamespace(connection=connections['default'])
    migration.restore_codes(apps, schema_editor)
    item.refresh_from_db()
    attention.refresh_from_db()
    assert item.codigo == 'IT001'
    assert item.codigo_anterior == 'IT-DEMO-01-000'
    assert attention.folio == f'ATN-{timezone.localtime(attention.created_at).year}-0001'
    assert attention.folio_anterior == 'ATN-2026-DEMO-01-0000'
    assert (attention.delegacion_id, attention.tipo_id, attention.subatencion_id, attention.cliente_id) == original
    migration.reverse_codes(apps, schema_editor)
    item.refresh_from_db()
    attention.refresh_from_db()
    assert item.codigo == 'IT-DEMO-01-000'
    assert attention.folio == 'ATN-2026-DEMO-01-0000'


def test_reversal_refuses_new_record_collision_before_changing_any_section(mundo):
    migration = importlib.import_module('gestion.migrations.0003_restore_section_codes')
    schema_editor = SimpleNamespace(connection=connections['default'])
    ItemMeta.all_objects.filter(pk=mundo['meta_a'].pk).update(codigo='IT050')
    migration.restore_codes(apps, schema_editor)
    ItemMeta.objects.create(codigo='IT050', delegacion=mundo['a'], nombre='Registro posterior', unidad_medida='Visitas')
    before = list(ItemMeta.all_objects.order_by('pk').values_list('pk', 'codigo'))
    with pytest.raises(RuntimeError, match='códigos anteriores ocupados'):
        migration.reverse_codes(apps, schema_editor)
    assert list(ItemMeta.all_objects.order_by('pk').values_list('pk', 'codigo')) == before
