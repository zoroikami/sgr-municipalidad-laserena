"""Exportación a Excel con la identidad municipal: franja institucional, contexto de la consulta y tabla ordenada.

Cada celda de datos se escribe como texto: lo que un usuario escribió con =, +, - o @ nunca se ejecuta como fórmula.
"""
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .delegation import active_delegation, has_global_scope

# Paleta institucional (assets/municipal/README.md) y tonos de estado de la aplicación.
ROJO, ROJO_OSCURO, TINTA, GRIS = 'C41230', '8B1D19', '302526', '6A6263'
FONDO_ALTERNO, LINEA = 'FBF4F4', 'EBDCDB'
TONOS_ESTADO = {
    'verde': ('E4F3E8', '1E5631'), 'ambar': ('FFF3D6', '7A4B00'), 'azul': ('E7F0FA', '1D4E89'),
    'rojo': ('FBE7E8', '8B1D19'), 'gris': ('F1EDED', '4F4748'),
}
ESTADOS = {
    'Activo': 'verde', 'Activa': 'verde', 'Resuelta': 'verde', 'Realizado': 'verde', 'Finalizada': 'verde', 'Cerrado': 'verde',
    'En proceso': 'ambar', 'En gestión': 'ambar',
    'Ingresada': 'azul', 'Ingresado': 'azul', 'Aprobada': 'azul', 'Abierto': 'azul',
    'Pendiente': 'rojo',
    'Inactivo': 'gris', 'Inactiva': 'gris', 'No aplica': 'gris',
}
FILA_ENCABEZADO = 6  # filas 1-4: identidad y contexto; fila 5: aire; desde la 6: la tabla
ANCHO_MINIMO, ANCHO_MAXIMO = 10, 60
FUENTE = 'Arial'  # la tipografía de respaldo del sitio; disponible en cualquier equipo


def _ambito(user):
    if has_global_scope(user):
        elegida = active_delegation(user)
        if elegida is None:
            return 'Todas las delegaciones'
        from .models import Delegacion
        return Delegacion.objects.filter(pk=elegida).values_list('nombre', flat=True).first() or 'Delegación seleccionada'
    perfil = getattr(user, 'perfil', None)
    return getattr(getattr(perfil, 'delegacion', None), 'nombre', '') or 'Sin delegación'


def _filtros(user, modulo, state):
    from django.contrib.auth import get_user_model
    from .access import scoped
    from .models import TipoAtencion
    partes = []
    if state.get('q'):
        partes.append(f'Búsqueda «{state["q"]}»')
    if state.get('estado'):
        partes.append(f'Estado: {state["estado"]}')
    if modulo == 'atenciones':
        if str(state.get('tipo', '')).isdigit():
            nombre = scoped(user, TipoAtencion).filter(pk=state['tipo']).values_list('nombre', flat=True).first()
            if nombre:
                partes.append(f'Tipo: {nombre}')
        if str(state.get('responsable', '')).isdigit():
            cuenta = get_user_model().objects.filter(pk=state['responsable']).first()
            if cuenta:
                partes.append(f'Responsable: {cuenta.get_full_name() or cuenta.username}')
        if state.get('desde'):
            partes.append(f'Desde {state["desde"]}')
        if state.get('hasta'):
            partes.append(f'Hasta {state["hasta"]}')
    return ' · '.join(partes) if partes else 'Sin filtros: todos los registros vigentes del ámbito.'


def libro_excel(request, modulo, titulo, columnas, filas):
    """Devuelve el .xlsx: `filas` entrega listas de textos ya formateados, en el orden de `columnas`."""
    from .queries import state_for
    state, _ = state_for(request, modulo)
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo[:31]
    total_columnas = len(columnas)
    ultima = get_column_letter(total_columnas)
    linea = Side(style='thin', color=LINEA)

    # Identidad municipal y contexto de la consulta.
    hoja.merge_cells(f'A1:{ultima}1')
    hoja['A1'] = 'Ilustre Municipalidad de La Serena · Sistema de Gestión de Resultados'
    hoja['A1'].font = Font(name=FUENTE, bold=True, color='FFFFFF', size=12)
    hoja['A1'].fill = PatternFill('solid', fgColor=ROJO)
    hoja['A1'].alignment = Alignment(vertical='center', indent=1)
    for columna in range(2, total_columnas + 1):
        hoja.cell(row=1, column=columna).fill = PatternFill('solid', fgColor=ROJO)
    hoja.row_dimensions[1].height = 26
    hoja['A2'] = titulo
    hoja['A2'].font = Font(name=FUENTE, bold=True, color=ROJO_OSCURO, size=16)
    hoja.row_dimensions[2].height = 26
    usuario = request.user.get_full_name() or request.user.username
    ahora = timezone.localtime()
    registros = 0
    cuerpo = []
    for fila in filas:
        cuerpo.append(fila)
        registros += 1
    hoja['A3'] = (f'{_ambito(request.user)} · {registros} registro{"s" if registros != 1 else ""} · '
                  f'Exportado el {ahora:%d-%m-%Y} a las {ahora:%H:%M} por {usuario}')
    hoja['A3'].font = Font(name=FUENTE, color=GRIS, size=10)
    hoja['A4'] = _filtros(request.user, modulo, state)
    hoja['A4'].font = Font(name=FUENTE, color=GRIS, size=10, italic=True)
    for celda in ('A2', 'A3', 'A4'):
        hoja[celda].data_type = 's'
    hoja.row_dimensions[5].height = 6

    # Encabezado de la tabla.
    for indice, (etiqueta, _) in enumerate(columnas, start=1):
        celda = hoja.cell(row=FILA_ENCABEZADO, column=indice, value=etiqueta)
        celda.font = Font(name=FUENTE, bold=True, color='FFFFFF')
        celda.fill = PatternFill('solid', fgColor=ROJO_OSCURO)
        celda.alignment = Alignment(vertical='center', wrap_text=True)
        celda.border = Border(bottom=linea)
    hoja.row_dimensions[FILA_ENCABEZADO].height = 30

    # Datos: texto siempre, filas alternadas y estados con su tono.
    anchos = [len(str(etiqueta)) for etiqueta, _ in columnas]
    columna_estado = next((i for i, (_, clave) in enumerate(columnas) if clave == 'estado'), None)
    for desplazamiento, valores in enumerate(cuerpo, start=1):
        numero = FILA_ENCABEZADO + desplazamiento
        fondo = PatternFill('solid', fgColor=FONDO_ALTERNO) if desplazamiento % 2 == 0 else None
        for indice, valor in enumerate(valores):
            texto = '' if valor is None else str(valor)
            celda = hoja.cell(row=numero, column=indice + 1)
            celda.value = texto
            celda.data_type = 's'
            celda.font = Font(name=FUENTE, color=TINTA)
            celda.alignment = Alignment(vertical='top', wrap_text=len(texto) > ANCHO_MAXIMO)
            celda.border = Border(bottom=linea)
            tono = ESTADOS.get(texto) if indice == columna_estado else None
            if tono:
                relleno, letra = TONOS_ESTADO[tono]
                celda.fill = PatternFill('solid', fgColor=relleno)
                celda.font = Font(name=FUENTE, color=letra, bold=True)
            elif fondo:
                celda.fill = fondo
            anchos[indice] = max(anchos[indice], min(len(texto), ANCHO_MAXIMO))

    for indice, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = max(ANCHO_MINIMO, min(ancho + 3, ANCHO_MAXIMO))
    ultima_fila = FILA_ENCABEZADO + max(registros, 1)
    hoja.auto_filter.ref = f'A{FILA_ENCABEZADO}:{ultima}{ultima_fila}'
    hoja.freeze_panes = f'A{FILA_ENCABEZADO + 1}'
    hoja.sheet_view.showGridLines = False

    # Impresión: horizontal, ajustada al ancho y con el encabezado en cada página.
    hoja.page_setup.orientation = 'landscape'
    hoja.page_setup.fitToWidth, hoja.page_setup.fitToHeight = 1, 0
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.print_title_rows = f'{FILA_ENCABEZADO}:{FILA_ENCABEZADO}'
    hoja.oddFooter.center.text = f'{titulo} · página &P de &N'
    hoja.oddFooter.right.text = 'Municipalidad de La Serena'

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
