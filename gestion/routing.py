from django.urls import path
from .consumers import AtencionesConsumer, ModulosConsumer

websocket_urlpatterns = [
    path('ws/atenciones/', AtencionesConsumer.as_asgi()),
    path('ws/modulos/<slug:modulo>/', ModulosConsumer.as_asgi()),
]
