#!/usr/bin/env bash
set -euo pipefail

# Deploy Doorbell on the EC2 host. Run from the repo root after `git pull`.
#
# Reads .env (in the repo root) and uses:
#   DOMAIN_API   -> baked into the frontend build as VITE_API_BASE_URL
#   DOMAIN_WEB   -> Caddy serves the React build here
#   (rest)       -> passed to the api container

if [[ ! -f .env ]]; then
  echo "Missing .env in repo root. Copy .env.example and fill it in." >&2
  exit 1
fi

# Load .env into the shell
set -a
# shellcheck disable=SC1091
source ./.env
set +a

: "${DOMAIN_API:?DOMAIN_API must be set in .env}"
: "${DOMAIN_WEB:?DOMAIN_WEB must be set in .env}"

echo "==> git pull"
git pull --ff-only || true

echo "==> Build frontend (VITE_API_BASE_URL=https://${DOMAIN_API})"
docker run --rm \
  -v "$(pwd)/frontend":/app \
  -w /app \
  -e VITE_API_BASE_URL="https://${DOMAIN_API}" \
  node:22-alpine \
  sh -c "npm ci || npm install; npm run build"

echo "==> Rebuild and restart compose"
docker compose up -d --build

echo "==> Wait for Caddy to settle, then health-check"
sleep 4
echo "Backend  : https://${DOMAIN_API}/health"
echo "Frontend : https://${DOMAIN_WEB}"
curl -sf "https://${DOMAIN_API}/health" \
  && echo "  ✓ API healthy" \
  || echo "  ! API health check failed — check 'docker compose logs api'"

echo "Done."
