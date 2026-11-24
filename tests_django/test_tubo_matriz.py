"""Hojas TUBO de la matriz SGR (revisión 3er trimestre): avance por colaborador y territorios sugeridos."""
import pytest
from django.urls import reverse

from gestion.models import GestionTubo

pytestmark = pytest.mark.django_db


def test_tablero_resume_el_avance_por_colaborador(client, mundo):
    editor, admin = mundo['users']['editor_a'], mundo['users']['admin_a']
    for n, (responsable, estado) in enumerate([(editor, 'Realizado'), (editor, 'Ingresado'), (editor, 'Realizado'),
                                                (admin, 'Pendiente')]):
        GestionTubo.objects.create(delegacion=mundo['a'], nombre=f'Gestión {n}', solicitante='Vecino',
                                   responsable=responsable, estado=estado)
    GestionTubo.objects.create(delegacion=mundo['b'], nombre='Ajena', solicitante='Vecino',
                               responsable=mundo['users']['lector_b'], estado='Realizado')
    client.force_login(editor)
    response = client.get(reverse('gestion:tablero'))
    filas = {c['nombre']: c for c in response.context['colaboradores']}
    assert set(filas) == {'editor_a', 'admin_a'}
    assert filas['editor_a']['conteos'] == [1, 0, 0, 2] and round(filas['editor_a']['porcentaje']) == 67
    html = response.content.decode()
    assert 'Avance por colaborador' in html
    # Los conteos por estado se muestran solo en las columnas, no repetidos en el resumen.
    assert 'En proceso activo' not in html and 'Pendientes / alerta' not in html
    assert 'Tasa de resolución' in html and '2 de 4 realizadas' in html


def test_territorio_sugiere_la_lista_de_la_delegacion_y_los_usados(client, mundo):
    GestionTubo.objects.create(delegacion=mundo['b'], nombre='Previa', solicitante='Vecino',
                               responsable=mundo['users']['lector_b'], territorio='  toqui ')
    GestionTubo.objects.create(delegacion=mundo['b'], nombre='Otra', solicitante='Vecino',
                               responsable=mundo['users']['lector_b'], territorio='Villa Lambert')
    client.force_login(mundo['users']['coordinador'])
    html = client.get(reverse('gestion:crear', args=['tubo']), {'delegacion': mundo['b'].pk}).content.decode()
    assert 'list="id_territorio_sugerencias"' in html
    for territorio in ('Latorre', 'Rukalaf', 'Toqui', 'Zorrilla', 'Villa Lambert'):
        assert f'<option value="{territorio}">' in html
    assert html.count('value="Toqui"') + html.count('value="toqui"') == 1
