from .roles import ROLE_NAMES, can_manage_users, is_cliente


def account_context(request):
    user = request.user
    if not user.is_authenticated:
        return {'is_cliente': False, 'role_label': ''}
    label = 'Superadministrador' if user.is_superuser else next(
        (name for name in ROLE_NAMES if user.groups.filter(name=name).exists()), 'Sin rol'
    )
    from gestion.models import Delegacion
    can_switch = getattr(request, 'can_switch_delegation', False)
    return {'is_cliente': is_cliente(user), 'role_label': label,
            'can_manage_accounts': can_manage_users(user),
            'can_switch_delegation': can_switch,
            'active_delegation': getattr(request, 'active_delegation', None),
            'available_delegations': Delegacion.objects.filter(estado='Activo').order_by('codigo') if can_switch else ()}
