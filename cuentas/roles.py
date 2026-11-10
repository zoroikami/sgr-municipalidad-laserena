from django.contrib.auth.models import Group, Permission

ROLE_NAMES = ('Superadministrador', 'Coordinador', 'Delegado Municipal', 'Operador / Funcionario', 'Consultor', 'Cliente')
LOCAL_ROLE_NAMES = ('Delegado Municipal', 'Operador / Funcionario', 'Consultor', 'Cliente')
BUSINESS_MODELS = ('delegacion', 'itemmeta', 'tipoatencion', 'subatencion', 'atencion')
ROLE_RULES = {
    # Technical access is granted through User.is_superuser, never a group name.
    'Superadministrador': {},
    'Coordinador': {model: ('view', 'add', 'change', 'delete') for model in BUSINESS_MODELS},
    'Delegado Municipal': {model: ('view', 'add', 'change', 'delete') for model in ('itemmeta', 'atencion')},
    'Operador / Funcionario': {'atencion': ('view', 'add', 'change')},
    'Consultor': {model: ('view',) for model in BUSINESS_MODELS},
    'Cliente': {},
}


def configure_groups():
    """Install the original municipal roles plus the isolated citizen portal."""
    for name, rules in ROLE_RULES.items():
        group, _ = Group.objects.get_or_create(name=name)
        codenames = [f'{action}_{model}' for model, actions in rules.items() for action in actions]
        selected = list(Permission.objects.filter(content_type__app_label='gestion', codename__in=codenames))
        if name == 'Delegado Municipal':
            selected.extend(Permission.objects.filter(content_type__app_label='cuentas',
                codename__in=['view_cuentas', 'add_cuentas', 'change_cuentas']))
        group.permissions.set(selected)


def is_cliente(user):
    return user.is_authenticated and not user.is_superuser and user.groups.filter(name='Cliente').exists()


def can_manage_users(user):
    return user.is_authenticated and (user.is_superuser or (
        not is_cliente(user) and user.groups.filter(name='Delegado Municipal').exists()
        and user.has_perm('cuentas.view_cuentas') and hasattr(user, 'perfil')
    ))
