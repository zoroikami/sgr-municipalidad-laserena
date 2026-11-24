"""Hojas RECLAMOS, SEMAFORO/RESUMEN, GES SEG y el indicador «Soluciones al ingreso al tubo» de la matriz."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from gestion.integrado import CARGOS, resultado_final, resultado_item, resultado_tubo, semaforo
from gestion.models import ActividadSGR, GestionTubo, ItemMeta, ReclamoSGR

pytestmark = pytest.mark.django_db


def delegado(mundo):
    user = mundo['users']['admin_a']
    user.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    return type(user).objects.get(pk=user.pk)


def test_resultado_final_bonifica_felicitaciones_descuenta_reclamos_y_tope_150():
    assert resultado_final(Decimal(90), 1, 0) == Decimal(100)
    assert resultado_final(Decimal(90), 5, 0) == Decimal(120)  # máximo 3 felicitaciones
    assert resultado_final(Decimal(90), 0, 1) == Decimal(70)
    assert resultado_final(Decimal(120), 3, 0) == Decimal(150)
    assert resultado_final(Decimal(145), 3, 0) == Decimal(150)
    assert resultado_final(Decimal(10), 0, 2) == Decimal(0)
    assert resultado_final(None, 2, 0) is None


def test_semaforo_objetivo_al_dia_descuenta_ausencias_y_usa_umbral_60():
    inicio, fin = date(2026, 10, 1), date(2026, 12, 31)  # 92 días
    hoy = date(2026, 11, 15)  # 46 días transcurridos
    luz = semaforo(Decimal(50), inicio, fin, hoy, [])
    assert luz['objetivo'] == Decimal(50) and luz['color'] == 'verde'
    assert semaforo(Decimal(40), inicio, fin, hoy, [])['color'] == 'naranjo'
    assert semaforo(Decimal(20), inicio, fin, hoy, [])['color'] == 'rojo'
    ausencias = [SimpleNamespace(desde=date(2026, 11, 1), hasta=date(2026, 11, 23))]
    luz = semaforo(Decimal(40), inicio, fin, hoy, ausencias)
    assert luz['netos'] == 31 and luz['color'] == 'verde'
    assert semaforo(Decimal(100), inicio, fin, date(2027, 2, 1), [])['objetivo'] == Decimal(100)
    assert semaforo(None, inicio, fin, hoy, [])['color'] is None


def test_soluciones_al_ingreso_al_tubo_mide_tasa_realizada():
    meta = SimpleNamespace(pk=1, meta_cantidad=80, ponderador=Decimal(25), indicador='tubo')
    datos = {'solicitante': 'Vecina ficticia', 'solicitante_telefono': '912345678'}
    gestiones = [SimpleNamespace(estado='Realizado', **datos)] * 4 + [SimpleNamespace(estado='Pendiente', **datos)]
    row = resultado_tubo(meta, gestiones)
    assert row['cantidad'] == 4 and row['porcentaje'] == Decimal(100)
    assert resultado_item(meta, [], [], date(2026, 10, 1), date(2026, 12, 31), gestiones)['porcentaje'] == Decimal(100)
    assert resultado_tubo(meta, [SimpleNamespace(estado='Realizado', **datos)])['porcentaje'] == Decimal(120)
    assert resultado_tubo(meta, [])['porcentaje'] is None


def test_felicitacion_no_cuenta_como_accion_del_item(mundo):
    meta = mundo['meta_a']
    meta.meta_cantidad = 1
    base = dict(delegacion=mundo['a'], responsable=mundo['users']['editor_a'], item=meta, cargo='social',
                fecha=timezone.localdate(), descripcion='x', solicitante_nombre='Vecino', solicitante_telefono='912345678')
    felicitacion = ActividadSGR(**base, felicitacion=True, respaldo_formal='Correo al delegado',
                                informado_por=mundo['users']['admin_a'])
    assert felicitacion.puntuable
    inicio = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
    fin = inicio + timedelta(days=4)
    assert resultado_item(meta, [felicitacion], [], inicio, fin)['cantidad'] == 0
    assert resultado_item(meta, [ActividadSGR(**base)], [], inicio, fin)['cantidad'] == 1


def test_gestor_de_seguridad_es_un_cargo_municipal():
    assert ('seguridad', 'Gestor de seguridad ciudadana') in CARGOS


def test_cargar_matriz_simula_aplica_y_es_idempotente(mundo):
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk)
    assert not ItemMeta.objects.filter(cargo_sgr='seguridad').exists()
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk, aplicar=True)
    seguridad = ItemMeta.objects.filter(delegacion=mundo['a'], cargo_sgr='seguridad')
    assert seguridad.count() == 7
    assert sum(item.ponderador for item in seguridad) == Decimal(100)
    assert seguridad.get(indicador='tubo').meta_cantidad == 80
    total = ItemMeta.objects.count()
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk, aplicar=True)
    assert ItemMeta.objects.count() == total
    for cargo in ('social', 'organizaciones', 'administrativo', 'servicios', 'planificacion'):
        assert ItemMeta.objects.filter(delegacion=mundo['a'], cargo_sgr=cargo).exists()
    assert ItemMeta.objects.get(pk=mundo['meta_a'].pk).estado == 'Activo'
    call_command('cargar_matriz_sgr', delegacion=mundo['a'].pk, aplicar=True, desactivar_comunes=True)
    assert ItemMeta.objects.get(pk=mundo['meta_a'].pk).estado == 'Inactivo'
    assert ItemMeta.objects.get(pk=mundo['meta_b'].pk).estado == 'Activo'


def test_reclamo_solo_lo_registra_el_delegado_y_valida_delegacion(client, mundo):
    client.force_login(mundo['users']['editor_a'])
    assert client.get(reverse('gestion:reclamo_crear')).status_code == 403
    jefe = delegado(mundo)
    client.force_login(jefe)
    datos = {'responsable': mundo['users']['editor_a'].pk, 'fecha': timezone.localdate().isoformat(),
             'usuario_nombre': 'Vecina de prueba', 'contacto': '912345678', 'situacion': 'Mala atención en oficina',
             'medio_escrito': 'libro', 'informado_a': 'Delegado'}
    assert client.post(reverse('gestion:reclamo_crear'), datos).status_code == 302
    reclamo = ReclamoSGR.objects.get()
    assert reclamo.delegacion == mundo['a'] and reclamo.registrado_por == jefe
    futuro = {**datos, 'fecha': (timezone.localdate() + timedelta(days=2)).isoformat()}
    assert client.post(reverse('gestion:reclamo_crear'), futuro).status_code == 200
    assert ReclamoSGR.objects.count() == 1
    with pytest.raises(ValidationError):
        ReclamoSGR(delegacion=mundo['a'], responsable=mundo['users']['lector_b'], usuario_nombre='x', situacion='y',
                   medio_escrito='correo', registrado_por=jefe).full_clean()


def test_resultados_muestran_semaforo_reclamos_y_alerta_rrhh(client, mundo):
    hoy = timezone.localdate()
    jefe = delegado(mundo)
    editor = mundo['users']['editor_a']
    editor.perfil.cargo_sgr = 'social'
    editor.perfil.save()
    mundo['meta_a'].meta_cantidad = 1
    mundo['meta_a'].save()
    ActividadSGR.objects.create(delegacion=mundo['a'], responsable=editor, item=mundo['meta_a'], cargo='social', fecha=hoy,
                                descripcion='Taller', solicitante_nombre='Vecino', solicitante_telefono='912345678')
    GestionTubo.objects.create(delegacion=mundo['a'], nombre='Poda', solicitante='JJVV', responsable=editor, estado='Realizado')
    # Reclamos en el trimestre actual y en los dos anteriores: más de dos trimestres seguidos.
    for meses in (0, 3, 6):
        fecha = (hoy.replace(day=1) - timedelta(days=31 * meses)).replace(day=1) if meses else hoy
        ReclamoSGR.objects.create(delegacion=mundo['a'], responsable=editor, fecha=fecha, usuario_nombre='Vecino',
                                  situacion='Mala atención', medio_escrito='correo', registrado_por=jefe)
    client.force_login(jefe)
    response = client.get(reverse('gestion:resultados_sgr'), {
        'anio': hoy.year, 'trimestre': (hoy.month - 1) // 3 + 1, 'responsable': editor.pk})
    assert response.status_code == 200
    detalle = response.context['detalle']
    assert detalle['reclamos'] == 1 and detalle['ingresos'] == 1 and detalle['ultimo'] == hoy
    assert detalle['porcentaje'] == detalle['base'] - 20
    assert detalle['semaforo']['color'] in ('verde', 'naranjo', 'rojo')
    assert detalle['rrhh']
    contenido = response.content.decode()
    assert 'Informar a RRHH' in contenido and 'Semáforo y resumen del equipo' in contenido
    assert 'Registrar reclamo' in contenido
