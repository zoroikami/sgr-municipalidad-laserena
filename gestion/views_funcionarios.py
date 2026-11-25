"""Aviso al digitar un RUT: indica si pertenece a un funcionario municipal y su cargo."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from cuentas.roles import is_cliente
from cuentas.rut import RutError, normalize_rut
from .funcionarios import buscar_funcionario, ficha

PERMISOS = ('gestion.add_gestiontubo', 'gestion.change_gestiontubo', 'gestion.add_atencion', 'gestion.change_atencion')


@login_required
@require_POST
def rut_funcionario(request):
    # POST con CSRF: el RUT no queda en URLs, historiales ni registros de acceso.
    if is_cliente(request.user) or not any(request.user.has_perm(permiso) for permiso in PERMISOS):
        raise PermissionDenied('Solo el personal municipal que registra solicitudes puede verificar funcionarios.')
    try:
        rut = normalize_rut(request.POST.get('rut', ''))
    except RutError:
        return JsonResponse({'valido': False, 'funcionario': False})
    funcionario = buscar_funcionario(rut)
    if funcionario is None:
        return JsonResponse({'valido': True, 'funcionario': False})
    return JsonResponse({'valido': True, 'funcionario': True, **ficha(funcionario)})
