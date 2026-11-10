from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import GroupPermissionsForm, ManagedUserForm, ProfileForm
from .models import Perfil
from .roles import can_manage_users


@login_required
@require_http_methods(['GET', 'POST'])
def perfil(request):
    profiles = Perfil.objects.select_related('delegacion')
    profile = profiles.filter(user=request.user).first() if request.user.is_superuser else get_object_or_404(profiles, user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            if form.cleaned_data.get('foto'):
                if profile is None:
                    profile, _ = Perfil.objects.get_or_create(user=request.user)
                previous = profile.foto.name
                profile.foto = form.cleaned_data['foto']
                profile.save(update_fields=['foto'])
                if previous:
                    storage = profile.foto.storage
                    transaction.on_commit(lambda: storage.delete(previous))
        messages.success(request, 'Tu perfil se guardó.')
        return redirect('cuentas:perfil')
    return render(request, 'cuentas/perfil.html', {'form': form, 'perfil': profile, 'titulo': 'Mi perfil'})


@login_required
def foto(request, pk):
    if not request.user.is_superuser and pk != request.user.pk:
        raise Http404
    profile = get_object_or_404(Perfil, user_id=pk)
    if not profile.foto:
        raise Http404
    try:
        response = FileResponse(profile.foto.open('rb'), content_type='image/png' if profile.foto.name.endswith('.png') else 'image/jpeg')
    except FileNotFoundError as exc:
        raise Http404 from exc
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def managed_users(actor):
    if not can_manage_users(actor):
        raise PermissionDenied
    users = User.objects.select_related('perfil__delegacion').prefetch_related('groups').filter(perfil__isnull=False, is_superuser=False)
    if not actor.is_superuser:
        users = users.filter(perfil__delegacion=actor.perfil.delegacion, is_staff=False)
    return users.order_by('username')


@login_required
def usuarios(request):
    return render(request, 'cuentas/usuarios.html', {'usuarios': managed_users(request.user), 'titulo': 'Usuarios'})


@login_required
@require_http_methods(['GET', 'POST'])
def usuario_form(request, pk=None):
    users = managed_users(request.user)
    if not request.user.has_perm('cuentas.change_cuentas' if pk else 'cuentas.add_cuentas'):
        raise PermissionDenied
    user = get_object_or_404(users, pk=pk) if pk else User()
    form = ManagedUserForm(request.POST or None, instance=user, actor=request.user)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'La cuenta se guardó.')
        return redirect('cuentas:usuarios')
    return render(request, 'cuentas/usuario_form.html', {'form': form, 'obj': user, 'titulo': 'Editar usuario' if pk else 'Crear usuario'})


@login_required
@require_http_methods(['GET', 'POST'])
def roles(request):
    if not request.user.is_superuser or not request.user.has_perm('auth.change_group'):
        raise PermissionDenied
    form = GroupPermissionsForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.cleaned_data['group'].permissions.set(form.cleaned_data['permissions'])
        messages.success(request, 'Los permisos del grupo se guardaron.')
        return redirect('cuentas:roles')
    return render(request, 'cuentas/roles.html', {'form': form, 'grupos': Group.objects.prefetch_related('permissions').order_by('name'), 'titulo': 'Roles y permisos'})
