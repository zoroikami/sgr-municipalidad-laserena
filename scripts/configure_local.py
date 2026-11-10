"""Create a private local MySQL/Redis/Mailpit configuration without overwriting it."""
from pathlib import Path
import os
import secrets


def main():
    path = Path(__file__).resolve().parents[1] / '.env'
    if path.exists():
        print('.env ya existe; se conservó sin cambios.')
        return
    values = {
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64), 'DJANGO_DEBUG': 'true',
        'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1',
        'CSRF_TRUSTED_ORIGINS': 'http://localhost:8001,http://127.0.0.1:8001',
        'DB_ENGINE': 'django.db.backends.mysql', 'USE_SQLITE': 'false',
        'DB_NAME': 'sgr_django', 'DB_USER': 'sgr',
        'DB_PASSWORD': secrets.token_urlsafe(32), 'MYSQL_ROOT_PASSWORD': secrets.token_urlsafe(32),
        'DB_HOST': '127.0.0.1', 'DB_PORT': '3307',
        'REDIS_URL': 'redis://127.0.0.1:6380/0',
        'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'EMAIL_HOST': '127.0.0.1', 'EMAIL_PORT': '1025', 'EMAIL_USE_TLS': 'false',
        'DEFAULT_FROM_EMAIL': 'SGR <sgr@example.test>',
        'TRUST_PROXY_SSL': 'false', 'APP_COMMIT': 'local',
    }
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        output.write(''.join(f'{key}={value}\n' for key, value in values.items()))
    print('.env creado con secretos privados. Inicia MySQL, Redis y Mailpit antes de migrar.')


if __name__ == '__main__':
    main()
