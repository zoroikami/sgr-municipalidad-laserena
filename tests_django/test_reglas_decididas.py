"""Reglas de la matriz que quedaban por decidir: verificación, ingreso al tubo, metas individuales, seguridad y cierre."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from gestion.integrado import DESCUENTO_RECLAMO, primera_fecha_admisible, titulo_item
from gestion.models import ActividadSGR, CasoSocial, GestionTubo, ItemMeta, MetaFuncionario

pytestmark = pytest.mark.django_db


def delegado_de(mundo):
    delegado = mundo['users']['admin_a']
    delegado.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    return type(delegado).objects.get(pk=delegado.pk)  # sin caché de permisos


def datos_actividad(mundo, **extra):
    return {'item': mundo['meta_a'].pk, 'cargo': 'social', 'fecha': timezone.localdate().isoformat(),
            'descripcion': 'Solicitud de poda en pasaje Los Aromos', 'es_accion': 'on', 'solicitante_nombre': 'Vecina',
            'solicitante_telefono': '912345678', **extra}


def test_reclamo_descuenta_30_por_ciento():
    assert DESCUENTO_RECLAMO == Decimal(30)


def test_actividad_marcada_ingresa_al_tubo_vinculada_y_sin_duplicar_nombres(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    for _ in range(2):
        assert client.post(reverse('gestion:actividad_crear'), datos_actividad(mundo, ingresar_tubo='on')).status_code == 302
    actividades = list(ActividadSGR.objects.order_by('pk'))
    gestiones = list(GestionTubo.objects.order_by('pk'))
    assert len(gestiones) == 2 and [a.gestion_tubo_id for a in actividades] == [g.pk for g in gestiones]
    assert gestiones[0].nombre == 'Solicitud de poda en pasaje Los Aromos'
    assert gestiones[1].nombre.endswith(f'({actividades[1].codigo})')
    assert all(g.estado == 'Ingresado' and g.solicitante_telefono == '912345678' for g in gestiones)


def test_ingreso_al_tubo_exige_telefono_y_respeta_otra_gestion_del_delegado(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    response = client.post(reverse('gestion:actividad_crear'),
                           datos_actividad(mundo, ingresar_tubo='on', solicitante_telefono=''))
    assert response.status_code == 200 and 'ingresar_tubo' in response.context['form'].errors
    assert not ActividadSGR.objects.exists() and not GestionTubo.objects.exists()
    client.post(reverse('gestion:actividad_crear'), datos_actividad(mundo, ingresar_tubo='on', solicitante_delegado='on'))
    assert GestionTubo.objects.get().solicitante_cargo == 'delegado'


def test_delegado_verifica_actividad_aunque_su_item_este_inactivo(client, mundo):
    editor, delegado = mundo['users']['editor_a'], delegado_de(mundo)
    actividad = ActividadSGR.objects.create(delegacion=mundo['a'], responsable=editor, item=mundo['meta_a'], cargo='social',
                                            descripcion='Taller', solicitante_nombre='Vecina', solicitante_telefono='912345678')
    assert actividad.puntuable and actividad.codigo == f'SOC-{actividad.fecha:%m%d}-{actividad.pk}'
    ItemMeta.objects.filter(pk=mundo['meta_a'].pk).update(estado='Inactivo')
    url = reverse('gestion:actividad_verificar', args=[actividad.pk])
    client.force_login(editor)
    assert client.post(url, {'verificacion': 'no_valida', 'motivo': 'Sin respaldo'}).status_code == 403
    client.force_login(delegado)
    client.post(url, {'verificacion': 'no_valida', 'motivo': ''})
    actividad.refresh_from_db()
    assert actividad.verificacion == 'valida'
    client.post(url, {'verificacion': 'no_valida', 'motivo': 'La foto no corresponde'})
    actividad.refresh_from_db()
    assert not actividad.puntuable and actividad.verificado_por == delegado
    assert actividad.motivo_puntaje == 'Sin puntaje: el verificador la marcó no válida: La foto no corresponde.'
    client.post(url, {'verificacion': 'valida'})
    actividad.refresh_from_db()
    assert actividad.puntuable and actividad.verificacion_motivo == ''


def test_meta_individual_del_funcionario_reemplaza_la_del_cargo(client, mundo):
    editor, delegado = mundo['users']['editor_a'], delegado_de(mundo)
    editor.perfil.cargo_sgr = 'social'
    editor.perfil.save()
    item = ItemMeta.objects.create(delegacion=mundo['a'], nombre='Entrega beneficio (Gestor social)', unidad_medida='Beneficios',
                                   cargo_sgr='social', meta_cantidad=8, ponderador=20)
    url = reverse('gestion:meta_funcionario', args=[item.pk, editor.pk])
    client.force_login(editor)
    assert client.get(url).status_code == 403
    client.force_login(delegado)
    response = client.post(url, {'meta_cantidad': 15, 'ponderador': '25'}, follow=True)
    assert response.status_code == 200 and not response.context['filter_form'].errors
    assert response.context['detalle']['funcionario'] == editor
    assert MetaFuncionario.objects.get(item=item, funcionario=editor).meta_cantidad == 15
    response = client.get(reverse('gestion:resultados_sgr'), {'anio': timezone.localdate().year,
                          'trimestre': (timezone.localdate().month - 1) // 3 + 1, 'responsable': editor.pk})
    fila = next(r for r in response.context['resultados'] if r['meta'].pk == item.pk)
    assert fila['meta'].meta_cantidad == 15 and fila['meta'].ponderador == Decimal(25)
    item.refresh_from_db()
    assert item.meta_cantidad == 8  # la meta del cargo no cambia
    client.post(url, {'meta_cantidad': 15, 'ponderador': '25', 'quitar': 'on'})
    assert not MetaFuncionario.objects.exists()


def test_seguridad_se_actualiza_a_salon_sin_pisar_lo_configurado(mundo):
    salida = open('/dev/null', 'w')
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk, aplicar=True, stdout=salida)
    comites = ItemMeta.objects.get(delegacion=mundo['a'], nombre=titulo_item('seguridad', 'FORMACIÓN DE COMITÉS DE SEGURIDAD'))
    assert (comites.meta_cantidad, comites.ponderador) == (6, Decimal(25))
    # Simula una delegación cargada con la versión anterior y un ítem que el delegado ya configuró.
    comites.meta_cantidad, comites.ponderador = 36, Decimal(20)
    comites.save()
    mediacion = ItemMeta.objects.get(delegacion=mundo['a'], nombre=titulo_item('seguridad', 'GESTIÓN DE MEDIACIÓN'))
    mediacion.meta_cantidad = 30
    mediacion.save()
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk, aplicar=True, actualizar=True, stdout=salida)
    comites.refresh_from_db()
    mediacion.refresh_from_db()
    assert (comites.meta_cantidad, comites.ponderador) == (6, Decimal(25))
    assert mediacion.meta_cantidad == 30
    salidas = ItemMeta.objects.get(delegacion=mundo['a'], nombre=titulo_item('seguridad', 'SALIDAS A TERRENO'))
    assert salidas.ponderador == 0


def test_tubo_nuevo_respeta_el_cierre_semanal_y_lo_antiguo_se_puede_editar(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    hoy = timezone.localdate()
    vieja = primera_fecha_admisible(hoy) - timedelta(days=1)
    datos = {'nombre': 'Retiro de escombros', 'fecha_solicitud': vieja.isoformat(), 'origen': 'EXT', 'solicitante': 'Vecina',
             'solicitante_telefono': '912345678', 'responsable': mundo['users']['editor_a'].pk}
    response = client.post(reverse('gestion:crear', args=['tubo']), datos)
    assert 'fecha_solicitud' in response.context['form'].errors
    gestion = GestionTubo.objects.create(delegacion=mundo['a'], nombre='Antigua', solicitante='Vecina',
                                         solicitante_telefono='912345678', responsable=mundo['users']['editor_a'],
                                         fecha_solicitud=vieja)
    response = client.post(reverse('gestion:editar', args=['tubo', gestion.pk]), {**datos, 'nombre': 'Antigua',
                           'estado': 'Ingresado', 'updated_at': gestion.updated_at.isoformat()})
    assert response.status_code in (200, 302)
    if response.status_code == 200:
        assert 'fecha_solicitud' not in response.context['form'].errors


def test_gestion_registrada_desde_el_caso_alimenta_sus_plazos(client, mundo):
    editor = mundo['users']['editor_a']
    editor.perfil.cargo_sgr = 'social'
    editor.perfil.save()
    visita = ItemMeta.objects.create(delegacion=mundo['a'], nombre=titulo_item('social', 'VISITA TERRENO'),
                                     unidad_medida='Visitas', cargo_sgr='social', meta_cantidad=12, ponderador=20)
    hoy = timezone.localdate()
    caso = CasoSocial.objects.create(delegacion=mundo['a'], nombre='Vecina con caso', responsable=editor,
                                     usuario_telefono='912345678', requiere_visita=True, fecha_ingreso=hoy,
                                     fecha_programada_visita=hoy)
    client.force_login(editor)
    detalle = client.get(reverse('gestion:detalle', args=['casos', caso.pk])).content.decode()
    enlace = f"{reverse('gestion:actividad_crear')}?caso={caso.pk}&amp;responsable={editor.pk}&amp;cargo=social"
    assert enlace in detalle
    formulario = client.get(reverse('gestion:actividad_crear'), {'caso': caso.pk, 'responsable': editor.pk, 'cargo': 'social'})
    assert formulario.context['form']['caso'].value() == str(caso.pk)
    response = client.post(reverse('gestion:actividad_crear'), datos_actividad(mundo, item=visita.pk, caso=caso.pk,
                           descripcion='Visita domiciliaria'), follow=True)
    assert response.status_code == 200 and response.request['PATH_INFO'] == reverse('gestion:detalle', args=['casos', caso.pk])
    caso = CasoSocial.objects.get(pk=caso.pk)
    assert caso.fecha_visita == hoy
    assert next(p for p in caso.plazos() if p['clave'] == 'programada_visita')['cumple'] is True


def test_sin_permiso_de_tubo_no_se_ofrece_ingresar_al_tubo(client, mundo):
    from django.contrib.auth.models import Group
    editor = mundo['users']['editor_a']
    grupo = Group.objects.get(name='Operador / Funcionario')
    grupo.permissions.remove(Permission.objects.get(codename='add_gestiontubo'))
    client.force_login(editor)
    form = client.get(reverse('gestion:actividad_crear')).context['form']
    assert 'ingresar_tubo' not in form.fields
    client.post(reverse('gestion:actividad_crear'), datos_actividad(mundo, ingresar_tubo='on'))
    assert ActividadSGR.objects.count() == 1 and not GestionTubo.objects.exists()
