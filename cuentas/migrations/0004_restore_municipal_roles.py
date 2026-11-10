"""Restore the original municipal names and scopes without replacing accounts."""
from django.db import migrations

RENAMES = {'Administrador': 'Delegado Municipal', 'Editor': 'Operador / Funcionario', 'Lector': 'Consultor'}
MODELS = ('delegacion', 'itemmeta', 'tipoatencion', 'subatencion', 'atencion')
RULES = {
    'Superadministrador': {},
    'Coordinador': {model: ('view', 'add', 'change', 'delete') for model in MODELS},
    'Delegado Municipal': {model: ('view', 'add', 'change', 'delete') for model in ('itemmeta', 'atencion')},
    'Operador / Funcionario': {'atencion': ('view', 'add', 'change')},
    'Consultor': {model: ('view',) for model in MODELS},
    'Cliente': {},
}


def rename_groups(apps, alias, renames):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    Membership = User.groups.through
    for old_name, name in renames.items():
        old = Group.objects.using(alias).filter(name=old_name).first()
        if old is None:
            continue
        target = Group.objects.using(alias).filter(name=name).first()
        if target is None:
            old.name = name
            old.save(using=alias, update_fields=['name'])
        else:
            for user_id in Membership.objects.using(alias).filter(group_id=old.pk).values_list('user_id', flat=True):
                Membership.objects.using(alias).get_or_create(user_id=user_id, group_id=target.pk)
            old.delete(using=alias)


def set_permissions(apps, alias, rules):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for name, models in rules.items():
        group, _ = Group.objects.using(alias).get_or_create(name=name)
        permissions = []
        specs = [('gestion', model, action, model) for model, actions in models.items() for action in actions]
        if name in ('Delegado Municipal', 'Administrador'):
            specs += [('cuentas', 'perfil', action, 'cuentas') for action in ('view', 'add', 'change')]
        for app, model, action, suffix in specs:
            ct, _ = ContentType.objects.using(alias).get_or_create(app_label=app, model=model)
            permission, _ = Permission.objects.using(alias).get_or_create(content_type=ct, codename=f'{action}_{suffix}',
                defaults={'name': f'Can {action} {suffix}'})
            permissions.append(permission.pk)
        group.permissions.set(permissions)


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    rename_groups(apps, alias, RENAMES)
    set_permissions(apps, alias, RULES)


def backwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    rename_groups(apps, alias, {name: old for old, name in RENAMES.items()})
    set_permissions(apps, alias, {
        'Administrador': {model: ('view', 'add', 'change', 'delete') for model in MODELS},
        'Editor': {model: ('view', 'add', 'change') for model in MODELS},
        'Lector': {model: ('view',) for model in MODELS}, 'Cliente': {},
    })


class Migration(migrations.Migration):
    dependencies = [('cuentas', '0003_alter_perfil_delegacion_alter_perfil_rut'),
                    ('gestion', '0003_restore_section_codes'), ('auth', '0012_alter_user_first_name_max_length')]
    operations = [migrations.RunPython(forwards, backwards)]
