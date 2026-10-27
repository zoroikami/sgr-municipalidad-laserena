from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Delegacion, Rol, ItemMeta, TipoAtencion, SubAtencion, Atencion

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('SGR', {'fields': ('nombre', 'rut', 'rol', 'delegacion', 'estado', 'foto_perfil')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('SGR', {'fields': ('email', 'nombre', 'rut', 'rol', 'delegacion')}),)
    list_display = ('username', 'nombre', 'email', 'rut', 'rol', 'delegacion', 'estado')
    search_fields = ('username', 'nombre', 'email', 'rut')
    list_filter = ('rol', 'delegacion', 'estado', 'is_staff')

@admin.register(Delegacion)
class DelegacionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'direccion', 'comuna', 'estado')
    search_fields = ('codigo', 'nombre', 'direccion')
    list_filter = ('estado', 'comuna')

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'permisos', 'alcance', 'estado')
    search_fields = ('codigo', 'nombre')
    list_filter = ('estado', 'permisos', 'alcance')

@admin.register(ItemMeta)
class ItemMetaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'meta_cantidad', 'unidad_medida', 'estado')
    search_fields = ('codigo', 'nombre')
    list_filter = ('estado',)

@admin.register(TipoAtencion)
class TipoAtencionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'estado')
    search_fields = ('codigo', 'nombre')
    list_filter = ('estado',)

@admin.register(SubAtencion)
class SubAtencionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'estado')
    search_fields = ('codigo', 'nombre', 'tipo__nombre')
    list_filter = ('tipo', 'estado')

@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ('folio', 'solicitante_rut', 'solicitante_nombre', 'delegacion', 'tipo', 'subtipo', 'responsable_nombre', 'fecha_registro')
    search_fields = ('folio', 'solicitante_rut', 'solicitante_nombre', 'responsable_nombre')
    list_filter = ('delegacion', 'tipo', 'fecha_registro')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (request.user.rol and request.user.rol.permisos == 'total'):
            return qs
        if request.user.delegacion_id:
            return qs.filter(delegacion_id=request.user.delegacion_id)
        return qs.none()
