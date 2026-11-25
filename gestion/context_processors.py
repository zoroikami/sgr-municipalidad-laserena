"""Datos comunes de la cabecera municipal: período de medición vigente y plazo semanal."""
from cuentas.roles import is_cliente

from .integrado import periodo_actual


def periodo(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or is_cliente(user):
        return {}
    return {'periodo_sgr': periodo_actual()}
