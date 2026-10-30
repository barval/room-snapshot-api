# Configuration

Three installation-specific files live in `config/` and are mounted into both
containers. They are git-ignored; edit them on the host and restart the services.

## Cameras — `config/cameras.conf`

```text
# code=ip:port/path:name
kuh=192.168.1.105:554/stream1:Kitchen
gos=192.168.1.102:554/stream1:Living room
```

| Field | Rules |
|-------|-------|
| `code` | Unique, lowercase, stable. Used in URLs and ACLs. Latin letters, digits, `_`, `-`. |
| `ip` | Camera address reachable from the container. |
| `port` | RTSP port, almost always `554`. Must be numeric. |
| `path` | Vendor-specific stream path, e.g. `stream1` or `Streaming/Channels/101`. |
| `name` | Default label, used when `rooms.i18n.json` has no translation. Optional; falls back to the code. |

A malformed line is skipped with a warning in `docker compose logs api`; the rest
of the file still loads. Never change an existing code when you only want to
rename a room — change its label instead.

## Credentials — `config/cameras.auth`

```text
# code=user:password
kuh=tapo-user:tapo-password
gos=tapo-user:tapo-password
```

Resolution order per camera:

1. a record in `cameras.auth`;
2. the global `RTSP_AUTH` from `.env`;
3. no userinfo at all (an anonymous RTSP URL).

A password may contain `:`; only the first `:` separates the user. Both parts are
URL-encoded before they enter the RTSP URL, so `@`, `/` and spaces are safe.

Credentials never appear in API responses or logs: room details return a masked
URL (`rtsp://***:***@ip:port/path`).

## Translations — `config/rooms.i18n.json`

```json
{
  "kuh": { "ru": "Кухня", "en": "Kitchen" },
  "gos": { "ru": "Гостиная", "en": "Living room" }
}
```

- Keys are room codes; keys inside are language tags (lowercase, two letters).
- Missing file or missing language: the `name` from `cameras.conf` is used.
- The code stays language-neutral in every URL; only the label changes.
- `GET /rooms` returns `{code: label}`; `GET /rooms/<code>` also returns `names`
  with every translation plus the `default` label.

Language resolution: `?lang=` → `Accept-Language` → `DEFAULT_LANG`.

## Environment — `.env`

See `.env.example` for every variable and its default. The important ones:

| Variable | Meaning |
|----------|---------|
| `API_KEY` | Required. The service refuses to start without it (unless `FLASK_DEBUG=true`). |
| `RTSP_AUTH` | Fallback camera credentials. |
| `DEFAULT_LANG` | `en` or `ru`; the default label language. |
| `SNAPSHOT_CACHE_TTL` | Seconds a captured frame is reused. |
| `SNAPSHOT_TIMEOUT` | ffmpeg capture timeout in seconds. |
| `CORS_ORIGINS` | Comma-separated origins for browser clients; empty disables cross-origin. |
| `MCP_PORT` | MCP listen port inside the container. |

Never set `FLASK_DEBUG=true` in production: it disables the API-key requirement.

## Applying changes

```bash
docker compose restart api mcp
```

Cameras and translations are read at startup. Verify:

```bash
curl -fsS -H "X-API-Key: $API_KEY" http://localhost:5005/rooms
curl -fsS -H "X-API-Key: $API_KEY" http://localhost:5005/health
curl -fsS -H "X-API-Key: $API_KEY" http://localhost:5005/snapshot/kuh -o /tmp/kuh.jpg
```

`/health` returning HTTP 200 does not mean the cameras work: check the `status`
field and the per-camera `reachable` flags.

## Adding a room without editing files

Not supported by design. Keep `cameras.conf` as the single source of truth so a
restart cannot silently drop a room.
