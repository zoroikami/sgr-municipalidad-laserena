"""Recuperación explícita de la base SQLite del prototipo anterior."""
import re
import sqlite3
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import identify_hasher
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from gestion.models import (
    Atencion, Delegacion, ItemMeta, Rol, Secuencia, SubAtencion, TipoAtencion, Usuario,
)


CATALOGS = (
    ('delegaciones', Delegacion, ('nombre', 'direccion', 'comuna', 'estado')),
    ('roles', Rol, ('nombre', 'descripcion', 'permisos', 'alcance', 'estado')),
    ('items_metas', ItemMeta, ('nombre', 'descripcion', 'unidad_medida', 'meta_cantidad', 'estado')),
    ('tipos_atencion', TipoAtencion, ('nombre', 'descripcion', 'estado')),
    ('sub_atenciones', SubAtencion, ('nombre', 'estado')),
)


def require_reference(model, code):
    if not model.objects.filter(codigo=code).exists():
        raise CommandError('La base anterior contiene una referencia inexistente. No se importó ningún registro.')


def restore_date(model, obj, field, value):
    if not value:
        return
    date = parse_datetime(value)
    if date is None:
        raise CommandError('La base anterior contiene una fecha inválida.')
    if timezone.is_naive(date):
        date = timezone.make_aware(date)
    model.objects.filter(pk=obj.pk).update(**{field: date})


class Command(BaseCommand):
    help = 'Recupera datos anteriores sin duplicar registros ni sustituir contraseñas o datos actuales.'

    def add_arguments(self, parser):
        parser.add_argument('source', nargs='?', default=str(settings.BASE_DIR / 'database/sgr_laserena.db'))

    def handle(self, *args, **options):
        source = Path(options['source']).resolve()
        if not source.is_file() or source == Path(settings.DATABASES['default']['NAME']).resolve():
            raise CommandError('Seleccione una base anterior existente, distinta de la base Django actual.')
        # SQLite abre el origen en modo de solo lectura; la recuperación es atómica.
        try:
            db = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
            try:
                db.row_factory = sqlite3.Row
                db.execute('BEGIN')
                tables = [item[0] for item in CATALOGS] + ['usuarios', 'atenciones']
                data = {table: [dict(row) for row in db.execute(f'SELECT * FROM {table}')] for table in tables}
            finally:
                db.close()
            with transaction.atomic():
                counts = self.import_records(data)
                self.sync_sequences()
        except (sqlite3.Error, KeyError, IntegrityError, ValueError) as exc:
            raise CommandError('La base anterior no tiene el formato esperado. No se importó ningún registro.') from exc
        for name, count in counts.items():
            self.stdout.write(f'{name}: {count} nuevos')
        self.stdout.write(self.style.SUCCESS('Recuperación completada. Los registros actuales y sus contraseñas se conservan.'))

    def import_records(self, data):
        counts = {}
        for table, model, fields in CATALOGS:
            counts[table] = 0
            for row in data[table]:
                defaults = {name: row[name] for name in fields}
                if model == SubAtencion:
                    require_reference(TipoAtencion, row['tipo_codigo'])
                    defaults['tipo_id'] = row['tipo_codigo']
                obj, created = model.objects.get_or_create(codigo=row['codigo'], defaults=defaults)
                counts[table] += int(created)
                if created and model == Delegacion:
                    restore_date(model, obj, 'creado_en', row.get('creado_en'))

        counts['usuarios'] = 0
        for row in data['usuarios']:
            email = row['email'].strip().lower()
            if not email:
                raise CommandError('Hay un usuario anterior sin correo. No se importó ningún registro.')
            rut = (row['rut'] or '').replace('.', '').strip().upper() or None
            matches = Usuario.objects.filter(Q(email__iexact=email) | Q(rut=rut)) if rut else Usuario.objects.filter(email__iexact=email)
            if matches.count() > 1:
                raise CommandError('El correo y RUT anteriores coinciden con cuentas distintas. No se importó ningún registro.')
            require_reference(Rol, row['rol_codigo'])
            require_reference(Delegacion, row['delegacion_codigo'])
            user = matches.first()
            defaults = {'nombre': row['nombre'], 'rut': rut, 'rol_id': row['rol_codigo'], 'delegacion_id': row['delegacion_codigo']}
            if user:
                # Completar el perfil vacío del superusuario ya creado sin tocar su acceso.
                changed = []
                for field, value in defaults.items():
                    if not getattr(user, field) and value:
                        setattr(user, field, value)
                        changed.append(field.removesuffix('_id'))
                if changed:
                    user.save(update_fields=changed)
                continue
            user = Usuario(username=email, email=email, estado=row['estado'], is_active=row['estado'] == 'Activo', **defaults)
            encoded = row.get('password_hash') or ''
            if not encoded:
                user.set_unusable_password()
            else:
                try:
                    identify_hasher(encoded)
                except ValueError:
                    if encoded.startswith(('scrypt:', 'pbkdf2:')):
                        raise CommandError('Hay una contraseña con formato no compatible. No se importó ningún registro.')
                    # El prototipo guardaba sus claves de ejemplo sin hash Django.
                    user.set_password(encoded)
                else:
                    user.password = encoded
            user.save()
            counts['usuarios'] += 1

        counts['atenciones'] = 0
        fields = ('solicitante_rut', 'solicitante_nombre', 'descripcion', 'responsable_nombre')
        for row in data['atenciones']:
            for model, field in ((Delegacion, 'delegacion'), (TipoAtencion, 'tipo'), (SubAtencion, 'subtipo')):
                require_reference(model, row[field + '_codigo'])
            if not SubAtencion.objects.filter(codigo=row['subtipo_codigo'], tipo_id=row['tipo_codigo']).exists():
                raise CommandError('Una atención anterior tiene un tipo y subatención incompatibles.')
            defaults = {field: row[field] for field in fields}
            defaults.update({field + '_id': row[field + '_codigo'] for field in ('delegacion', 'tipo', 'subtipo')})
            obj, created = Atencion.objects.get_or_create(folio=row['folio'], defaults=defaults)
            counts['atenciones'] += int(created)
            if created:
                restore_date(Atencion, obj, 'fecha_registro', row.get('fecha_registro'))
        return counts

    def sync_sequences(self):
        for table, model, _fields in CATALOGS:
            resource = table.replace('_', '-')
            values = [int(match[1]) for code in model.objects.values_list('codigo', flat=True)
                      if (match := re.fullmatch(r'[A-Z]+(\d+)', code))]
            self.advance_sequence(resource, max(values, default=0))
        for folio in Atencion.objects.values_list('folio', flat=True):
            if match := re.fullmatch(r'ATN-(\d{4})-(\d+)', folio):
                self.advance_sequence(f'atenciones-{match[1]}', int(match[2]))

    def advance_sequence(self, name, value):
        sequence, _created = Secuencia.objects.get_or_create(nombre=name)
        Secuencia.objects.filter(pk=sequence.pk, valor__lt=value).update(valor=value)
