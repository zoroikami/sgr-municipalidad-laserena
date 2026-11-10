#!/usr/bin/env bash
# Run as root from a daily systemd timer on the EC2 host.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
domain="${1:?Indica el dominio público del certificado}"
[[ "$domain" =~ ^[A-Za-z0-9.-]+$ ]] || exit 1
docker run --rm \
  -v "$PWD/.private/letsencrypt:/etc/letsencrypt" \
  -v "$PWD/.private/acme:/var/www/acme" \
  certbot/certbot:v5.1.0 renew --quiet --webroot -w /var/www/acme
install -m 644 ".private/letsencrypt/live/$domain/fullchain.pem" deploy/tls/fullchain.pem
install -m 600 ".private/letsencrypt/live/$domain/privkey.pem" deploy/tls/privkey.pem
docker compose -f compose.yaml -f deploy/compose.production.yaml exec -T nginx nginx -t
docker compose -f compose.yaml -f deploy/compose.production.yaml exec -T nginx nginx -s reload
