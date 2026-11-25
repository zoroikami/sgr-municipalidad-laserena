"""Ejecuta los verificadores existentes contra un servidor y datos de prueba aislados."""
from datetime import timedelta
import importlib.util
import json
from pathlib import Path

import pytest
from django.utils import timezone

from gestion.models import Atencion, Carta, GestionTubo, ItemMeta

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize('name', ['check_tableros', 'check_design', 'check_usability'])
def test_script_existente_con_datos_ficticios(mundo, live_server, tmp_path, name):
    api = pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip('Requiere python -m playwright install chromium.')
    root = Path(__file__).resolve().parents[1]
    credentials = [{'usuario': alias, 'password': 'Ensayo#Privado2026'} for alias in mundo['users']]
    for path in [tmp_path / '.private/cuentas-demo.json', tmp_path / '.private/tablero/demo.json']:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(credentials))
        path.chmod(0o600)
    for number in range(2):
        ItemMeta.objects.create(delegacion=mundo['a'], nombre=f'Meta ficticia {number}', unidad_medida='Atenciones')
    Atencion.objects.create(delegacion=mundo['a'], tipo=mundo['tipo_a'], subatencion=mundo['sub_a'],
        responsable=mundo['users']['editor_a'], solicitante_nombre='Vecina ficticia', solicitante_rut='12345678-5',
        descripcion='Verificación local')
    yesterday = timezone.localdate() - timedelta(days=1)
    for number in range(3):
        Carta.objects.create(delegacion=mundo['a'], nombre='VERIFICACION - Carta atrasada' if number == 0 else f'Carta ficticia {number}',
            numero_ingreso=f'OP-CHECK-{number}', remite='Organización ficticia', encargado=mundo['users']['editor_a'],
            fecha_actividad=yesterday)
    GestionTubo.objects.create(delegacion=mundo['a'], nombre='VERIFICACION - Gestión atrasada', solicitante='Vecina ficticia',
        responsable=mundo['users']['editor_a'], solicitante_telefono='912345678', estado='En proceso', fecha_compromiso=yesterday)
    spec = importlib.util.spec_from_file_location(name, root / 'tests_browser' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE = live_server.url
    module.ROOT = tmp_path
    module.OUTPUT = tmp_path / name
    module.PREFIX = 'VERIFICACION'
    module.run()
