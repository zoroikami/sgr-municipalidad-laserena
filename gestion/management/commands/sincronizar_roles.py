from django.core.management.base import BaseCommand
from gestion.permissions import sync_all_users

class Command(BaseCommand):
    help = 'Sincroniza los grupos y permisos Django con los roles SGR existentes, sin crear cuentas.'

    def handle(self, *args, **options):
        sync_all_users()
        self.stdout.write(self.style.SUCCESS('Permisos de roles sincronizados.'))
