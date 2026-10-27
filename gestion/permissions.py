"""Traducción de los roles SGR a Groups y permisos nativos de Django."""
from django.contrib.auth.models import Group, Permission
from .models import Usuario

CATALOGS = {'delegacion', 'rol', 'usuario', 'itemmeta', 'tipoatencion', 'subatencion'}
ROLE_MODELS = {
    'ROL01': CATALOGS,
    'ROL02': {'delegacion', 'itemmeta', 'tipoatencion', 'subatencion'},
    'ROL03': {'usuario', 'itemmeta'},
    'ROL04': set(),
    'ROL05': {'delegacion', 'itemmeta', 'tipoatencion', 'subatencion'},
}
PREFIX = 'SGR:'


def sync_user_group(user, using='default'):
    """Gestiona solo grupos SGR; conserva permisos y grupos externos."""
    previous = user.groups.filter(name__startswith=PREFIX)
    role = user.rol
    if not role:
        user.groups.remove(*previous)
        return
    group, _ = Group.objects.using(using).get_or_create(name=PREFIX + role.codigo)
    models = CATALOGS if role.permisos == 'total' else ROLE_MODELS.get(role.codigo, set())
    read_only = role.codigo == 'ROL05' and role.permisos != 'total'
    actions = ['view'] if read_only else ['view', 'add', 'change', 'delete']
    codes = [f'{action}_{model}' for model in models for action in actions]
    permissions = Permission.objects.using(using).filter(content_type__app_label='gestion', codename__in=codes)
    group.permissions.set(permissions)
    user.groups.remove(*previous.exclude(pk=group.pk))
    user.groups.add(group)
    for cache in ('_perm_cache', '_user_perm_cache', '_group_perm_cache'):
        user.__dict__.pop(cache, None)


def sync_all_users(using='default'):
    for user in Usuario.objects.using(using).select_related('rol'):
        sync_user_group(user, using=using)
