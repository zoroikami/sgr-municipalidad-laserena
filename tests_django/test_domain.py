"""Reject invalid business relationships even when JavaScript is bypassed."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from gestion.models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion

pytestmark = pytest.mark.django_db


@pytest.fixture
def delegaciones():
    return (Delegacion.objects.create(nombre='Centro', direccion='Centro 1'),
            Delegacion.objects.create(nombre='Compañías', direccion='Norte 1'))


def test_meta_rejects_negative_quantity(delegaciones):
    item = ItemMeta(delegacion=delegaciones[0], nombre='Cobertura', unidad_medida='Atenciones', meta_cantidad=-1)
    with pytest.raises(ValidationError):
        item.full_clean()
    assert ItemMeta.objects.count() == 0


def test_subatencion_cannot_reference_other_delegation(delegaciones):
    a, b = delegaciones
    tipo = TipoAtencion.objects.create(delegacion=b, nombre='Social')
    sub = SubAtencion(delegacion=a, tipo=tipo, nombre='Subsidios')
    with pytest.raises(ValidationError):
        sub.full_clean()
    assert SubAtencion.objects.count() == 0


def test_duplicate_name_is_rejected_within_delegation_but_allowed_between_scopes(delegaciones):
    a, b = delegaciones
    TipoAtencion.objects.create(delegacion=a, nombre='Social')
    TipoAtencion.objects.create(delegacion=b, nombre='Social')
    with pytest.raises(IntegrityError), transaction.atomic():
        TipoAtencion.objects.create(delegacion=a, nombre='Social')
    assert TipoAtencion.objects.count() == 2


def test_codes_are_automatic_and_distinct(delegaciones):
    a, _ = delegaciones
    first = ItemMeta.objects.create(delegacion=a, nombre='Cobertura', unidad_medida='Atenciones')
    second = ItemMeta.objects.create(delegacion=a, nombre='Resolución', unidad_medida='Atenciones')
    assert first.codigo.startswith('IT')
    assert first.codigo != second.codigo
    assert first.meta_cantidad == 100


def test_archived_records_are_excluded_by_default(delegaciones):
    from django.utils import timezone
    item = ItemMeta.objects.create(delegacion=delegaciones[0], nombre='Archivo', unidad_medida='Atenciones')
    item.deleted_at = timezone.now()
    item.save(update_fields=['deleted_at'])
    assert not ItemMeta.objects.filter(pk=item.pk).exists()
    assert ItemMeta.all_objects.filter(pk=item.pk).exists()
