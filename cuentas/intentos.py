"""Límite de intentos de autenticación (CWE-307) con contadores atómicos en Redis.

Cada intento reserva su lugar ANTES de comprobar la contraseña: INCR y EXPIRE ocurren en un solo script Lua,
así varias peticiones simultáneas no pueden leer el mismo contador ni dejar una clave sin vencimiento.
Las claves son HMAC del identificador: Redis no guarda usuarios, correos ni direcciones en claro.
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

# Suma y asegura el vencimiento sin alargar una ventana vigente (TTL -1 = clave sin vencimiento).
_SUMAR = """
local valor = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return valor
"""
# Devuelve un lugar reservado sin crear claves nuevas ni dejar valores negativos.
_DEVOLVER = """
if redis.call('EXISTS', KEYS[1]) == 1 and tonumber(redis.call('GET', KEYS[1])) > 0 then
  return redis.call('DECR', KEYS[1])
end
return 0
"""


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


def _redis(tipo, identificador):
    """Cliente Redis y clave final (con el prefijo del caché) del contador."""
    cache = caches[CACHE]
    clave = cache.make_and_validate_key('intentos:' + salted_hmac(
        f'sgr.intentos.{tipo}', str(identificador).strip().casefold(), algorithm='sha256').hexdigest())
    return cache._cache.get_client(clave, write=True), clave


def reservar(tipo, identificador):
    """Suma un intento antes de verificar y devuelve el total; 0 si Redis no responde."""
    try:
        cliente, clave = _redis(tipo, identificador)
        return int(cliente.eval(_SUMAR, 1, clave, VENTANA))
    except Exception:  # noqa: BLE001 - Redis caído: la autenticación no depende del contador
        logger.exception('No se pudo registrar el intento %s.', tipo)
        return 0


def devolver(tipo, identificador):
    """Libera un lugar reservado (por ejemplo, el de un ingreso correcto en el contador por IP)."""
    try:
        cliente, clave = _redis(tipo, identificador)
        cliente.eval(_DEVOLVER, 1, clave)
    except Exception:  # noqa: BLE001
        logger.exception('No se pudo liberar el intento %s.', tipo)


def limpiar(tipo, identificador):
    try:
        cliente, clave = _redis(tipo, identificador)
        cliente.delete(clave)
    except Exception:  # noqa: BLE001
        logger.exception('No se pudo limpiar el contador de intentos %s.', tipo)


def excede(tipo, total):
    return total > LIMITES[tipo]


def permitir(tipo, identificador):
    """Reserva el intento y responde si todavía está dentro del límite (para solicitudes, no contraseñas)."""
    return not excede(tipo, reservar(tipo, identificador))
