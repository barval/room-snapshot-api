# Fresh deployment

## Prerequisites

- Docker Engine with the Compose v2 plugin (`docker compose version`).
- Network access from the host (and containers) to every camera, usually TCP 554.
- Free host ports `5005` (REST) and `5006` (MCP). Override with `API_PORT` and
  `MCP_PORT` only if you also edit `docker-compose.yml`.
- About 300 MB of disk for the image.

The image contains ffmpeg, so nothing else must be installed on the host.

## Recommended: the installer

```bash
git clone <repository-url> room-snapshot-api
cd room-snapshot-api
./install.sh
```

`install.sh` is idempotent. It:

1. checks docker, the compose plugin and curl;
2. creates `.env` from `.env.example` and fills `API_KEY` with a random value
   (an existing `.env` is kept as is);
3. copies `config/*.example` to the real config files without overwriting;
4. runs `docker compose up -d --build`;
5. waits up to 90 seconds for `GET /health` and prints the URLs.

If it times out it prints the last 30 log lines of the `api` service and exits 1.

## Manual equivalent

```bash
cp .env.example .env                 # set API_KEY; generate one, e.g. openssl rand -hex 32
cp config/cameras.conf.example config/cameras.conf
cp config/cameras.auth.example config/cameras.auth
cp config/rooms.i18n.example.json config/rooms.i18n.json
docker compose up -d --build
docker compose ps
```

## Services and ports

| Service | Container port | Host port | Purpose |
|---------|----------------|-----------|---------|
| `api` | 5000 (gunicorn) | 5005 | REST API |
| `mcp` | 8000 (uvicorn) | 5006 | MCP over streamable HTTP at `/mcp` |

Both containers mount `./config` read-write, run as the non-root `appuser` and
restart unless stopped. There is no database and no persistent state; snapshots
live in memory for `SNAPSHOT_CACHE_TTL` seconds.

## Without Docker (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt      # includes runtime requirements
export API_KEY=dev-only-key
python -m app.app                        # REST on HOST:PORT (default 0.0.0.0:5000)
python -m app.mcp_server                 # MCP on MCP_PORT (default 8000)
```

ffmpeg must be installed and on `PATH`; `/health` reports `ffmpeg_available: false`
when it is missing.

## Upgrading

```bash
git pull
docker compose up -d --build
```

Configuration files and `.env` are untouched by an upgrade.

## Teardown

```bash
docker compose down          # stops and removes containers, keeps config and .env
```

There is no volume to delete: removing the directory removes everything except
what the user copied elsewhere.

## Reverse proxy and HTTPS

The service speaks plain HTTP and authenticates with a header. In production put
it behind a TLS-terminating proxy and do not expose `5005`/`5006` directly to the
internet. Camera credentials never leave the container: they are used only in the
ffmpeg command line, and errors are masked before logging.

## Read-only secret handling

`.env`, `config/cameras.auth` and `config/cameras.conf` are git-ignored and are
excluded from the image by `.dockerignore`. Never commit them; never paste the
API key into a chat, an issue or a screenshot.
