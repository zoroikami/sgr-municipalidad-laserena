from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from .models import Usuario, Rol
from .permissions import sync_all_users, sync_user_group

@receiver(post_save, sender=Usuario)
def user_role_changed(sender, instance, raw=False, using='default', **kwargs):
    if not raw:
        sync_user_group(instance, using=using)

@receiver(post_save, sender=Rol)
def role_permissions_changed(sender, instance, using='default', **kwargs):
    for user in Usuario.objects.using(using).filter(rol=instance):
        sync_user_group(user, using=using)

@receiver(post_migrate)
def initialize_role_permissions(sender, using='default', **kwargs):
    if sender.label == 'gestion':
        create_permissions(sender, verbosity=0, using=using)
        sync_all_users(using=using)
