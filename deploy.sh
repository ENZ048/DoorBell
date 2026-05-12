#!/usr/bin/env bash
set -euo pipefail

# Convenience deploy script: pull, build frontend, rebuild containers.
# Run on the EC2 host from the repo root.

echo "==> git pull"
git pull --ff-only

echo "==> Build frontend"
docker run --rm \
  -v "$(pwd)/frontend":/app \
  -w /app \
  node:22-alpine \
  sh -c "npm ci || npm install; npm run build"

echo "==> Rebuild and restart compose"
docker compose up -d --build

echo "==> Health check"
sleep 3
curl -sf http://localhost/health || curl -sf "https://${DOMAIN:-localhost}/health" || true

echo "Done."
