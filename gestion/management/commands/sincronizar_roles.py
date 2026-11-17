from django.core.management.base import BaseCommand
from cuentas.roles import configure_groups


class Command(BaseCommand):
    help = 'Restablece los permisos predeterminados de los roles municipales después de migrar.'

    def handle(self, *args, **options):
        configure_groups()
        self.stdout.write('Roles municipales actualizados.')
