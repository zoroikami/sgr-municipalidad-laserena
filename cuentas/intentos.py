"""Límite de intentos de autenticación (CWE-307) con contadores atómicos en Redis.

Se cuentan los fallos por cuenta y por dirección IP antes de comprobar la contraseña. Las claves son HMAC del
identificador: Redis no guarda usuarios, correos ni direcciones en claro.
"""
import ipaddress
import logging

from django.conf import settings
from django.core.cache import caches
from django.utils.crypto import salted_hmac

logger = logging.getLogger(__name__)
CACHE = 'autenticacion'
VENTANA = 15 * 60
LIMITES = {
    'login-cuenta': 5,       # contraseñas fallidas para una misma cuenta
    'login-ip': 20,          # fallos desde una misma IP, sumando todas las cuentas
    'clave-actual': 5,       # contraseña actual errada al cambiarla
    'recuperacion-ip': 5,    # solicitudes de recuperación desde una IP
    'cambio-correo': 5,      # solicitudes de cambio de correo de una cuenta
}
MENSAJE_BLOQUEO = ('Hiciste demasiados intentos. Por seguridad, espera 15 minutos antes de volver a intentarlo '
                   'o recupera tu contraseña.')


def direccion(request):
    """IP del cliente. Detrás del Nginx incluido se usa X-Real-IP, que el proxy siempre sobrescribe."""
    if request is None:
        return 'desconocida'
    valor = request.META.get('REMOTE_ADDR', '')
    if getattr(settings, 'SECURE_PROXY_SSL_HEADER', None):
        valor = request.META.get('HTTP_X_REAL_IP', valor)
    try:
        return str(ipaddress.ip_address(valor))
    except ValueError:
        return 'desconocida'


def _clave(tipo, identificador):
    return 'intentos:' + salted_hmac(f'sgr.intentos.{tipo}', str(identificador).strip().casefold(),
                                     algorithm='sha256').hexdigest()


def excedido(tipo, identificador):
    """True si el identificador ya agotó sus intentos. Si Redis no responde se permite y se registra:
    la autenticación no debe caerse por el contador, que es una protección adicional."""
    try:
        return int(caches[CACHE].get(_clave(tipo, identificador)) or 0) >= LIMITES[tipo]
    except Exception:  # noqa: BLE001 - Redis caído o ilegible
        logger.exception('No se pudo leer el contador de intentos %s.', tipo)
        return False


def registrar(tipo, identificador):
    """Suma un intento sin alargar la ventana vigente; devuelve el total (0 si Redis no responde)."""
    cache = caches[CACHE]
    clave = _clave(tipo, identificador)
    try:
        if cache.add(clave, 1, timeout=VENTANA):
            return 1
        try:
            return cache.incr(clave)
        except ValueError:  # venció entre add e incr
            cache.add(clave, 1, timeout=VENTANA)
            return 1
    except Exception:  # noqa: BLE001
        logger.exception('No se pudo registrar el intento %s.', tipo)
        return 0


def limpiar(tipo, identificador):
    try:
        caches[CACHE].delete(_clave(tipo, identificador))
    except Exception:  # noqa: BLE001
        logger.exception('No se pudo limpiar el contador de intentos %s.', tipo)


def permitir(tipo, identificador):
    """Registra el intento y responde si todavía está dentro del límite (para solicitudes, no contraseñas)."""
    return registrar(tipo, identificador) <= LIMITES[tipo]
