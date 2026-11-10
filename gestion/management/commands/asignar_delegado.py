from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Asigna la atribución municipal de delegado sin cambiar el rol de acceso del funcionario.'

    def add_arguments(self, parser):
        parser.add_argument('usuario')

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['usuario'], is_active=True).first()
        if not user or not hasattr(user, 'perfil') or not user.perfil.delegacion_id:
            raise CommandError('Selecciona un funcionario activo con delegación asignada.')
        if not user.has_perm('gestion.add_ausenciasgr') or not user.has_perm('gestion.change_itemmeta'):
            raise CommandError('Primero asigna un rol de Editor o Administrador al funcionario.')
        user.user_permissions.add(Permission.objects.get(content_type__app_label='gestion', codename='validar_delegado'))
        self.stdout.write('Atribución de delegado asignada.')
