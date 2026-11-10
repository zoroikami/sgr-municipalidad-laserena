#!/usr/bin/env bash
# Run on the existing EC2 checkout after the reviewed PR is merged to main.
set -Eeuo pipefail
cd "$(dirname "$0")"
public_origin="${1:-}"
if [[ ! "$public_origin" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]]; then
  echo 'Uso: ./deploy_ec2.sh https://dominio-publico-de-la-instancia' >&2
  exit 1
fi
command -v docker >/dev/null
docker compose version >/dev/null
[[ -f .env && -f deploy/tls/fullchain.pem && -f deploy/tls/privkey.pem ]] || {
  echo 'Configura .env privado y los certificados TLS en deploy/tls antes de desplegar.' >&2; exit 1;
}
[[ "$(git branch --show-current)" == main ]] || {
  echo 'Integra la rama mediante un PR revisado y ejecuta el despliegue desde main.' >&2; exit 1;
}
git diff --quiet && git diff --cached --quiet || {
  echo 'El checkout tiene cambios sin commit. Despliega un commit identificable.' >&2; exit 1;
}
export APP_COMMIT
APP_COMMIT="$(git rev-parse HEAD)"
compose=(docker compose -f compose.yaml -f deploy/compose.production.yaml)
"${compose[@]}" config --quiet
mkdir -p .private/backups
chmod 700 .private .private/backups
"${compose[@]}" up -d mysql redis
"${compose[@]}" build web
"${compose[@]}" run --rm web python manage.py check --deploy --fail-level WARNING
backup_file=".private/backups/mysql-$(date -u +%Y%m%dT%H%M%SZ).sql"
(umask 077; "${compose[@]}" exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump --single-transaction --no-tablespaces -u"$MYSQL_USER" "$MYSQL_DATABASE"' > "$backup_file")
"${compose[@]}" run --rm web python manage.py migrate --noinput
"${compose[@]}" run --rm --user "$(id -u):$(id -g)" -v "$PWD/.private:/private" web python manage.py seed_demo --update-names --credentials-file /private/cuentas-demo.json
"${compose[@]}" run --rm --user "$(id -u):$(id -g)" -v "$PWD/.private:/private" web python manage.py provision_superadmin --credentials-file /private/superadmin.json
"${compose[@]}" run --rm web python manage.py verify_environment --demo --production
"${compose[@]}" run --rm web python manage.py collectstatic --noinput
"${compose[@]}" up -d web nginx
curl --fail --silent --show-error --retry 5 --retry-delay 2 "$public_origin/api/health/"
echo
echo "Commit desplegado: $APP_COMMIT"
echo "Acceso público: $public_origin"
echo 'Comprueba WebSocket, recuperación por correo y las seis cuentas en navegadores separados.'
