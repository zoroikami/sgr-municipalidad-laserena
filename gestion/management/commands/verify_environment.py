"""Verify live dependencies; never report test doubles as a ready environment."""
import asyncio
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.mail import get_connection
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection

from gestion.models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion


class Command(BaseCommand):
    help = 'Verificar MySQL, Redis y SMTP reales; opcionalmente semillas y configuración de producción.'

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true')
        parser.add_argument('--production', action='store_true')

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            raise CommandError('Se requiere MySQL real para acreditar este entorno.')
        with connection.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
            cursor.execute("SELECT CONVERT_TZ('2026-11-01 03:00:00', 'UTC', 'America/Santiago')")
            if cursor.fetchone()[0] is None:
                raise CommandError('Carga las tablas de zonas horarias de MySQL para los filtros de fechas.')
        self.stdout.write(f'MySQL conectado: {version}. Zonas horarias disponibles.')

        layer = get_channel_layer()
        if layer is None or layer.__class__.__module__ != 'channels_redis.core':
            raise CommandError('Se requiere channels_redis; una capa en memoria no acredita Redis.')

        async def round_trip():
            channel = await layer.new_channel()
            group = 'verificacion.' + uuid.uuid4().hex
            try:
                await layer.group_add(group, channel)
                await layer.group_send(group, {'type': 'verification.ping'})
                result = await asyncio.wait_for(layer.receive(channel), timeout=5)
                if result != {'type': 'verification.ping'}:
                    raise CommandError('Redis no devolvió el evento esperado.')
            finally:
                await layer.group_discard(group, channel)
                await layer.close_pools()
        async_to_sync(round_trip)()
        self.stdout.write('Redis: envío y recepción de evento comprobados.')

        if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
            raise CommandError('Configura SMTP real o Mailpit; consola, archivos y memoria no acreditan envío.')
        with get_connection() as smtp:
            code, _ = smtp.connection.noop()
            if code != 250:
                raise CommandError('El servidor SMTP no respondió correctamente.')
        self.stdout.write('SMTP conectado. El recorrido de navegador verifica la entrega y el token.')

        if options['demo']:
            from django.contrib.auth import get_user_model
            from gestion.management.commands.seed_demo import ACCOUNTS
            counts = {model.__name__: model.objects.count() for model in
                      (Delegacion, ItemMeta, TipoAtencion, SubAtencion, Atencion)}
            if sum(counts.values()) < 2000 or counts['ItemMeta'] < 50 or counts['Atencion'] < 50:
                raise CommandError('Faltan al menos 2.000 registros de negocio y 50 por CRUD.')
            users = get_user_model().objects.filter(username__in=[account[0] for account in ACCOUNTS])
            if users.count() != 6 or users.filter(is_superuser=True).exists() or users.filter(is_active=False).exists():
                raise CommandError('Las seis cuentas de revisión deben estar activas y sin superusuario.')
            self.stdout.write(f'Semillas y cuentas disponibles: {counts}.')

        if options['production']:
            if settings.DEBUG:
                raise CommandError('Producción requiere DJANGO_DEBUG=false.')
            call_command('check', deploy=True, fail_level='WARNING')
        self.stdout.write(self.style.SUCCESS('Entorno verificado.'))
