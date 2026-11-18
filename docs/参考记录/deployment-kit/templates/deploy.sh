#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found in $(pwd)" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "ERROR: Docker Compose is not available" >&2
  exit 1
fi

APP_NAME="${APP_NAME:-$(awk -F= '/^APP_NAME=/{print $2; exit}' .env)}"
APP_PORT="${APP_PORT:-$(awk -F= '/^APP_PORT=/{print $2; exit}' .env)}"
APP_NAME="${APP_NAME:-app}"
APP_PORT="${APP_PORT:-8000}"
HEALTH_PATH="${HEALTH_PATH:-$(awk -F= '/^HEALTH_PATH=/{print $2; exit}' .env)}"
HEALTH_PATH="${HEALTH_PATH:-/health}"

echo "Building and starting ${APP_NAME} on port ${APP_PORT}..."
"${COMPOSE[@]}" -f docker-compose.yml up -d --build

echo "Waiting for health check..."
for _ in $(seq 1 30); do
  if curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}${HEALTH_PATH}" >/tmp/${APP_NAME}-health.json 2>/dev/null; then
    echo "Health check passed:"
    cat /tmp/${APP_NAME}-health.json
    echo
    docker ps --filter "name=${APP_NAME}"
    exit 0
  fi
  sleep 2
done

echo "ERROR: health check failed. Recent logs:" >&2
"${COMPOSE[@]}" -f docker-compose.yml logs --tail=120 >&2 || true
exit 1
