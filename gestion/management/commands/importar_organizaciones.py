"""Importación explícita de la base de JJVV y organizaciones; nunca publica la planilla original.

Modos:
- `--delegacion N --territorio X`: un territorio exacto hacia una delegación.
- `--todas`: cada territorio de la planilla hacia su delegación (TERRITORIOS). Las filas sin territorio
  se informan y no se importan: no se adivina su delegación.
Sin `--aplicar` solo simula. Un nombre ya registrado en la delegación (incluso archivado) no se duplica.
"""
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from unicodedata import normalize

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from gestion.models import Delegacion, Organizacion

# Territorio de la planilla (columna TERRIT. DELEG.) -> nombre de la delegación.
TERRITORIOS = {
    'CIAS': 'LAS COMPANIAS', 'CENTRO': 'CENTRO', 'PAMPA': 'LA PAMPA', 'RURAL': 'RURAL',
    'ANTENA': 'LA ANTENA - LA FLORIDA', 'ALFALFARES': 'LA ANTENA - LA FLORIDA', 'AV DEL MAR': 'AVENIDA DEL MAR',
}

# Orden relevante: lo específico antes que lo genérico (vivienda y agua antes de «comité»).
CLASIFICACION = [
    (r'\bJUNTAS? DE VECINOS\b|\bJJ\.? ?VV\b|\bJ\.J\.V\.V\b', 'territorial', 'Junta de vecinos'),
    (r'\bVIVIENDA|\bALLEGAD', 'funcional', None),
    (r'\bAGUA POTABLE|\bAPR\b', 'funcional', 'Comité de agua potable rural'),
    (r'\bADULTOS? MAYOR|\bTERCERA EDAD|\bABUELIT', 'funcional', 'Club de adulto mayor'),
    (r'\bPADRES Y APODERADOS|\bCENTRO GENERAL DE PADRES', 'funcional', 'Centro de padres y apoderados'),
    (r'\bDEPORT|\bFUTBOL|\bFUTSAL|\bBASQUET|\bTAEKWON|\bKARATE|\bCICLIS|\bATLETI', 'funcional', 'Organización deportiva'),
    (r'\bCENTRO DE MADRES\b', 'funcional', 'Centro de madres'),
    (r'\bCULTUR|\bFOLCLOR|\bFOLKLOR|\bBAILE|\bCORO\b|\bTEATR|\bMUSIC|\bARTISTIC', 'funcional', 'Centro cultural'),
    (r'\bJUVEN', 'funcional', 'Agrupación juvenil'),
    (r'\bSEGURIDAD|\bDELINCUENCIA', 'funcional', 'Comité de seguridad'),
    (r'\bCOMITE', 'funcional', 'Comité de vecinos'),
]


def texto(value):
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value or '').strip()


def canon(value):
    limpio = ''.join(c for c in normalize('NFD', texto(value).upper()) if not '̀' <= c <= 'ͯ')
    return ' '.join(limpio.split())


def fecha(value):
    return value.date() if isinstance(value, datetime) else value if isinstance(value, date) else None


def clasificar(nombre):
    value = canon(nombre)
    for patron, familia, categoria in CLASIFICACION:
        if re.search(patron, value):
            if categoria is None:
                categoria = 'Comité de allegados' if 'ALLEGAD' in value else 'Comité de vivienda'
            return familia, categoria
    return 'funcional', 'Por clasificar'


class Command(BaseCommand):
    help = 'Importa organizaciones sin verificar por territorio (o todas con --todas). Sin --aplicar solo simula.'

    def add_arguments(self, parser):
        parser.add_argument('archivo')
        parser.add_argument('--delegacion', type=int)
        parser.add_argument('--territorio')
        parser.add_argument('--todas', action='store_true', help='Importa cada territorio en su delegación.')
        parser.add_argument('--aplicar', action='store_true', help='Sin esta opción solo simula.')

    def destinos(self, options):
        if options['todas']:
            if options['delegacion'] or options['territorio']:
                raise CommandError('Usa --todas o bien --delegacion y --territorio, no ambos.')
            activas = {canon(d.nombre): d for d in Delegacion.objects.filter(estado='Activo')}
            faltantes = sorted({nombre for nombre in TERRITORIOS.values() if nombre not in activas})
            if faltantes:
                raise CommandError(f'Faltan delegaciones activas: {", ".join(faltantes)}.')
            return {territorio: activas[nombre] for territorio, nombre in TERRITORIOS.items()}
        if not options['delegacion'] or not options['territorio']:
            raise CommandError('Indica --delegacion y --territorio, o usa --todas.')
        delegacion = Delegacion.objects.filter(pk=options['delegacion'], estado='Activo').first()
        if not delegacion:
            raise CommandError('Selecciona una delegación activa.')
        return {canon(options['territorio']): delegacion}

    def handle(self, *args, **options):
        destinos = self.destinos(options)
        try:
            book = load_workbook(options['archivo'], read_only=True, data_only=True)
        except (OSError, ValueError) as exc:
            raise CommandError('No se pudo abrir la planilla.') from exc
        creadas, existentes, sin_territorio = Counter(), Counter(), []
        territorios_desconocidos, subfamilias, registros_pj = Counter(), Counter(), defaultdict(set)
        try:
            sheet = book['juntas de vecinos']
            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, max_col=8, values_only=True):
                    if not row or not row[0]:
                        continue
                    nombre, territorio = ' '.join(texto(row[0]).split()), canon(row[2])
                    if not territorio:
                        sin_territorio.append(nombre)
                        continue
                    delegacion = destinos.get(territorio)
                    if delegacion is None:
                        if options['todas']:
                            territorios_desconocidos[territorio] += 1
                        continue
                    if texto(row[5]).isdigit():
                        registros_pj[texto(row[5])].add(nombre)
                    # No truncar ni reactivar datos archivados; tampoco repetir un nombre en la delegación.
                    if Organizacion.all_objects.filter(delegacion=delegacion, nombre__iexact=nombre).exists():
                        existentes[delegacion.nombre] += 1
                        continue
                    familia, subfamilia = clasificar(nombre)
                    obj = Organizacion(delegacion=delegacion, nombre=nombre, familia=familia, subfamilia=subfamilia,
                        domicilio=texto(row[1]), socios_activos=int(row[3]) if isinstance(row[3], (int, float)) and row[3] >= 0 else None,
                        fecha_constitucion=fecha(row[4]), registro_pj=texto(row[5]), fecha_inscripcion=fecha(row[6]),
                        registro_directiva=texto(row[7]), verificada=False)
                    obj.full_clean()
                    obj.save()
                    creadas[delegacion.nombre] += 1
                    subfamilias[subfamilia] += 1
                if not options['aplicar']:
                    transaction.set_rollback(True)
        except (KeyError, ValueError) as exc:
            raise CommandError('La estructura de la planilla no corresponde al formato de organizaciones.') from exc
        finally:
            book.close()
        modo = 'Importadas' if options['aplicar'] else 'Simuladas'
        self.stdout.write(f'{modo}: {sum(creadas.values())}. Existentes omitidas: {sum(existentes.values())}.')
        if options['todas']:
            for nombre in sorted(set(creadas) | set(existentes)):
                self.stdout.write(f'  {nombre}: {creadas[nombre]} nuevas, {existentes[nombre]} ya registradas.')
            self.stdout.write('Subfamilias: ' + ', '.join(f'{k} {v}' for k, v in subfamilias.most_common()))
            if sin_territorio:
                self.stdout.write(f'Sin territorio (no importadas, revisar en la planilla): {len(sin_territorio)}.')
                for nombre in sin_territorio:
                    self.stdout.write(f'  - {nombre}')
            for territorio, cantidad in territorios_desconocidos.items():
                self.stdout.write(f'Territorio sin delegación asignada «{territorio}»: {cantidad} filas.')
            repetidos = {pj: nombres for pj, nombres in registros_pj.items() if len(nombres) > 1}
            for pj, nombres in sorted(repetidos.items()):
                self.stdout.write(f'Registro P.J. {pj} repetido en organizaciones distintas: {"; ".join(sorted(nombres))}.')
