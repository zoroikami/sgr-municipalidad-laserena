import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from redis.exceptions import RedisError

from .access import authorize, scoped
from .consulta import ATTEMPT_WINDOW, DeliveryError, allow_consultation_attempt, lookup_consultation, send_consultation_access
from .models import Atencion
from .public_forms import PublicConsultationForm

logger = logging.getLogger(__name__)
LOOKUP_ERROR = 'No pudimos consultar la atención. Revisa el folio y el código privado. Si necesitas uno nuevo, comunícate con tu delegación.'


@never_cache
@require_http_methods(['GET', 'POST'])
def consulta_publica(request):
    form = PublicConsultationForm(request.POST if request.method == 'POST' else None)
    result, error, status = None, '', 200
    if request.method == 'POST':
        try:
            allowed = allow_consultation_attempt(request)
        except (RedisError, OSError):
            allowed = False
            status = 503
            error = 'La consulta no está disponible por el momento. Inténtalo nuevamente en unos minutos.'
        if status == 200 and not allowed:
            status = 429
            error = 'Alcanzaste el límite de consultas. Espera 15 minutos antes de intentarlo nuevamente.'
        if allowed and form.is_valid():
            result = lookup_consultation(form.cleaned_data['folio'], form.cleaned_data['codigo'])
            if result is None:
                error = LOOKUP_ERROR
    response = render(request, 'gestion/consulta_publica.html', {
        'form': form, 'result': result, 'lookup_error': error, 'public_layout': True,
        'titulo': 'Consultar mi atención',
    }, status=status)
    # Preserve same-origin form navigation for CSRF while suppressing cross-site referrers.
    response['Referrer-Policy'] = 'same-origin'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    if status == 429:
        response['Retry-After'] = str(ATTEMPT_WINDOW)
    return response


def schedule_access_email(request, record_id):
    url = request.build_absolute_uri(reverse('gestion:consulta_publica'))

    def deliver():
        try:
            send_consultation_access(record_id, url)
        except (DeliveryError, Atencion.DoesNotExist):
            logger.warning('No se envió el acceso de consulta de la atención %s.', record_id)
            messages.warning(request, 'La atención está guardada, pero no pudimos enviar el correo. Revisa la dirección y vuelve a enviarlo desde el detalle de la atención.')
        else:
            messages.success(request, 'Enviamos el folio y el código privado al correo del solicitante.')

    transaction.on_commit(deliver, robust=True)


@login_required
@require_POST
def enviar_codigo_consulta(request, pk):
    authorize(request.user, Atencion, 'change')
    with transaction.atomic():
        record = get_object_or_404(scoped(request.user, Atencion).select_for_update(), pk=pk)
        if record.solicitante_email:
            schedule_access_email(request, record.pk)
        else:
            messages.warning(request, 'Agrega el correo del solicitante al editar la atención antes de enviar el código.')
    return redirect('gestion:detalle', modulo='atenciones', pk=pk)
