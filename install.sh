#!/bin/sh
# First-time installer for the Room Snapshot API.
#
# Creates .env and the installation-specific config files from their templates
# (never overwriting existing ones), builds the image and starts both services.
# Safe to re-run: existing files and an existing API key are kept.
#
# Usage: ./install.sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

API_PORT=${API_PORT:-5005}
MCP_PORT=${MCP_PORT:-5006}

fail() {
    printf 'error: %s\n' "$1" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "the docker compose plugin is not installed"
command -v curl >/dev/null 2>&1 || fail "curl is required for the health check"

random_hex() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        od -An -tx1 -N32 /dev/urandom | tr -d ' \n'
    fi
}

env_value() {
    sed -n "s/^$1=\(.*\)$/\1/p" .env | head -n 1 | sed 's/^"//; s/"$//'
}

created_env=0
if [ ! -f .env ]; then
    [ -f .env.example ] || fail ".env.example is missing"
    api_key=$(random_hex)
    secret_key=$(random_hex)
    sed -e "s|^API_KEY=.*|API_KEY=\"$api_key\"|" \
        -e "s|^SECRET_KEY=.*|SECRET_KEY=\"$secret_key\"|" \
        .env.example > .env
    chmod 600 .env
    created_env=1
    printf 'created .env with a generated API key\n'
else
    printf 'keeping existing .env\n'
fi

if [ ! -f config/cameras.conf ]; then
    cp config/cameras.conf.example config/cameras.conf
    printf 'created config/cameras.conf from the template - edit it before relying on the cameras\n'
fi
if [ ! -f config/cameras.auth ]; then
    cp config/cameras.auth.example config/cameras.auth
    printf 'created config/cameras.auth from the template\n'
fi
if [ ! -f config/rooms.i18n.json ]; then
    cp config/rooms.i18n.example.json config/rooms.i18n.json
    printf 'created config/rooms.i18n.json from the template\n'
fi

api_key=$(env_value API_KEY)
[ -n "$api_key" ] || fail "API_KEY in .env is empty"

printf 'building and starting containers\n'
docker compose up -d --build

printf 'waiting for the API on http://localhost:%s\n' "$API_PORT"
ready=0
attempt=0
while [ "$attempt" -lt 90 ]; do
    if curl -fsS -m 3 -H "X-API-Key: $api_key" \
        "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
        ready=1
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ "$ready" -ne 1 ]; then
    printf 'error: the API did not become healthy in time\n' >&2
    docker compose logs --tail 30 api >&2 || true
    exit 1
fi

printf '\n'
printf 'Room Snapshot API is up.\n'
printf '  REST: http://localhost:%s\n' "$API_PORT"
printf '  MCP:  http://localhost:%s/mcp\n' "$MCP_PORT"
if [ "$created_env" -eq 1 ]; then
    printf '  API key: %s\n' "$api_key"
else
    printf '  API key: see .env\n'
fi
printf '\nNext steps:\n'
printf '  1. Edit config/cameras.conf with your camera addresses.\n'
printf '  2. docker compose restart api mcp\n'
printf '  3. curl -H "X-API-Key: <your-api-key>" http://localhost:%s/rooms\n' "$API_PORT"
