"""Carga el catálogo de atención social de la matriz SGR: tipos de atención y subatenciones.

La hoja LISTA define las subatenciones de «Informes sociales» y «Gestión de subsidios». Las listas desplegables
de las hojas G SOC (columnas TIPO ATENCION y SUB ATENCION) agregan los demás tipos; ahí se asocian solo los
pares evidentes, porque esas dos listas no están enlazadas en la planilla.
"""
import re
import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion.models import Delegacion, SubAtencion, TipoAtencion

# Tipo de atención: [(subatención, forma de la ayuda de la hoja LISTA o None)].
CATALOGO = {
    'Informes sociales': [('Informe aporte económico', 'Dinero'), ('Informe aporte material', 'Material'),
                          ('Informe institución', 'Documento')],
    'Gestión de subsidios': [('IPS', 'Documento'), ('PGU', 'Aporte'), ('SUF', 'Aporte'), ('SAP', 'Aporte'),
                             ('Exención pago aseo domiciliario', None)],
    # El nombre de la subatención es único por delegación: se distinguen las de derivación.
    'Derivaciones': [('Derivación con orientación social', None), ('Otras derivaciones', None)],
    'Otras gestiones sociales': [('Orientación social', None), ('Otras gestiones', None)],
    'Entrega de emergencia': [('Emergencia', None)],
}


def clave(texto):
    """Compara nombres sin distinguir mayúsculas, tildes ni espacios repetidos."""
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', texto).strip().casefold()


class Command(BaseCommand):
    help = 'Carga el catálogo social de la hoja LISTA en una o todas las delegaciones. Sin --aplicar solo simula.'

    def add_arguments(self, parser):
        destino = parser.add_mutually_exclusive_group(required=True)
        destino.add_argument('--delegacion', type=int)
        destino.add_argument('--todas', action='store_true', help='Todas las delegaciones activas.')
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, *args, delegacion=None, todas=False, aplicar=False, **options):
        orgs = Delegacion.objects.filter(estado='Activo') if todas else Delegacion.objects.filter(pk=delegacion)
        if not orgs.exists():
            raise CommandError('La delegación indicada no existe.')
        tipos_nuevos = subs_nuevas = existentes = 0
        with transaction.atomic():
            for org in orgs:
                tipos = {clave(t.nombre): t for t in TipoAtencion.all_objects.filter(delegacion=org)}
                for nombre_tipo, subatenciones in CATALOGO.items():
                    tipo = tipos.get(clave(nombre_tipo))
                    if tipo is None:
                        tipo = TipoAtencion.objects.create(delegacion=org, nombre=nombre_tipo,
                            descripcion='Catálogo de atención social de la matriz SGR (hojas LISTA y G SOC).')
                        tipos_nuevos += 1
                    else:
                        existentes += 1
                        if tipo.deleted_at or tipo.estado != 'Activo':
                            # Un tipo archivado o inactivo lo decidió alguien: no se reactiva ni se duplica.
                            self.stdout.write(f'{org.nombre}: «{tipo.nombre}» está archivado o inactivo; se omite.')
                            continue
                    propias = {clave(s.nombre) for s in SubAtencion.all_objects.filter(delegacion=org, tipo=tipo)}
                    otras = {clave(s.nombre) for s in SubAtencion.all_objects.filter(delegacion=org).exclude(tipo=tipo)}
                    for nombre, forma in subatenciones:
                        if clave(nombre) in propias:
                            existentes += 1
                            continue
                        if clave(nombre) in otras:
                            self.stdout.write(f'{org.nombre}: «{nombre}» ya existe en otro tipo de atención; se omite.')
                            continue
                        origen = (f'Hoja LISTA de la matriz SGR. Forma de la ayuda: {forma.lower()}.' if forma
                                  else 'Lista desplegable de las hojas G SOC de la matriz SGR.')
                        SubAtencion.objects.create(delegacion=org, tipo=tipo, nombre=nombre, descripcion=origen)
                        subs_nuevas += 1
            if not aplicar:
                transaction.set_rollback(True)
        modo = 'Aplicado' if aplicar else 'Simulación (sin cambios)'
        self.stdout.write(f'{modo}: {tipos_nuevos} tipos y {subs_nuevas} subatenciones nuevas, {existentes} ya existentes '
                          f'en {orgs.count()} delegación(es).')
