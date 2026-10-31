#!/bin/sh
# Preflight checks for the Room Snapshot API.
#
#   preflight.sh --local                  check the deployment prerequisites
#   preflight.sh [URL] [API_KEY]          check a running instance
#
# URL and API_KEY default to ROOM_SNAPSHOT_URL and ROOM_SNAPSHOT_API_KEY.
set -u

say() {
    printf '%-22s %s\n' "$1" "$2"
}

if [ "${1:-}" = "--local" ]; then
    if command -v docker >/dev/null 2>&1; then
        say docker "$(docker --version 2>/dev/null || echo unknown)"
    else
        say docker "MISSING - install Docker Engine"
    fi
    if docker compose version >/dev/null 2>&1; then
        say "docker compose" "$(docker compose version --short 2>/dev/null || echo ok)"
    else
        say "docker compose" "MISSING - install the compose plugin"
    fi
    if command -v ffmpeg >/dev/null 2>&1; then
        say ffmpeg "$(ffmpeg -version 2>/dev/null | head -n 1 | cut -d' ' -f1-3)"
    else
        say ffmpeg "not on PATH (fine inside Docker, required for a local run)"
    fi
    if command -v ss >/dev/null 2>&1; then
        for port in 5005 5006; do
            if ss -ltn 2>/dev/null | grep -q ":$port "; then
                say "port $port" "IN USE"
            else
                say "port $port" free
            fi
        done
    fi
    exit 0
fi

url=${1:-${ROOM_SNAPSHOT_URL:-http://localhost:5005}}
key=${2:-${ROOM_SNAPSHOT_API_KEY:-}}

if ! command -v curl >/dev/null 2>&1; then
    say curl "MISSING"
    exit 1
fi

if [ -z "$key" ]; then
    say "API key" "not set (pass it or export ROOM_SNAPSHOT_API_KEY)"
    exit 1
fi

tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp"' EXIT INT TERM

code=$(curl -sS -m 5 -H "X-API-Key: $key" -o "$tmp" -w '%{http_code}' "$url/info" 2>/dev/null || true)

case $code in
    200)
        say API "$url reachable"
        say version "$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$tmp" | head -n 1)"
        ;;
    401)
        say API "401 Unauthorized - wrong API key"
        exit 1
        ;;
    000|"")
        say API "$url unreachable"
        exit 1
        ;;
    *)
        say API "HTTP $code"
        exit 1
        ;;
esac

code=$(curl -sS -m 5 -H "X-API-Key: $key" -o "$tmp" -w '%{http_code}' "$url/rooms" 2>/dev/null || true)
if [ "$code" = "200" ]; then
    say rooms "$(cat "$tmp")"
else
    say rooms "HTTP $code"
fi
