#!/usr/bin/env bash
# Run once on the VM after DNS points at it: sudo /opt/ccp/docker/nginx/issue-certs.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

set -a; . ./.env; set +a
command -v certbot >/dev/null || { apt-get update && apt-get install -y certbot; }

COMPOSE="docker compose -f $PWD/docker-compose.yml -f $PWD/docker-compose.prod.yml"
certbot certonly --standalone --cert-name ccp \
  -d "$APP_DOMAIN" -d "$SIMULATOR_DOMAIN" \
  --non-interactive --agree-tos --register-unsafely-without-email \
  --pre-hook "$COMPOSE stop nginx" \
  --post-hook "$COMPOSE up -d nginx"
