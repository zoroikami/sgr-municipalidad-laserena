"""Período visible (RF-005, RF-026, nuevo requerimiento punto 4) y listas acotadas (RF-003, 2a entrega)."""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from gestion.integrado import periodo_actual, primera_fecha_admisible
from gestion.models import Atencion, GestionTubo, ItemMeta

pytestmark = pytest.mark.django_db


def test_periodo_actual_informa_inicio_termino_y_plazo_semanal():
    p = periodo_actual(date(2026, 11, 18))
    assert (p['inicio'], p['fin'], p['nombre']) == (date(2026, 10, 1), date(2026, 12, 31), '4º trimestre 2026')
    assert (p['dia'], p['dias_totales'], p['restantes']) == (49, 92, 43)
    assert p['meta_esperada'] == Decimal(49) * 100 / Decimal(92)
    assert (p['semana_inicio'], p['semana_fin'], p['cierre_semana']) == (date(2026, 11, 16), date(2026, 11, 20), date(2026, 11, 23))
    assert not p['cierra_hoy']
    lunes = periodo_actual(date(2026, 11, 16))
    assert lunes['cierra_hoy'] and lunes['primera_admisible'] == date(2026, 11, 9)
    assert primera_fecha_admisible(date(2026, 11, 17)) == date(2026, 11, 16)
    assert periodo_actual(date(2026, 2, 10))['fin'] == date(2026, 3, 31)


def test_aviso_del_periodo_visible_para_funcionarios_y_no_para_clientes(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    contenido = client.get(reverse('gestion:inicio')).content.decode()
    assert 'Trimestre en curso' in contenido and 'Plazo de ingreso semanal' in contenido
    assert timezone.localdate().strftime('%Y') in contenido
    client.force_login(mundo['users']['cliente_1'])
    assert 'Trimestre en curso' not in client.get(reverse('gestion:portal')).content.decode()


def items_cargo(mundo):
    a = mundo['a']
    social = ItemMeta.objects.create(delegacion=a, nombre='Visita social', unidad_medida='Visitas', cargo_sgr='social')
    seguridad = ItemMeta.objects.create(delegacion=a, nombre='Comités', unidad_medida='Comités', cargo_sgr='seguridad')
    tubo = ItemMeta.objects.create(delegacion=a, nombre='Soluciones tubo', unidad_medida='%', cargo_sgr='social',
                                   indicador='tubo', meta_cantidad=80)
    return social, seguridad, tubo


def test_actividad_carga_solo_items_del_cargo_asignado(client, mundo):
    social, seguridad, tubo = items_cargo(mundo)
    editor = mundo['users']['editor_a']
    editor.perfil.cargo_sgr = 'social'
    editor.perfil.save()
    client.force_login(editor)
    form = client.get(reverse('gestion:actividad_crear')).context['form']
    items = set(form.fields['item'].queryset)
    assert items == {mundo['meta_a'], social}  # comunes + cargo, sin el indicador automático del tubo
    assert form.fields['cargo'].disabled and form.fields['cargo'].initial == 'social'
    hoy = timezone.localdate()
    assert form.fields['fecha'].widget.attrs['max'] == hoy.isoformat()
    assert form.fields['fecha'].widget.attrs['min'] == primera_fecha_admisible(hoy).isoformat()
    datos = {'item': seguridad.pk, 'fecha': hoy.isoformat(), 'descripcion': 'Taller', 'es_accion': 'on',
             'solicitante_nombre': 'Vecina', 'solicitante_telefono': '912345678'}
    response = client.post(reverse('gestion:actividad_crear'), datos)
    assert response.status_code == 200 and response.context['form'].errors.get('item')
    response = client.post(reverse('gestion:actividad_crear'), {**datos, 'item': social.pk, 'cargo': 'seguridad'})
    assert response.status_code == 302
    assert editor.actividadsgr_set.get().cargo == 'social'


def test_sin_cargo_asignado_se_elige_cargo_y_se_recargan_items(client, mundo):
    social, seguridad, _ = items_cargo(mundo)
    client.force_login(mundo['users']['editor_a'])
    form = client.get(reverse('gestion:actividad_crear')).context['form']
    assert not form.fields['cargo'].disabled
    assert set(form.fields['item'].queryset) == {mundo['meta_a']}
    data = client.get(reverse('gestion:items_actividad'), {'cargo': 'seguridad'}).json()
    assert data['cargo'] == 'seguridad' and not data['cargo_fijo']
    assert {item['id'] for item in data['items']} == {mundo['meta_a'].pk, seguridad.pk}


def test_delegado_al_elegir_funcionario_recibe_items_de_su_cargo(client, mundo):
    social, _, _ = items_cargo(mundo)
    editor = mundo['users']['editor_a']
    editor.perfil.cargo_sgr = 'social'
    editor.perfil.save()
    delegado = mundo['users']['admin_a']
    delegado.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    client.force_login(delegado)
    data = client.get(reverse('gestion:items_actividad'), {'responsable': editor.pk}).json()
    assert data == {'cargo': 'social', 'cargo_fijo': True,
                    'items': [{'id': mundo['meta_a'].pk, 'nombre': mundo['meta_a'].nombre}, {'id': social.pk, 'nombre': social.nombre}]}
    # Un funcionario de otra delegación no amplía las opciones.
    otro = client.get(reverse('gestion:items_actividad'), {'responsable': mundo['users']['lector_b'].pk}).json()
    assert otro['cargo'] == '' and social.pk not in {item['id'] for item in otro['items']}
    client.force_login(mundo['users']['lector_a'])
    assert client.get(reverse('gestion:items_actividad')).status_code == 403


def test_tubo_ofrece_solo_atenciones_abiertas_y_conserva_la_vinculada(client, mundo):
    resuelta = mundo['atn_2']
    Atencion.objects.filter(pk=resuelta.pk).update(estado='Resuelta')
    client.force_login(mundo['users']['editor_a'])
    form = client.get(reverse('gestion:crear', args=['tubo'])).context['form']
    assert mundo['atn_a'] in form.fields['atencion'].queryset and resuelta not in form.fields['atencion'].queryset
    gestion = GestionTubo.objects.create(delegacion=mundo['a'], nombre='Poda', solicitante='JJVV',
                                         responsable=mundo['users']['editor_a'], atencion=resuelta)
    form = client.get(reverse('gestion:editar', args=['tubo', gestion.pk])).context['form']
    assert resuelta in form.fields['atencion'].queryset
    assert 'data-buscable' in form.fields['atencion'].widget.attrs


def test_organizacion_usa_subfamilias_del_nuevo_requerimiento(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    url = reverse('gestion:crear', args=['organizaciones'])
    contenido = client.get(url).content.decode()
    assert 'Club de adulto mayor' in contenido and 'Junta de vecinos' in contenido
    base = {'nombre': 'Club Los Aromos', 'familia': 'funcional', 'estado': 'Activo'}
    response = client.post(url, {**base, 'subfamilia': 'Junta de vecinos'})
    assert response.status_code == 200 and response.context['form'].errors.get('subfamilia')
    assert client.post(url, {**base, 'subfamilia': 'Club de adulto mayor'}).status_code == 302
