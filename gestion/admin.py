from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Delegacion, Rol, ItemMeta, TipoAtencion, SubAtencion, Atencion

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('SGR', {'fields': ('nombre', 'rut', 'rol', 'delegacion', 'estado')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('SGR', {'fields': ('email', 'nombre', 'rut', 'rol', 'delegacion')}),)
    list_display = ('username', 'nombre', 'email', 'rol', 'delegacion', 'estado')

admin.site.register([Delegacion, Rol, ItemMeta, TipoAtencion, SubAtencion, Atencion])
