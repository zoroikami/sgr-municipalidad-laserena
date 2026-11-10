from django.urls import path
from .consumers import AtencionesConsumer

websocket_urlpatterns = [path('ws/atenciones/', AtencionesConsumer.as_asgi())]
