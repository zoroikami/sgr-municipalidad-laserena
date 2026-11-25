"""Un host no permitido (por ejemplo, la IP pública sin el nombre del sitio) responde 400, no 500."""
from pathlib import Path

import pytest
from django.test import Client


@pytest.mark.django_db
def test_host_no_permitido_responde_400_con_la_pagina_de_error():
    respuesta = Client().get('/', HTTP_HOST='203.0.113.5')
    assert respuesta.status_code == 400
    assert 'Solicitud inválida' in respuesta.content.decode()


def test_nginx_redirige_la_ip_al_nombre_con_certificado():
    conf = (Path(__file__).resolve().parents[1] / 'deploy' / 'nginx.conf').read_text()
    assert 'sgr-$a-$b-$c-$d.sslip.io' in conf
    assert conf.count('return 301 https://$sgr_destino$request_uri;') == 2
