"""Importación explícita por territorio; nunca publica la planilla original."""
from datetime import date, datetime
from unicodedata import normalize

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from gestion.models import Delegacion, Organizacion


def texto(value):
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value or '').strip()


def canon(value):
    return ''.join(c for c in normalize('NFD', texto(value).upper()) if not '\u0300' <= c <= '\u036f')


def fecha(value):
    return value.date() if isinstance(value, datetime) else value if isinstance(value, date) else None


def clasificar(nombre):
    value = canon(nombre)
    if 'JUNTA DE VECINOS' in value or 'JJVV' in value or 'J.J.V.V' in value:
        return 'territorial', 'Junta de vecinos'
    for patron, categoria in [('ADULTO MAYOR', 'Club de adulto mayor'), ('DEPORT', 'Organización deportiva'),
                              ('CENTRO DE MADRES', 'Centro de madres'), ('CULTUR', 'Centro cultural'),
                              ('JUVEN', 'Agrupación juvenil'), ('SEGURIDAD', 'Comité de seguridad'),
                              ('ALLEGAD', 'Comité de allegados'), ('COMITE', 'Comité de vecinos')]:
        if patron in value:
            return 'funcional', categoria
    return 'funcional', 'Por clasificar'


class Command(BaseCommand):
    help = 'Importa organizaciones sin verificar. Selecciona un territorio exacto y una delegación destino.'

    def add_arguments(self, parser):
        parser.add_argument('archivo')
        parser.add_argument('--delegacion', required=True, type=int)
        parser.add_argument('--territorio', required=True)
        parser.add_argument('--aplicar', action='store_true', help='Sin esta opción solo simula.')

    def handle(self, *args, **options):
        delegacion = Delegacion.objects.filter(pk=options['delegacion'], estado='Activo').first()
        if not delegacion:
            raise CommandError('Selecciona una delegación activa.')
        try:
            book = load_workbook(options['archivo'], read_only=True, data_only=True)
        except (OSError, ValueError) as exc:
            raise CommandError('No se pudo abrir la planilla.') from exc
        count, repetidos = 0, 0
        try:
            sheet = book['juntas de vecinos']
            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, max_col=8, values_only=True):
                    if not row[0] or canon(row[2]) != canon(options['territorio']):
                        continue
                    nombre = texto(row[0])
                    # No truncar ni reactivar datos archivados.
                    if Organizacion.all_objects.filter(delegacion=delegacion, nombre__iexact=nombre).exists():
                        repetidos += 1
                        continue
                    familia, subfamilia = clasificar(nombre)
                    obj = Organizacion(delegacion=delegacion, nombre=nombre, familia=familia, subfamilia=subfamilia,
                        domicilio=texto(row[1]), socios_activos=int(row[3]) if isinstance(row[3], (int, float)) and row[3] >= 0 else None,
                        fecha_constitucion=fecha(row[4]), registro_pj=texto(row[5]), fecha_inscripcion=fecha(row[6]),
                        registro_directiva=texto(row[7]), verificada=False)
                    obj.full_clean()
                    obj.save()
                    count += 1
                if not options['aplicar']:
                    transaction.set_rollback(True)
        except (KeyError, ValueError) as exc:
            raise CommandError('La estructura de la planilla no corresponde al formato de organizaciones.') from exc
        finally:
            book.close()
        self.stdout.write(f"{'Importadas' if options['aplicar'] else 'Simuladas'}: {count}. Existentes omitidas: {repetidos}.")
