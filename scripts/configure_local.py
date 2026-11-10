#!/usr/bin/env python3
"""Create a private local environment without printing or overwriting secrets."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    raise SystemExit('Ya existe .env. Se conservó su configuración sin cambios.')
values = {
    'DJANGO_SECRET_KEY': secrets.token_urlsafe(60), 'DJANGO_DEBUG': 'true',
    'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1,testserver',
    'CSRF_TRUSTED_ORIGINS': 'http://localhost:8001,http://127.0.0.1:8001',
    'DB_NAME': 'sgr_django', 'DB_USER': 'sgr',
    'DB_PASSWORD': secrets.token_urlsafe(30), 'MYSQL_ROOT_PASSWORD': secrets.token_urlsafe(30),
    'DB_HOST': '127.0.0.1', 'DB_PORT': '3307', 'REDIS_URL': 'redis://127.0.0.1:6380/0',
    'EMAIL_HOST': '127.0.0.1', 'EMAIL_PORT': '1025', 'EMAIL_USE_TLS': 'false',
    'DEFAULT_FROM_EMAIL': 'SGR <sgr@example.test>',
}
with target.open('x') as output:
    target.chmod(0o600)
    output.write(''.join(f'{key}={value}\n' for key, value in values.items()))
print('Entorno local creado en .env con permisos privados. No lo subas a Git.')
