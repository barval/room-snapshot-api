# Room Snapshot API v1.3

**English** | [Русский](README-ru.md)

[![Python 3.15](https://img.shields.io/badge/python-3.15-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-%230db7ed.svg)](https://www.docker.com/)

A small service that turns RTSP surveillance cameras into a simple HTTP API and an
MCP server. Other projects — scripts, sites, apps and AI agents — talk to it instead
of dealing with RTSP URLs and camera credentials.

## Features

- **HTTP API** for room lists, room details and JPEG snapshots.
- **MCP server** (streamable HTTP) so AI agents get cameras as ready-made tools.
- **Per-camera credentials** instead of one shared login.
- **API key authentication** on every endpoint (REST and MCP).
- **Concurrent capture**: requests to different cameras run in parallel.
- **In-memory snapshot cache** with `ETag`/`304` and `Cache-Control`.
- **Localized room names** (`ru`/`en`) with a per-installation translation file.
- **Real health check**: live TCP probes of every camera.
- Docker image, runs as a non-root user.

## Requirements

- Docker and Docker Compose (recommended), or
- Python 3.15 and FFmpeg for local development.
- Network access to the RTSP cameras.

## Quick start

```bash
git clone git@gitea.prits.ru:barval-my/room-snapshot-api.git
cd room-snapshot-api

cp .env.example .env               # set API_KEY and RTSP_AUTH
cp config/cameras.conf.example config/cameras.conf
cp config/cameras.auth.example config/cameras.auth     # optional per-camera credentials
cp config/rooms.i18n.example.json config/rooms.i18n.json  # optional translations

docker compose up -d
```

The REST API is available at `http://localhost:5005` and the MCP server at
`http://localhost:5006/mcp`.

## Installation-specific files

The set of cameras, their names and credentials differ per installation and are
**never committed**. Only the `*.example` templates are tracked; the real files live
in `config/` and are excluded from the Docker image (mounted as a volume).

| File | Purpose | Format |
|------|---------|--------|
| `config/cameras.conf` | Camera list | `code=ip:port/path:name` |
| `config/cameras.auth` | Per-camera credentials (optional) | `code=user:password` |
| `config/rooms.i18n.json` | Localized room names (optional) | `{"kuh": {"ru": "Кухня", "en": "Kitchen"}}` |

- A camera without a record in `cameras.auth` falls back to the global `RTSP_AUTH`.
- A camera without any credentials gets a URL without userinfo.
- A missing `rooms.i18n.json` means names from `cameras.conf` are used as-is.

## Configuration (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Shared API key for REST and MCP. Required. | — |
| `RTSP_AUTH` | Fallback camera credentials `user:password`. | `` |
| `CORS_ORIGINS` | Comma-separated allowed origins; empty blocks cross-origin. | `` |
| `DEFAULT_LANG` | Default room-name language (`en` or `ru`). | `en` |
| `SNAPSHOT_CACHE_TTL` | Snapshot cache lifetime, seconds. | `5` |
| `SNAPSHOT_TIMEOUT` | ffmpeg capture timeout, seconds. | `15` |
| `MCP_PORT` | MCP server port. | `8000` |
| `FLASK_DEBUG` | Debug mode (never in production). | `false` |
| `SECRET_KEY` | Flask session secret. | — |
| `HOST`, `PORT` | Bind address/port (development server). | `0.0.0.0`, `5000` |

The service **fails closed**: if `API_KEY` is empty and `FLASK_DEBUG` is not `true`,
it refuses to start.

## Authentication

Every request needs the shared key, either as an `X-API-Key` header or as
`Authorization: Bearer <key>`:

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/rooms
```

A missing or wrong key returns `401 {"error": "Unauthorized"}`.

## REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/info` | API metadata and endpoint list. |
| GET | `/rooms` | `{code: name}` for all rooms (language via `?lang=` / `Accept-Language`). |
| GET | `/rooms/<code>` | Room details: `name`, `names`, `ip`, `stream`, masked `url`. |
| GET | `/snapshot/<code>` | JPEG snapshot. Params: `width=<px>`, `fresh=1`, `lang=`. |
| GET | `/health` | Live camera reachability; always HTTP 200. |

Snapshot responses carry `ETag` and `Cache-Control`; send `If-None-Match` to get
`304 Not Modified`. `?fresh=1` bypasses the cache and refreshes it.

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/snapshot/kuh?width=640 -o kuh.jpg
```

## MCP server

AI agents connect over **streamable HTTP** at `http://host:5006/mcp`, using the same
`API_KEY` (`X-API-Key` header or `Authorization: Bearer`).

Tools exposed:

| Tool | Arguments | Returns |
|------|-----------|---------|
| `list_rooms` | `lang?` | Room code → localized name. |
| `get_snapshot` | `room`, `width?`, `lang?` | JPEG frame as image content. |
| `room_info` | `room`, `lang?` | Room details with a masked URL. |
| `health` | — | Camera reachability and ffmpeg availability. |

Example MCP client configuration (URL transport):

```json
{
  "mcpServers": {
    "room-snapshot": {
      "url": "http://localhost:5006/mcp",
      "headers": { "X-API-Key": "your-api-key" }
    }
  }
}
```

## Localization

The room **code** (`kuh`) is a stable, language-neutral identifier used by URLs, ACLs
and integrations. Only the **label** is translated. Language resolution order:
`?lang=` → `Accept-Language` header → `DEFAULT_LANG`. `/rooms` keeps returning
`{code: name}`; `/rooms/<code>` additionally includes `names` with every translation.

Because the default is `en`, existing Russian-language clients (for example FLAI) must
send `Accept-Language: ru` or `?lang=ru` to keep receiving Russian labels.

## Monitoring

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5005/health | jq
```

`status` is `healthy`, `degraded` (some cameras unreachable) or `unhealthy` (none).
The HTTP code stays 200 so a switched-off camera does not restart the container.
`docker compose logs -f` shows JSON logs.

## Docker

```bash
docker compose build
docker compose up -d      # api on :5005, mcp on :5006
docker compose down
```

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

CI runs `ruff` and `pytest` on every push (`.gitea/workflows/ci.yml`).

## Security notes

- Credentials live in `config/cameras.auth` and `.env`, never in git or the image.
- Every endpoint requires the API key; the service will not start without one.
- Requests to different cameras run in parallel; one slow stream does not block the rest.
- Use HTTPS and a reverse proxy in production; camera credentials are URL-encoded and
  masked in API responses and logs.

## Roadmap

- MJPEG / WebSocket live streams
- ONVIF camera discovery
- Web viewing UI
- Archive recording
- Prometheus metrics

## License

MIT — see [LICENSE](LICENSE). Russian translation: [LICENSE-ru](LICENSE-ru).
