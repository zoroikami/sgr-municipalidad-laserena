from django.core.exceptions import PermissionDenied


def is_cliente(user):
    return user.is_authenticated and user.groups.filter(name='Cliente').exists()


def delegation_id(user):
    profile = getattr(user, 'perfil', None)
    if not profile or profile.delegacion.deleted_at or profile.delegacion.estado != 'Activo':
        raise PermissionDenied('Tu cuenta no tiene una delegación activa asignada.')
    return profile.delegacion_id


def authorize(user, model, action='view'):
    if is_cliente(user) or not user.has_perm(f'{model._meta.app_label}.{action}_{model._meta.model_name}'):
        raise PermissionDenied('Tu cuenta no tiene permiso para realizar esta acción.')
    delegation_id(user)


def scoped(user, model):
    from .models import Delegacion
    org = delegation_id(user)
    query = model.objects.all()
    return query.filter(pk=org) if model is Delegacion else query.filter(delegacion_id=org)
