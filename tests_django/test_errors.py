import pytest
from django.test import override_settings


@pytest.mark.parametrize('code', [400, 403, 404, 500])
@override_settings(ROOT_URLCONF='tests_django.error_urls', DEBUG=False)
def test_error_pages_have_real_status_safe_message_and_exit(client, code):
    client.raise_request_exception = False
    response = client.get(f'/controlled/{code}/')
    assert response.status_code == code
    assert 'Volver al inicio' in response.content.decode()
    assert 'detalle interno' not in response.content.decode()
    assert b'Traceback' not in response.content
