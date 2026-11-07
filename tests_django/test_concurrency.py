"""Deterministic interleaving: an editor must never resurrect an archived row."""
import threading
from unittest.mock import patch

import pytest
from django.db import connections
from django.test import Client
from django.urls import reverse

from gestion.forms import AtencionForm, ItemMetaForm

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize('modulo,objkey,form_class', [
    ('metas', 'meta_a', ItemMetaForm), ('atenciones', 'atn_a', AtencionForm),
])
def test_edit_and_archive_cannot_resurrect_record(mundo, modulo, objkey, form_class):
    target = mundo[objkey]
    editor = Client()
    admin = Client()
    editor.force_login(mundo['users']['editor_a'])
    admin.force_login(mundo['users']['admin_a'])
    entered_save = threading.Event()
    release_save = threading.Event()
    archive_done = threading.Event()
    responses = {}
    errors = []
    real_save = form_class.save
    if modulo == 'metas':
        payload = {'nombre': target.nombre, 'descripcion': 'Edición concurrente', 'unidad_medida': 'Visitas', 'estado': 'Activo'}
    else:
        payload = {'solicitante_nombre': target.solicitante_nombre, 'solicitante_rut': '12345678-5',
            'descripcion': 'Edición concurrente', 'tipo': mundo['tipo_a'].pk,
            'subatencion': mundo['sub_a'].pk, 'estado': 'Ingresada'}

    def delayed_save(form, *args, **kwargs):
        entered_save.set()
        assert release_save.wait(5), 'El coordinador de la prueba no liberó el guardado.'
        return real_save(form, *args, **kwargs)

    def edit():
        try:
            responses['edit'] = editor.post(reverse('gestion:editar', args=[modulo, target.pk]), payload).status_code
        except Exception as error:
            errors.append(error)
        finally:
            connections.close_all()

    def archive():
        try:
            responses['archive'] = admin.post(reverse('gestion:archivar', args=[modulo, target.pk])).status_code
        except Exception as error:
            errors.append(error)
        finally:
            archive_done.set()
            connections.close_all()

    with patch.object(form_class, 'save', delayed_save):
        edit_thread = threading.Thread(target=edit, daemon=True)
        archive_thread = threading.Thread(target=archive, daemon=True)
        edit_thread.start()
        assert entered_save.wait(5)
        archive_thread.start()
        # With a row lock the archive waits; without it it completes before save.
        archive_done.wait(0.3)
        release_save.set()
        edit_thread.join(5)
        archive_thread.join(5)
    assert not errors, errors
    assert responses == {'edit': 302, 'archive': 302}
    assert not type(target).objects.filter(pk=target.pk).exists()
    assert type(target).all_objects.get(pk=target.pk).deleted_at is not None
