"""Shared settings. MySQL and secrets are explicit in every environment."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def required(name):
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f'Configura {name} en el entorno.')
    return value


def enabled(name, default='false'):
    return os.environ.get(name, default).lower() == 'true'


SECRET_KEY = required('DJANGO_SECRET_KEY')
DEBUG = enabled('DJANGO_DEBUG')
ALLOWED_HOSTS = [x.strip() for x in required('DJANGO_ALLOWED_HOSTS').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()]
# SQLite is an explicit development option; production must use MySQL.
DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3' if enabled('USE_SQLITE') else 'django.db.backends.mysql')
if DB_ENGINE not in ('django.db.backends.mysql', 'django.db.backends.sqlite3'):
    raise ImproperlyConfigured('DB_ENGINE debe ser MySQL o SQLite de desarrollo.')
if DB_ENGINE == 'django.db.backends.sqlite3' and not DEBUG:
    raise ImproperlyConfigured('SQLite solo está permitido con DJANGO_DEBUG=true. Configura MySQL para producción.')

if DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.mysql', 'NAME': required('DB_NAME'),
        'USER': required('DB_USER'), 'PASSWORD': required('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'), 'CONN_MAX_AGE': 0,
        'OPTIONS': {'charset': 'utf8mb4', 'isolation_level': 'read committed',
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
        'TEST': {'NAME': 'test_' + required('DB_NAME')},
    }}

CHANNEL_LAYERS = {'default': {
    'BACKEND': 'channels_redis.core.RedisChannelLayer',
    'CONFIG': {'hosts': [os.environ.get('REDIS_URL', 'redis://127.0.0.1:6380/0')]},
}}

INSTALLED_APPS = ['daphne',
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'channels', 'cuentas', 'gestion',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'cuentas.context_processors.account_context',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static', ('municipal', BASE_DIR / 'assets' / 'municipal')]
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'cuentas:login'
LOGIN_REDIRECT_URL = 'gestion:inicio'
LOGOUT_REDIRECT_URL = 'cuentas:login'
PASSWORD_RESET_TIMEOUT = 3600
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = enabled('EMAIL_USE_TLS', 'true')
EMAIL_USE_SSL = enabled('EMAIL_USE_SSL')
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'SGR <sgr@example.test>')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_COOKIE_SECURE = enabled('COOKIE_SECURE', 'false' if DEBUG else 'true')
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = enabled('SECURE_SSL_REDIRECT', 'false' if DEBUG else 'true')
SECURE_HSTS_SECONDS = 0 if DEBUG else int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# Enable only behind the supplied trusted Nginx configuration.
if enabled('TRUST_PROXY_SSL'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
CSRF_FAILURE_VIEW = 'config.errors.csrf_failure'
