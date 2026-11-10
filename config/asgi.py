import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from gestion.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': ASGIStaticFilesHandler(django_asgi_app) if settings.DEBUG else django_asgi_app,
    'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
})
