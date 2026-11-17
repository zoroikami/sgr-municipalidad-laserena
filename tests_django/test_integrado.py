from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from gestion.integrado import validar_fecha, resultado_item
from gestion.models import ActividadSGR, AusenciaSGR, GestionTubo, Organizacion

pytestmark = pytest.mark.django_db


def actividad(mundo, **changes):
    data = dict(delegacion=mundo['a'], responsable=mundo['users']['editor_a'], item=mundo['meta_a'],
        cargo='social', fecha=timezone.localdate(), descripcion='Taller realizado',
        solicitante_nombre='Usuario de prueba', solicitante_telefono='+56912345678')
    return ActividadSGR(**{**data, **changes})


def test_cierre_semanal_lunes_y_martes():
    validar_fecha(date(2026, 11, 2), hoy=date(2026, 11, 9))
    with pytest.raises(ValidationError):
        validar_fecha(date(2026, 11, 6), hoy=date(2026, 11, 10))
    with pytest.raises(ValidationError):
        validar_fecha(date(2026, 11, 11), hoy=date(2026, 11, 10))


def test_octava_actividad_rechazada_y_sin_nombre_se_guarda_sin_puntos(mundo):
    for n in range(7):
        actividad(mundo, descripcion=f'Taller {n}').save()
    with pytest.raises(ValidationError, match='siete'):
        actividad(mundo).save()
    assert ActividadSGR.objects.count() == 7
    assert not actividad(mundo, solicitante_nombre='').puntuable
    assert not actividad(mundo, solicitante_telefono='').puntuable
    assert not actividad(mundo, solicitante_delegado=True).puntuable
    assert not actividad(mundo, es_accion=False).puntuable


def test_tope_ingreso_hoy_no_se_elude_con_fechas_distintas(mundo):
    lunes = date(2026, 11, 9)
    instante = timezone.make_aware(datetime(2026, 11, 9, 12))
    with patch('gestion.integrado.timezone.localdate', return_value=lunes), patch('gestion.models_integrado.timezone.now', return_value=instante):
        for n in range(7):
            actividad(mundo, fecha=lunes - timedelta(days=n)).save()
        with pytest.raises(ValidationError, match='siete'):
            actividad(mundo, fecha=lunes).save()


def test_felicitacion_exige_respaldo_e_informe_del_delegado(mundo):
    obj = actividad(mundo, felicitacion=True)
    assert not obj.puntuable
    obj.respaldo_formal = 'Libro de observaciones, folio de prueba'
    obj.informado_por = mundo['users']['editor_a']
    with pytest.raises(ValidationError, match='delegado'):
        obj.save()
    mundo['users']['admin_a'].user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    obj.informado_por = mundo['users']['admin_a']
    obj.save()
    assert obj.puntuable


def test_metas_tope_120_y_ausencias_superpuestas(mundo):
    meta = mundo['meta_a']
    meta.meta_cantidad = 5
    objs = [actividad(mundo) for _ in range(20)]
    ausencias = [SimpleNamespace(desde=date(2026, 11, 9), hasta=date(2026, 11, 10)),
                 SimpleNamespace(desde=date(2026, 11, 10), hasta=date(2026, 11, 11))]
    row = resultado_item(meta, objs, ausencias, date(2026, 11, 9), date(2026, 11, 13))
    assert row['ajustada'] == Decimal(2)
    assert row['porcentaje'] == Decimal(120)
    row = resultado_item(meta, objs, [SimpleNamespace(desde=date(2026, 11, 9), hasta=date(2026, 11, 13))],
                         date(2026, 11, 9), date(2026, 11, 13))
    assert row['porcentaje'] is None


def test_tablero_ambito_y_transiciones_con_control_de_version(client, mundo):
    obj = GestionTubo.objects.create(delegacion=mundo['a'], nombre='Gestión local',
        solicitante='Vecino local', responsable=mundo['users']['editor_a'])
    foreign = GestionTubo.objects.create(delegacion=mundo['b'], nombre='Gestión ajena',
        solicitante='Vecino ajeno', responsable=mundo['users']['lector_b'])
    client.force_login(mundo['users']['editor_a'])
    response = client.get(reverse('gestion:tablero'))
    assert response.status_code == 200
    assert 'Gestión local' in response.content.decode()
    assert 'Gestión ajena' not in response.content.decode()
    url = reverse('gestion:tubo_mover', args=[obj.pk])
    assert client.get(url).status_code == 405
    assert client.post(reverse('gestion:tubo_mover', args=[foreign.pk]), {'desde': 'Ingresado'}).status_code == 404
    for desde, hasta in [('Ingresado', 'Pendiente'), ('Pendiente', 'En proceso'), ('En proceso', 'Realizado')]:
        assert client.post(url, {'desde': desde}).status_code == 302
        obj.refresh_from_db()
        assert obj.estado == hasta
        client.post(url, {'desde': desde})
        obj.refresh_from_db()
        assert obj.estado == hasta
    client.force_login(mundo['users']['lector_a'])
    assert client.post(url, {'desde': 'Realizado'}).status_code == 403
    client.force_login(mundo['users']['cliente_1'])
    assert client.get(reverse('gestion:tablero')).status_code == 403


def test_actividad_y_ausencia_vistas_respetan_ambito_y_atribucion(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    assert client.get(reverse('gestion:ausencia_crear')).status_code == 403
    response = client.post(reverse('gestion:actividad_crear'), {
        'item': mundo['meta_a'].pk, 'cargo': 'social', 'fecha': timezone.localdate().isoformat(),
        'descripcion': 'Realización de taller', 'es_accion': 'on', 'solicitante_nombre': 'Vecino',
        'solicitante_telefono': '912345678', 'delegacion': mundo['b'].pk,
        'responsable': mundo['users']['lector_b'].pk})
    assert response.status_code == 302
    obj = ActividadSGR.objects.get()
    assert obj.delegacion == mundo['a'] and obj.responsable == mundo['users']['editor_a']
    response = client.get(reverse('gestion:resultados_sgr'))
    assert response.status_code == 200
    response = client.get(reverse('gestion:resultados_sgr'), {
        'anio': timezone.localdate().year, 'trimestre': 4, 'responsable': mundo['users']['lector_b'].pk})
    assert response.context['filter_form'].errors


def test_importacion_simulada_idempotente_y_sin_verificar(tmp_path, mundo):
    from django.core.management import call_command
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = 'juntas de vecinos'
    sheet.append(['ORGANIZACIONES', 'DOMICILIO', 'TERRITORIO'])
    sheet.append(['JUNTA DE VECINOS DE PRUEBA', 'Dirección de prueba', 'CENTRO'])
    sheet.append(['ORGANIZACIÓN AJENA', 'Dirección ajena', 'ANTENA'])
    path = tmp_path / 'base.xlsx'
    book.save(path)
    kwargs = dict(delegacion=mundo['a'].pk, territorio='CENTRO')
    call_command('importar_organizaciones', str(path), **kwargs)
    assert not Organizacion.objects.exists()
    call_command('importar_organizaciones', str(path), aplicar=True, **kwargs)
    call_command('importar_organizaciones', str(path), aplicar=True, **kwargs)
    obj = Organizacion.objects.get()
    assert not obj.verificada and obj.familia == 'territorial' and obj.delegacion == mundo['a']


def test_coordinador_crea_gestion_con_relaciones_de_la_delegacion_elegida(client, mundo):
    from django.contrib.auth.models import Permission
    user = mundo['users']['coordinador']
    user.user_permissions.add(Permission.objects.get(codename='add_gestiontubo'))
    client.force_login(user)
    response = client.post(reverse('gestion:crear', args=['tubo']), {
        'delegacion': mundo['b'].pk, 'nombre': 'Seguimiento en Las Compañías',
        'fecha_solicitud': timezone.localdate().isoformat(), 'origen': 'EXT',
        'solicitante': 'Solicitante de prueba', 'responsable': mundo['users']['lector_b'].pk,
        'atencion': mundo['atn_b'].pk,
    })
    assert response.status_code == 302, response.context['form'].errors
    obj = GestionTubo.objects.get()
    assert obj.delegacion == mundo['b'] and obj.atencion == mundo['atn_b']


def test_delegado_registra_actividad_para_funcionario_designado(client, mundo):
    from django.contrib.auth.models import Permission
    user = mundo['users']['admin_a']
    user.user_permissions.add(*Permission.objects.filter(codename__in=['add_actividadsgr', 'validar_delegado']))
    client.force_login(user)
    response = client.post(reverse('gestion:actividad_crear'), {
        'responsable': mundo['users']['editor_a'].pk, 'item': mundo['meta_a'].pk,
        'cargo': 'social', 'fecha': timezone.localdate().isoformat(),
        'descripcion': 'Actividad informada por el delegado', 'es_accion': 'on',
        'solicitante_nombre': 'Solicitante de prueba', 'solicitante_telefono': '912345678',
    })
    assert response.status_code == 302
    assert ActividadSGR.objects.get().responsable == mundo['users']['editor_a']


def test_roles_municipales_acceden_a_modulos_integrados(client, mundo):
    for alias in ['admin_a', 'editor_a', 'lector_a', 'coordinador']:
        client.force_login(mundo['users'][alias])
        for url in [reverse('gestion:tablero'), reverse('gestion:resultados_sgr'),
                    reverse('gestion:listado', args=['organizaciones'])]:
            assert client.get(url).status_code == 200, (alias, url)
    assert mundo['users']['editor_a'].has_perm('gestion.add_actividadsgr')
    assert not mundo['users']['lector_a'].has_perm('gestion.add_actividadsgr')
    assert not mundo['users']['editor_a'].has_perm('gestion.delete_gestiontubo')
    client.force_login(mundo['users']['cliente_1'])
    assert client.get(reverse('gestion:resultados_sgr')).status_code == 403


def test_actividad_fuera_de_delegacion_del_funcionario_muestra_error_sin_guardar(client, mundo):
    client.force_login(mundo['users']['coordinador'])
    response = client.post(reverse('gestion:actividad_crear'), {
        'delegacion': mundo['b'].pk, 'item': mundo['meta_b'].pk,
        'cargo': 'social', 'fecha': timezone.localdate().isoformat(),
        'descripcion': 'Actividad con ámbito incorrecto', 'es_accion': 'on',
        'solicitante_nombre': 'Solicitante de prueba', 'solicitante_telefono': '912345678',
    })
    assert response.status_code == 200
    assert response.context['form'].non_field_errors()
    assert not ActividadSGR.objects.exists()


def test_altas_globales_ofrecen_relaciones_sin_necesitar_un_post_previo(client, mundo):
    client.force_login(mundo['users']['coordinador'])
    response = client.get(reverse('gestion:crear', args=['tubo']))
    assert response.status_code == 200
    assert mundo['users']['lector_b'] in response.context['form'].fields['responsable'].queryset
    assert mundo['atn_b'] in response.context['form'].fields['atencion'].queryset
    response = client.get(reverse('gestion:actividad_crear'))
    assert mundo['meta_b'] in response.context['form'].fields['item'].queryset
