"""Grant the new modules without resetting existing permission customizations."""
from django.db import migrations


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    models = ('organizacion', 'gestiontubo', 'actividadsgr', 'ausenciasgr')
    rules = {
        'Coordinador': {model: ('view', 'add', 'change', 'delete') for model in models},
        'Delegado Municipal': {
            'organizacion': ('view', 'add', 'change', 'delete'),
            'gestiontubo': ('view', 'add', 'change', 'delete'),
            'actividadsgr': ('view', 'add'), 'ausenciasgr': ('view', 'add'),
        },
        'Operador / Funcionario': {
            'organizacion': ('view', 'add', 'change'),
            'gestiontubo': ('view', 'add', 'change'),
            'actividadsgr': ('view', 'add'), 'ausenciasgr': ('view',),
        },
        'Consultor': {model: ('view',) for model in models},
    }
    # Permissions must exist before post_migrate runs on a fresh installation.
    permissions = {}
    for model in models:
        ct, _ = ContentType.objects.using(alias).get_or_create(app_label='gestion', model=model)
        for action in ('view', 'add', 'change', 'delete'):
            permission, _ = Permission.objects.using(alias).get_or_create(
                content_type=ct, codename=f'{action}_{model}',
                defaults={'name': f'Can {action} {model}'})
            permissions[(model, action)] = permission
    for name, sections in rules.items():
        group = Group.objects.using(alias).filter(name=name).first()
        if group is not None:
            group.permissions.add(*(permissions[(model, action)]
                for model, actions in sections.items() for action in actions))


class Migration(migrations.Migration):
    dependencies = [
        ('gestion', '0007_merge_integrado'),
        ('cuentas', '0006_merge_integrado'),
    ]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
