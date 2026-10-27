# AGENTS.md — Room Snapshot API v1.3

> **Read this file first.** It holds the project's hard rules, exact commands and
> constraints for anyone (human or agent) changing this code. The README is the
> user-facing overview.

## What this is

A small service that turns RTSP surveillance cameras into a simple HTTP API **and** an
MCP server, so other projects (scripts, sites, apps, AI agents) can use cameras without
dealing with RTSP or credentials. Flask REST app + a separate MCP process (streamable
HTTP), both built from the same image, sharing config, capture and cache modules.

## Commands (exact)

```bash
# Dev environment
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# Lint and test
ruff check app tests
pytest tests/test_<name>.py      # run one file at a time (see Testing notes)
pytest -q                        # full suite (light)

# Dev servers
python -m app.app                # REST, uses HOST/PORT
python -m app.mcp_server         # MCP, uses MCP_PORT (streamable HTTP at /mcp)

# Docker
docker compose config -q
docker build -t room-snapshot-api:v1.3 .
docker compose up -d             # api on :5005, mcp on :5006
```

## Layout

| Path | Responsibility |
|------|----------------|
| `app/config.py` | `Config`, camera/auth/translation loading, path resolution |
| `app/i18n.py` | Language selection and localized room names |
| `app/auth.py` | Shared API-key extraction, comparison and global guard |
| `app/cache.py` | In-memory snapshot TTL cache and ETag |
| `app/capture.py` | ffmpeg capture (temp files), secret masking, TCP probe |
| `app/health.py` | Shared camera health aggregation |
| `app/app.py` | Flask app factory, routes, error handlers (`app:app` for gunicorn) |
| `app/mcp_server.py` | MCP server, tools and API-key ASGI middleware |
| `config/*.example` | Templates for installation-specific files (never real data) |
| `tests/` | pytest suite (unit + API via test client) |
| `Dockerfile`, `docker-compose.yml` | Image (non-root) and the `api` + `mcp` services |
| `.gitea/workflows/ci.yml` | CI: `ruff` + `pytest` |

## Hard rules

1. **English only in the repository** — code, comments, docstrings, log messages,
   `*.example` files, `README.md`, `LICENSE`, CI. The only Russian files are the
   `*-ru` ones: `README-ru.md` and `LICENSE-ru`. Commit messages are English too.
2. **Installation-specific files are never committed** — `config/cameras.conf`,
   `config/cameras.auth`, `config/rooms.i18n.json` are git-ignored; only their
   `*.example` templates are tracked, and none of them may enter the Docker image
   (they are volume-mounted).
3. **`docs/superpowers/` is never committed** — internal specs and plans only.
4. **Every REST and MCP endpoint requires `API_KEY`**, and the service is fail-closed:
   no key and `FLASK_DEBUG != true` means it must not start. Never weaken this.
5. **Camera credentials must never leak** — not into responses, logs, or error
   messages. Use `Camera.masked_url()` and `mask_secrets()`.
6. **The room code is a stable, language-neutral identifier** (e.g. `kuh`); only the
   label is localized. URLs, ACLs and integrations depend on the code never changing.
7. **Keep the client contract** — `GET /rooms` → `{code: name}`, `GET /snapshot/<code>`
   → `image/jpeg`, `GET /health` → HTTP 200 (camera failures only change the `status`
   field, never the HTTP code, so the container healthcheck does not restart-loop).
8. **The version lives in one place** — `Config.API_VERSION` in `app/config.py`;
   update it together with the README title/badges on a release.

## Breaking change to carry

Because `DEFAULT_LANG` is `en`, existing Russian-language clients (for example FLAI,
which builds Russian declensions from room names) must send `Accept-Language: ru` or
`?lang=ru`. The shared API key is also a breaking change: clients must send `X-API-Key`.

## Testing notes

- TDD: write the failing test first, watch it fail, then implement.
- Run tests **narrowly** (one file) while iterating; the full suite is light, but never
  start a second pytest run in parallel, and check free RAM before a broad run.
- ffmpeg, sockets and camera probes are monkeypatched in tests — no network access.
- `tests/conftest.py` sets a dummy `API_KEY` so importing the package succeeds.
