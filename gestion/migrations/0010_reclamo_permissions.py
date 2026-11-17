"""Grant the RECLAMOS module without resetting existing permission customizations."""
from django.db import migrations


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    rules = {
        'Coordinador': ('view', 'add', 'change', 'delete'),
        'Delegado Municipal': ('view', 'add'),
        'Operador / Funcionario': ('view',),
        'Consultor': ('view',),
    }
    ct, _ = ContentType.objects.using(alias).get_or_create(app_label='gestion', model='reclamosgr')
    permissions = {}
    for action in ('view', 'add', 'change', 'delete'):
        permissions[action], _ = Permission.objects.using(alias).get_or_create(
            content_type=ct, codename=f'{action}_reclamosgr', defaults={'name': f'Can {action} reclamo SGR'})
    for name, actions in rules.items():
        group = Group.objects.using(alias).filter(name=name).first()
        if group is not None:
            group.permissions.add(*(permissions[action] for action in actions))


class Migration(migrations.Migration):
    dependencies = [('gestion', '0009_reclamos_indicador_tubo')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
