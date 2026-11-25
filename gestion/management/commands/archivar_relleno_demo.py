"""Archiva los ítems ficticios inactivos de seed_demo («Social: meta territorial 01»…) que ensucian el listado de metas."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from gestion.models import ActividadSGR, ItemMeta


class Command(BaseCommand):
    help = ('Archiva los ítems de relleno de seed_demo que ya están inactivos. Los que tienen actividades quedan '
            'como están. Sin --aplicar solo simula; el archivo se puede revertir.')

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, *args, aplicar=False, **options):
        relleno = ItemMeta.objects.filter(codigo_anterior__startswith='IT-DEMO-', estado='Inactivo')
        usados = set(ActividadSGR.objects.filter(item__in=relleno).values_list('item_id', flat=True))
        archivables = relleno.exclude(pk__in=usados)
        cantidad = archivables.count()
        if aplicar:
            with transaction.atomic():
                archivables.update(deleted_at=timezone.now(), updated_at=timezone.now())
        modo = 'Aplicado' if aplicar else 'Simulación (sin cambios)'
        self.stdout.write(f'{modo}: {cantidad} ítems de relleno archivados; {len(usados)} con actividades se mantienen.')
