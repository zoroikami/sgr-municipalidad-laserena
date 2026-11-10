"""Create a separate global operator without elevating any evaluation account."""
from pathlib import Path
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cuentas.models import Perfil
from gestion.management.commands.seed_demo import write_credentials


class Command(BaseCommand):
    help = 'Crear superadministrador global; conservar cuentas y contraseñas existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--credentials-file', default='.private/superadmin.json')

    def handle(self, *args, **options):
        path = Path(options['credentials_file']).resolve()
        with transaction.atomic():
            user = get_user_model().objects.filter(username=options['username']).first()
            if user:
                if not (user.is_superuser and user.is_staff and user.is_active):
                    raise CommandError('Ese usuario ya existe sin acceso global activo; no se alteró la cuenta.')
                self.stdout.write('El superadministrador ya existe; se conservó su contraseña.')
                return
            if path.exists():
                raise CommandError('El archivo de credenciales ya existe; utiliza otro archivo para no sobrescribirlo.')
            password = secrets.token_urlsafe(24)
            user = get_user_model().objects.create_superuser(options['username'], password=password,
                first_name='Superadministrador', last_name='SGR')
            Perfil.objects.create(user=user)
            write_credentials(path, [{'usuario': user.username, 'password': password,
                'rol': 'Superadministrador', 'ambito': 'Todas las delegaciones y roles'}])
        self.stdout.write(f'Superadministrador creado. Credenciales solo en {path}.')
