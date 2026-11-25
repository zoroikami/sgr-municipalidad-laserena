"""The optional environment console is reserved to technical superusers."""
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from cuentas.models import Perfil
from gestion.models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion


class TechnicalAdminSite(AdminSite):
    site_header = 'SGR La Serena · Soporte técnico'
    site_title = 'Soporte SGR'
    index_title = 'Administración del entorno'

    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def login(self, request, extra_context=None):
        # Un solo punto de ingreso con límite de intentos: la consola técnica usa el login municipal.
        from django.contrib.auth.views import redirect_to_login
        from django.urls import reverse
        destino = request.GET.get('next') or reverse('admin:index')
        return redirect_to_login(destino, login_url=reverse('cuentas:login'))


site = TechnicalAdminSite(name='admin')
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)
for model in [Perfil, Delegacion, ItemMeta, TipoAtencion, SubAtencion, Atencion]:
    site.register(model, ModelAdmin)
