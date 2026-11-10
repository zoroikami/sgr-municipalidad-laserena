"""Controlled failures used only by tests; never exposed in production routes."""
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.urls import include, path


def bad(request):
    raise SuspiciousOperation('detalle interno que no debe mostrarse')


def forbidden(request):
    raise PermissionDenied('detalle interno que no debe mostrarse')


def missing(request):
    raise Http404('detalle interno que no debe mostrarse')


def broken(request):
    raise RuntimeError('detalle interno que no debe mostrarse')


urlpatterns = [path('controlled/400/', bad), path('controlled/403/', forbidden),
               path('controlled/404/', missing), path('controlled/500/', broken),
               path('', include('config.urls'))]
handler400 = 'config.errors.bad_request'
handler403 = 'config.errors.permission_denied'
handler404 = 'config.errors.not_found'
handler500 = 'config.errors.server_error'
