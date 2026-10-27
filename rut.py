"""Chilean RUT syntax/check-digit validation (modulo 11), not registry lookup."""
import re

RUT_ERROR = 'Ingresa un RUT chileno válido con su dígito verificador (ej.: 12.345.678-5).'


class RutError(ValueError):
    pass


def normalize_rut(value):
    if not isinstance(value, str) or len(value) > 20:
        raise RutError(RUT_ERROR)
    raw = value.strip().upper()
    if not re.fullmatch(r'(?:[0-9]{1,8}|[0-9]{1,3}(?:\.[0-9]{3}){1,2})-?[0-9K]', raw):
        raise RutError(RUT_ERROR)
    compact = raw.replace('.', '').replace('-', '')
    body, dv = compact[:-1].lstrip('0'), compact[-1]
    if not body or len(body) > 8:
        raise RutError(RUT_ERROR)
    total = sum(int(digit) * (2 + index % 6) for index, digit in enumerate(reversed(body)))
    remainder = 11 - total % 11
    expected = 'K' if remainder == 10 else '0' if remainder == 11 else str(remainder)
    if dv != expected:
        raise RutError(RUT_ERROR)
    return body + '-' + dv


def is_valid_rut(value):
    try:
        normalize_rut(value)
        return True
    except RutError:
        return False
