from django.core.exceptions import PermissionDenied

from cuentas.roles import is_cliente
from .delegation import active_delegation, has_global_scope


def delegation_id(user):
    profile = getattr(user, 'perfil', None)
    if not profile or not profile.delegacion_id or profile.delegacion.deleted_at or profile.delegacion.estado != 'Activo':
        raise PermissionDenied('Tu cuenta no tiene una delegación activa asignada.')
    return profile.delegacion_id


def authorize(user, model, action='view'):
    if is_cliente(user) or not user.has_perm(f'{model._meta.app_label}.{action}_{model._meta.model_name}'):
        raise PermissionDenied('Tu cuenta no tiene permiso para realizar esta acción.')
    if not has_global_scope(user):
        delegation_id(user)


def scoped(user, model):
    from .models import Atencion, Delegacion
    query = model.objects.all()
    if is_cliente(user):
        return query.filter(cliente=user, delegacion_id=delegation_id(user)) if model is Atencion else query.none()
    if has_global_scope(user) and active_delegation(user) is None:
        return query
    org = active_delegation(user) if has_global_scope(user) else delegation_id(user)
    return query.filter(pk=org) if model is Delegacion else query.filter(delegacion_id=org)
