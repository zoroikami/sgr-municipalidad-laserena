"""Production must never silently fall back to a local SQLite database."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('debug,sqlite,expected', [('false', 'true', False), ('true', 'true', True), ('false', 'false', True)])
def test_database_configuration_requires_explicit_development_sqlite(debug, sqlite, expected):
    env = os.environ | {'DJANGO_DEBUG': debug, 'USE_SQLITE': sqlite,
        'DB_ENGINE': 'django.db.backends.sqlite3' if sqlite == 'true' else 'django.db.backends.mysql',
        'DB_NAME': 'config_test', 'DB_USER': 'config_test', 'DB_PASSWORD': 'fixture-only',
        'DJANGO_SECRET_KEY': 'configuration-fixture-only-' * 4, 'DJANGO_ALLOWED_HOSTS': 'localhost'}
    result = subprocess.run([sys.executable, '-c', 'import config.settings'],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True)
    assert (result.returncode == 0) is expected
    if not expected:
        assert 'SQLite solo' in result.stderr
