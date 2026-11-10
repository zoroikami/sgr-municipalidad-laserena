from .roles import ROLE_NAMES, is_cliente


def account_context(request):
    user = request.user
    if not user.is_authenticated:
        return {'is_cliente': False, 'role_label': ''}
    label = 'Superadministrador' if user.is_superuser else next(
        (name for name in ROLE_NAMES if user.groups.filter(name=name).exists()), 'Sin rol'
    )
    return {'is_cliente': is_cliente(user), 'role_label': label}
