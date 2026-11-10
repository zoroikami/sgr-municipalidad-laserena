"""Expose the client's actual owner-only read permission without granting writes."""
from django.db import migrations


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    group, _ = Group.objects.using(alias).get_or_create(name='Cliente')
    permission = Permission.objects.using(alias).get(content_type__app_label='gestion',
        content_type__model='atencion', codename='view_atencion')
    group.permissions.set([permission.pk])


def backwards(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    group = Group.objects.using(schema_editor.connection.alias).filter(name='Cliente').first()
    if group is not None:
        group.permissions.clear()


class Migration(migrations.Migration):
    dependencies = [('cuentas', '0004_restore_municipal_roles')]
    operations = [migrations.RunPython(forwards, backwards)]
