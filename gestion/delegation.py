"""Resolve the municipal workspace without changing account ownership or privileges."""
from cuentas.roles import is_cliente

SESSION_KEY = 'active_delegation_id'


def has_global_scope(user):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or (not is_cliente(user) and user.groups.filter(name='Coordinador').exists())
    )


def active_delegation(user):
    """A validated, request-local selection; absence means the global workspace."""
    return getattr(user, 'active_delegation_id', None) if has_global_scope(user) else None


def session_delegation(session):
    from .models import Delegacion
    value = session.get(SESSION_KEY)
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    return Delegacion.objects.filter(pk=value, estado='Activo').first()


class DelegationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_delegation = None
        request.can_switch_delegation = has_global_scope(request.user)
        if request.can_switch_delegation:
            request.active_delegation = session_delegation(request.session)
            if request.active_delegation is None:
                request.session.pop(SESSION_KEY, None)
            request.user.active_delegation_id = (
                request.active_delegation.pk if request.active_delegation else None
            )
        else:
            request.session.pop(SESSION_KEY, None)
        return self.get_response(request)
