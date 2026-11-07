from django.urls import include, path
from .admin import site

urlpatterns = [
    path('admin/', site.urls),
    path('cuentas/', include('cuentas.urls')),
    path('', include('gestion.urls')),
]
handler400 = 'config.errors.bad_request'
handler403 = 'config.errors.permission_denied'
handler404 = 'config.errors.not_found'
handler500 = 'config.errors.server_error'
