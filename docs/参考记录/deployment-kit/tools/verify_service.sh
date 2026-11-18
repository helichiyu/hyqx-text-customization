#!/usr/bin/env bash
set -euo pipefail

APP_PORT="${APP_PORT:-8000}"
BASE_URL="${BASE_URL:-http://127.0.0.1:${APP_PORT}}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
OPERATORS_PATH="${OPERATORS_PATH:-/operators}"
REQUIRE_AUTH="${REQUIRE_AUTH:-1}"
TOKEN="${X_TOKEN:-}"

if [[ "$REQUIRE_AUTH" == "1" && -z "$TOKEN" ]]; then
  echo "ERROR: set X_TOKEN or set REQUIRE_AUTH=0 for an auth-disabled service" >&2
  exit 1
fi

assert_code() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL ${label}: expected HTTP ${expected}, got ${actual}" >&2
    exit 1
  fi
  echo "OK ${label}: HTTP ${actual}"
}

echo "1. health without token"
assert_code 200 "$(curl -sS -o /tmp/op-health.out -w '%{http_code}' --max-time 10 "${BASE_URL}${HEALTH_PATH}")" health

if [[ "$REQUIRE_AUTH" == "1" ]]; then
  echo "2. business endpoint without token"
  assert_code 401 "$(curl -sS -o /tmp/op-no-token.out -w '%{http_code}' --max-time 10 "${BASE_URL}${OPERATORS_PATH}")" no_token
  echo "3. business endpoint with token"
  assert_code 200 "$(curl -sS -o /tmp/op-token.out -w '%{http_code}' --max-time 10 -H "X-Token: $TOKEN" "${BASE_URL}${OPERATORS_PATH}")" with_token
else
  echo "auth disabled; skipping 401/200 checks"
fi

echo "verification passed"