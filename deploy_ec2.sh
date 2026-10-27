#!/usr/bin/env bash
# Ejecutar desde una copia actualizada del proyecto en EC2.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"
if [ ! -f .env ]; then
    echo 'Cree .env desde .env.example y configure producción antes de desplegar.' >&2
    exit 1
fi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py check --deploy
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
# Gunicorn se ejecuta con el usuario actual detrás de un proxy HTTPS.
exec .venv/bin/gunicorn sgr.wsgi:application --bind "127.0.0.1:${PORT:-8000}" --workers 2 --access-logfile -
