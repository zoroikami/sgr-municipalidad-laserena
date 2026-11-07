from django.contrib.auth.models import Group, Permission

ROLE_NAMES = ('Administrador', 'Editor', 'Lector', 'Cliente')


def configure_groups():
    """Reconcile the four municipal roles against model permissions, idempotently."""
    actions = {
        'Administrador': ('view', 'add', 'change', 'delete'),
        'Editor': ('view', 'add', 'change'),
        'Lector': ('view',),
        'Cliente': (),
    }
    for name, allowed in actions.items():
        group, _ = Group.objects.get_or_create(name=name)
        permissions = Permission.objects.filter(content_type__app_label='gestion').exclude(
            content_type__model='secuencia'
        )
        selected = [p for p in permissions if p.codename.split('_', 1)[0] in allowed]
        if name == 'Administrador':
            selected.extend(Permission.objects.filter(content_type__app_label='cuentas',
                codename__in=['view_cuentas', 'add_cuentas', 'change_cuentas']))
        group.permissions.set(selected)


def is_cliente(user):
    return user.is_authenticated and not user.is_superuser and user.groups.filter(name='Cliente').exists()


def can_manage_users(user):
    return user.is_authenticated and (user.is_superuser or (
        not is_cliente(user) and user.groups.filter(name='Administrador').exists()
        and user.has_perm('cuentas.view_cuentas') and hasattr(user, 'perfil')
    ))
