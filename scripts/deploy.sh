#!/usr/bin/env bash
# ReEngrave — Deploy / update script
# Run from the repo root on the server.
#
# Required env vars:
#   DOMAIN      your domain, e.g. reengrave.io
#   ACME_EMAIL  email for Let's Encrypt alerts
#
# Usage:
#   export DOMAIN=reengrave.io ACME_EMAIL=you@reengrave.io
#   bash scripts/deploy.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${DOMAIN:?Set DOMAIN env var, e.g. export DOMAIN=reengrave.io}"
: "${ACME_EMAIL:?Set ACME_EMAIL env var}"

echo "==> Deploying ReEngrave to $DOMAIN"
cd "$REPO_DIR"

echo "==> Pulling latest code"
git pull --ff-only

echo "==> Checking .env.production"
if [ ! -f backend/.env.production ]; then
  echo "ERROR: backend/.env.production not found."
  echo "Copy backend/.env.production.example and fill in all values."
  exit 1
fi

echo "==> Building images"
DOMAIN="$DOMAIN" ACME_EMAIL="$ACME_EMAIL" \
  docker compose -f docker-compose.prod.yml build

echo "==> Starting / restarting containers"
DOMAIN="$DOMAIN" ACME_EMAIL="$ACME_EMAIL" \
  docker compose -f docker-compose.prod.yml up -d

echo "==> Waiting for backend health check"
for i in $(seq 1 30); do
  if docker compose -f docker-compose.prod.yml exec -T backend \
      curl -sf http://localhost:8000/health &>/dev/null; then
    echo "Backend healthy."
    break
  fi
  echo "  Attempt $i/30 — waiting 5s…"
  sleep 5
done

echo ""
echo "===================================================="
echo "Deploy complete!"
echo "Site: https://$DOMAIN"
echo ""
echo "Useful commands:"
echo "  View logs:     docker compose -f docker-compose.prod.yml logs -f"
echo "  Backend logs:  docker compose -f docker-compose.prod.yml logs -f backend"
echo "  Stop:          docker compose -f docker-compose.prod.yml down"
echo "===================================================="
