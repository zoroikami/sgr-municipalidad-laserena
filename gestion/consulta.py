"""Email a private credential and resolve one minimal, anonymous status view."""
from datetime import timedelta
import ipaddress
import secrets
from smtplib import SMTPException

from django.conf import settings
from django.core.cache import caches
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import Atencion

CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
CODE_LIFETIME = timedelta(days=30)
ATTEMPT_LIMIT = 30
ATTEMPT_WINDOW = 15 * 60


class DeliveryError(Exception):
    """The record is saved, but no new access credential was committed."""


def normalise_code(value):
    return ''.join(value.upper().split()).replace('-', '')


def code_digest(record_id, email, code):
    return salted_hmac('sgr.public-consultation',
        f'{record_id}:{email.casefold()}:{normalise_code(code)}', algorithm='sha256').hexdigest()


def send_consultation_access(record_id, consultation_url):
    # A row lock serializes renewals. Failed SMTP keeps the previous credential usable.
    with transaction.atomic():
        record = Atencion.objects.select_for_update().get(pk=record_id)
        if not record.solicitante_email:
            raise DeliveryError('La atención no tiene correo del solicitante.')
        raw = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(20))
        code = '-'.join(raw[index:index + 4] for index in range(0, 20, 4))
        now = timezone.now()
        body = render_to_string('gestion/consulta_email.txt', {
            'folio': record.folio, 'codigo': code, 'consulta_url': consultation_url,
            'vence': now + CODE_LIFETIME,
        })
        try:
            sent = send_mail('SGR La Serena: consulta de tu atención', body,
                settings.DEFAULT_FROM_EMAIL, [record.solicitante_email], fail_silently=False)
        except (SMTPException, OSError, ValueError) as error:
            raise DeliveryError('No se pudo enviar el correo.') from error
        if sent != 1:
            raise DeliveryError('El servidor de correo no aceptó el mensaje.')
        record.consulta_codigo_hash = code_digest(record.pk, record.solicitante_email, raw)
        record.consulta_enviado_at = now
        record.save(update_fields=['consulta_codigo_hash', 'consulta_enviado_at'])


def lookup_consultation(folio, code):
    row = Atencion.objects.filter(folio=folio, delegacion__estado='Activo',
        delegacion__deleted_at__isnull=True).values('pk', 'folio', 'estado', 'created_at',
        'updated_at', 'delegacion__nombre', 'solicitante_email', 'consulta_codigo_hash',
        'consulta_enviado_at').first()
    digest = code_digest(row['pk'] if row else 0, row['solicitante_email'] if row else '', code)
    matches = constant_time_compare(row['consulta_codigo_hash'] if row else '0' * 64, digest)
    now = timezone.now()
    if not row or not matches or not row['consulta_enviado_at']:
        return None
    if not now - CODE_LIFETIME <= row['consulta_enviado_at'] <= now:
        return None
    return {'folio': row['folio'], 'estado': row['estado'], 'created_at': row['created_at'],
            'updated_at': row['updated_at'], 'delegacion': row['delegacion__nombre']}


def allow_consultation_attempt(request):
    address = request.META.get('REMOTE_ADDR', '')
    if getattr(settings, 'SECURE_PROXY_SSL_HEADER', None):
        # Nginx overwrites X-Real-IP; the ASGI service has no public port.
        address = request.META.get('HTTP_X_REAL_IP', address)
    try:
        address = str(ipaddress.ip_address(address))
    except ValueError:
        address = 'unknown'
    key = 'attempts:' + salted_hmac('sgr.consultation-ip', address, algorithm='sha256').hexdigest()
    cache = caches['consulta_publica']
    if cache.add(key, 1, timeout=ATTEMPT_WINDOW):
        return True
    try:
        return cache.incr(key) <= ATTEMPT_LIMIT
    except ValueError:
        # The key may have expired between add and incr. Retry without extending a live window.
        return cache.add(key, 1, timeout=ATTEMPT_WINDOW)
