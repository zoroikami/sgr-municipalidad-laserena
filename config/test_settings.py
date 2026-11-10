from .settings import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
# MySQL stays enabled in tests. Fast hashes are only used for test accounts.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
