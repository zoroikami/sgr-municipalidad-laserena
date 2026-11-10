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


site = TechnicalAdminSite(name='admin')
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)
for model in [Perfil, Delegacion, ItemMeta, TipoAtencion, SubAtencion, Atencion]:
    site.register(model, ModelAdmin)
