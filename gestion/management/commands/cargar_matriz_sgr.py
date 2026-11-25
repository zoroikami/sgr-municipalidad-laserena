"""Carga los ítems, metas trimestrales y ponderadores de la matriz SGR por cargo municipal."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion.integrado import titulo_item
from gestion.models import Delegacion, ItemMeta

TUBO = 'SOLUCIONES DE INGRESOS AL TUBO'

# (nombre, ponderador, meta trimestral, unidad). La meta del indicador del tubo es el % realizado (0,8 = 80).
# Emergencia queda con meta 0 (no aplica) hasta que el delegado la configure cuando ocurra.
MATRIZ = {
    'social': ('Gestor social (hojas G SOC)', [
        ('ATENCIÓN SOCIAL A USUARIO PRESENCIAL', '0.20', 90, 'Atenciones'),
        ('VISITA TERRENO', '0.20', 12, 'Visitas'),
        ('ENTREGA INFORME', '0.25', 40, 'Informes'),
        ('ENTREGA BENEFICIO', '0.20', 8, 'Beneficios'),
        ('EMERGENCIA', '0.05', 0, 'Emergencias'),
        (TUBO, '0.10', 80, '% realizado'),
    ]),
    'organizaciones': ('Territorial OO.CC. (hojas T OC)', [
        ('ATENCIÓN DE USUARIO TELÉFONO Y PRESENCIAL', '0.15', 60, 'Atenciones'),
        ('VISITAS, REUNIONES CON ORGANIZACIONES', '0.15', 24, 'Visitas'),
        ('CONFORMACIÓN DE ORGANIZACIONES', '0.25', 1, 'Organizaciones'),
        ('GESTIÓN DE TALLERES Y ACTIVIDADES', '0.15', 6, 'Talleres'),
        ('EMERGENCIA', '0.05', 0, 'Emergencias'),
        (TUBO, '0.25', 80, '% realizado'),
    ]),
    'administrativo': ('Apoyo administrativo (hoja AP ADM)', [
        ('ATENCIÓN DE USUARIO TELÉFONO Y PRESENCIAL', '0.20', 240, 'Atenciones'),
        ('LLAMADAS PREVENTIVAS A USUARIOS', '0.30', 90, 'Llamadas'),
        ('INFORME DE INVENTARIOS', '0.25', 1, 'Informes'),
        ('INFORME A COMUNICACIONES', '0.20', 12, 'Informes'),
        ('EMERGENCIA', '0.05', 0, 'Emergencias'),
    ]),
    'servicios': ('Coordinador DISERCO (hoja COOR DISERCO)', [
        ('INFORMES PERSONAL', '0.10', 3, 'Informes'),
        ('INFORME TRABAJO', '0.10', 12, 'Informes'),
        ('OPERATIVO DELEGACIÓN', '0.15', 24, 'Operativos'),
        ('OPERATIVO DISERCO', '0.10', 12, 'Operativos'),
        ('TALLERES', '0.10', 12, 'Talleres'),
        ('TERRENO', '0.10', 24, 'Salidas'),
        ('ATENCIÓN REQUERIMIENTO USUARIO', '0.15', 24, 'Atenciones'),
        ('EMERGENCIA', '0.05', 0, 'Emergencias'),
        (TUBO, '0.15', 80, '% realizado'),
    ]),
    'planificacion': ('Planificación y control (hoja PLAN y CON)', [
        ('REUNIÓN SEMANAL CON EL EQUIPO', '0.15', 12, 'Reuniones'),
        ('SOLUCIÓN DE PROBLEMAS A USUARIOS PARTICULARES', '0.30', 8, 'Casos'),
        ('EMERGENCIA', '0.05', 0, 'Emergencias'),
        (TUBO, '0.35', 80, '% realizado'),
    ]),
    # Seguridad: la hoja SALON (bloque G SEGUR) puntúa con sus propias metas y ponderadores y toma el avance
    # de GES SEG; las celdas de cumplimiento de GES SEG apuntan a filas equivocadas (H6 a H9) y su total omite
    # filas, por eso rige SALON. «Salidas a terreno» no pondera en SALON: queda con ponderador 0, informativo.
    'seguridad': ('Gestor de seguridad ciudadana (hoja SALON, bloque G SEGUR)', [
        ('FORMACIÓN DE COMITÉS DE SEGURIDAD', '0.25', 6, 'Comités'),
        ('LEVANTAMIENTO DE INCIVILIDADES', '0.25', 45, 'Levantamientos'),
        ('GESTIÓN DE MEDIACIÓN', '0.10', 12, 'Mediaciones'),
        ('RECUPERACIÓN DE ESPACIOS PÚBLICOS', '0.10', 50, 'Espacios'),
        ('INFRACCIONES VARIAS', '0.15', 60, 'Infracciones'),
        ('SALIDAS A TERRENO', '0', 45, 'Salidas'),
        (TUBO, '0.15', 80, '% realizado'),
    ]),
}

# Valores que cargó la versión anterior del comando. --actualizar solo cambia ítems que aún los conservan,
# para no pisar lo que un delegado haya configurado con «Configurar meta».
ANTERIORES = {
    'seguridad': {
        'FORMACIÓN DE COMITÉS DE SEGURIDAD': ('0.20', 36), 'LEVANTAMIENTO DE INCIVILIDADES': ('0.20', 40),
        'GESTIÓN DE MEDIACIÓN': ('0.10', 50), 'INFRACCIONES VARIAS': ('0.15', 45), 'SALIDAS A TERRENO': ('0.10', 45),
    },
}


class Command(BaseCommand):
    help = 'Carga los ítems de la matriz SGR por cargo en una delegación. Sin --aplicar solo simula.'

    def add_arguments(self, parser):
        parser.add_argument('--delegacion', type=int, required=True)
        parser.add_argument('--aplicar', action='store_true')
        parser.add_argument('--actualizar', action='store_true',
            help='Actualiza meta y ponderador de los ítems que conservan los valores de la versión anterior.')
        parser.add_argument('--desactivar-comunes', action='store_true',
            help='Deja inactivos los ítems sin cargo de la delegación para que solo rija la matriz por cargo.')

    def handle(self, *args, delegacion, aplicar, desactivar_comunes=False, actualizar=False, **options):
        org = Delegacion.objects.filter(pk=delegacion).first()
        if org is None:
            raise CommandError('La delegación indicada no existe.')
        creados = existentes = actualizados = 0
        conservados = []
        with transaction.atomic():
            for cargo, (hoja, items) in MATRIZ.items():
                for nombre, ponderador, meta, unidad in items:
                    # El nombre es único por delegación: se distingue el ítem común de cada cargo.
                    titulo = titulo_item(cargo, nombre)
                    actual = ItemMeta.all_objects.filter(delegacion=org, nombre=titulo).first()
                    if actual is not None:
                        existentes += 1
                        nuevo = (Decimal(ponderador) * 100, meta)
                        if actualizar and (actual.ponderador, actual.meta_cantidad) != nuevo:
                            previo = ANTERIORES.get(cargo, {}).get(nombre)
                            if previo and (actual.ponderador, actual.meta_cantidad) == (Decimal(previo[0]) * 100, previo[1]):
                                actual.ponderador, actual.meta_cantidad = nuevo
                                actual.descripcion = f'Matriz SGR, {hoja}.'
                                actual.save(update_fields=['ponderador', 'meta_cantidad', 'descripcion', 'updated_at'])
                                actualizados += 1
                            else:
                                conservados.append(titulo)
                        continue
                    ItemMeta.objects.create(
                        delegacion=org, cargo_sgr=cargo, nombre=titulo, unidad_medida=unidad, meta_cantidad=meta,
                        ponderador=Decimal(ponderador) * 100, indicador='tubo' if nombre == TUBO else 'cantidad',
                        descripcion=f'Matriz SGR, {hoja}.')
                    creados += 1
            inactivos = 0
            if desactivar_comunes:
                inactivos = ItemMeta.objects.filter(delegacion=org, cargo_sgr='', estado='Activo').update(estado='Inactivo')
            if not aplicar:
                transaction.set_rollback(True)
        modo = 'Aplicado' if aplicar else 'Simulación (sin cambios)'
        self.stdout.write(f'{modo}: {creados} ítems nuevos, {existentes} ya existentes, {actualizados} actualizados, '
                          f'{inactivos} ítems comunes desactivados en {org.nombre}.')
        for titulo in conservados:
            self.stdout.write(f'  Se conserva (configurado por el delegado): {titulo}')
