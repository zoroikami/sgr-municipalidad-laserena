import datetime
import json
import os
from pathlib import Path
import secrets
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cuentas.models import Perfil
from cuentas.roles import configure_groups
from gestion.models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion

DELEGACIONES = [('DEL01', 'Centro'), ('DEL02', 'Las Compañías'), ('DEL03', 'La Pampa'),
                ('DEL04', 'La Antena - La Florida'), ('DEL05', 'Rural'), ('DEL06', 'Avenida del Mar')]
ACCOUNTS = [('admin_a', 'Administrador', 0, 'Keoni Vergara'),
            ('editor_a', 'Editor', 0, 'Harold Concha'), ('lector_a', 'Lector', 0, 'Marcos Ortiz'),
            ('lector_b', 'Lector', 1, 'Claudio Romo'),
            ('cliente_1', 'Cliente', 0, 'Javier Ahumada'), ('cliente_2', 'Cliente', 0, 'Jorge Cortes')]


def fictitious_rut(number):
    body = str(number)
    digit = 11 - sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(body))) % 11
    return body + '-' + ('0' if digit == 11 else 'K' if digit == 10 else str(digit))


def write_credentials(path, accounts):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as output:
        os.chmod(output.name, 0o600)
        json.dump(accounts, output, ensure_ascii=False, indent=2)
        temporary = output.name
    os.replace(temporary, path)


class Command(BaseCommand):
    help = 'Cargar datos ficticios de revisión sin duplicarlos.'

    def add_arguments(self, parser):
        parser.add_argument('--credentials-file', default='.private/cuentas-demo.json')
        parser.add_argument('--update-names', action='store_true', help='Actualizar solo los nombres de las seis cuentas de demostración.')

    def handle(self, *args, **options):
        path = Path(options['credentials_file']).resolve()
        try:
            previous = json.loads(path.read_text()) if path.exists() else []
            if not isinstance(previous, list):
                raise ValueError
        except (ValueError, OSError) as exc:
            raise CommandError('El archivo privado de cuentas no se puede leer. Elige otro archivo o revisa sus permisos.') from exc
        created_credentials = []
        anchor = datetime.datetime(2026, 11, 6, 12, tzinfo=datetime.timezone.utc)
        with transaction.atomic():
            configure_groups()
            orgs = [Delegacion.objects.get_or_create(codigo=code, defaults={
                'nombre': name, 'direccion': f'Oficina municipal de revisión {i + 1}',
                'comuna': 'La Serena'})[0] for i, (code, name) in enumerate(DELEGACIONES)]
            users = {}
            for i, (alias, role, org_index, name) in enumerate(ACCOUNTS):
                first_name, last_name = name.split(' ', 1)
                user, created = get_user_model().objects.get_or_create(username=alias, defaults={
                    'first_name': first_name, 'last_name': last_name,
                    'email': os.environ.get(f'DEMO_EMAIL_{alias.upper()}', f'{alias}@example.test'),
                    'is_staff': False, 'is_superuser': False})
                if created:
                    password = secrets.token_urlsafe(18)
                    user.set_password(password)
                    user.save(update_fields=['password'])
                    user.groups.set([Group.objects.get(name=role)])
                    created_credentials.append({'usuario': alias, 'password': password, 'rol': role, 'ambito': orgs[org_index].nombre})
                profile, _ = Perfil.objects.get_or_create(user=user, defaults={
                    'delegacion': orgs[org_index], 'rut': fictitious_rut(22000001 + i)})
                if profile.delegacion_id != orgs[org_index].pk or user.is_superuser or user.is_staff:
                    raise CommandError(f'La cuenta {alias} ya existe con otro ámbito o privilegios técnicos. No se alteró esa cuenta.')
                if options['update_names'] and not created:
                    previous_name = user.get_full_name()
                    user.first_name, user.last_name = first_name, last_name
                    user.save(update_fields=['first_name', 'last_name'])
                    # Synchronize only unchanged demo labels; preserve edited business records.
                    Atencion.all_objects.filter(cliente=user, folio_anterior__startswith='ATN-2026-DEMO-',
                        solicitante_nombre=previous_name).update(solicitante_nombre=name)
                users[alias] = user
            services = ['Social', 'Salud', 'Educación', 'Servicios urbanos', 'Seguridad ciudadana']
            units = ['Atenciones', 'Visitas', 'Gestiones', 'Operativos']
            for d, org in enumerate(orgs, start=1):
                types = [TipoAtencion.all_objects.get_or_create(codigo_anterior=f'TA-DEMO-{d:02}-{i:02}', defaults={
                    'delegacion': org, 'nombre': label, 'descripcion': f'Catálogo ficticio para revisión de {org.nombre}',
                    'created_at': anchor - datetime.timedelta(days=180 + i)})[0] for i, label in enumerate(services)]
                subs = []
                for i in range(15):
                    sub, _ = SubAtencion.all_objects.get_or_create(codigo_anterior=f'SA-DEMO-{d:02}-{i:02}', defaults={
                        'delegacion': org, 'tipo': types[i // 3], 'nombre': f'{services[i // 3]}: gestión {i % 3 + 1}',
                        'created_at': anchor - datetime.timedelta(days=170 + i)})
                    subs.append(sub)
                for i in range(60):
                    ItemMeta.all_objects.get_or_create(codigo_anterior=f'IT-DEMO-{d:02}-{i:03}', defaults={
                        'delegacion': org, 'nombre': f'{services[i % 5]}: meta territorial {i + 1:02}',
                        'descripcion': f'Meta ficticia del sector {i % 12 + 1} de {org.nombre}',
                        'unidad_medida': units[i % len(units)], 'meta_cantidad': 100,
                        'estado': 'Inactivo' if i % 7 == 0 else 'Activo',
                        'created_at': anchor - datetime.timedelta(days=i, hours=d)})
                for i in range(300):
                    sub = subs[i % len(subs)]
                    owner = users['cliente_1'] if d == 1 and i < 30 else users['cliente_2'] if d == 1 and i < 60 else None
                    # A reader is not used as an employee in B; a seeded technical owner
                    # is unnecessary: the responsible account identifies the data origin.
                    responsible = users['editor_a'] if d == 1 else users['lector_b'] if d == 2 else None
                    if responsible is None:
                        # The six demo accounts stay in A/B. Records elsewhere have a
                        # reproducible inactive employee, excluded from demo account totals.
                        alias = f'responsable_demo_{d}'
                        responsible, created = get_user_model().objects.get_or_create(username=alias, defaults={'is_active': False, 'first_name': f'Responsable ficticio {org.nombre}'})
                        if created:
                            responsible.set_unusable_password()
                            responsible.save(update_fields=['password'])
                        Perfil.objects.get_or_create(user=responsible, defaults={'delegacion': org, 'rut': fictitious_rut(23000000 + d)})
                    Atencion.all_objects.get_or_create(folio_anterior=f'ATN-2026-DEMO-{d:02}-{i:04}', defaults={
                        'delegacion': org, 'tipo': sub.tipo, 'subatencion': sub, 'cliente': owner,
                        'responsable': responsible,
                        'solicitante_rut': owner.perfil.rut if owner else fictitious_rut(24000000 + d * 1000 + i),
                        'solicitante_nombre': owner.get_full_name() if owner else f'{["Elena", "Matías", "Antonia", "Vicente", "Camila"][i % 5]} {["Araya", "Rojas", "Tapia", "Cortés", "Olivares"][(i // 5) % 5]} {i + 1:03}',
                        'descripcion': f'Dato ficticio: {sub.nombre.lower()} del sector {i % 12 + 1} de {org.nombre}.',
                        'estado': ['Ingresada', 'En proceso', 'Resuelta'][i % 3],
                        'created_at': anchor - datetime.timedelta(days=i // 2, hours=i % 12, minutes=d)})
        if created_credentials:
            by_alias = {account['usuario']: account for account in previous}
            by_alias.update({account['usuario']: account for account in created_credentials})
            write_credentials(path, list(by_alias.values()))
            self.stdout.write(f'Cuentas nuevas: {len(created_credentials)}. Credenciales solo en el archivo privado {path}.')
        else:
            self.stdout.write('No se crearon cuentas ni se reiniciaron contraseñas.')
        totals = {model._meta.model_name: model.all_objects.count() for model in [Delegacion, ItemMeta, TipoAtencion, SubAtencion, Atencion]}
        self.stdout.write(json.dumps(totals, ensure_ascii=False))
