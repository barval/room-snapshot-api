# REST API

Base URL: `http://<host>:5005`. Every request needs the shared key, sent as
`X-API-Key: <key>` or `Authorization: Bearer <key>`.

```bash
curl -fsS -H "X-API-Key: $KEY" http://localhost:5005/rooms
```

A missing or wrong key returns `401 {"error": "Unauthorized"}`. `OPTIONS`
preflight requests are not authenticated.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/info` | Name, version, endpoint list, MCP settings. |
| GET | `/rooms` | `{code: label}` for every room. |
| GET | `/rooms/<code>` | `code`, `name`, `names`, `ip`, `stream`, masked `url`. |
| GET | `/snapshot/<code>` | JPEG frame. |
| GET | `/health` | Camera reachability, always HTTP 200. |

Room codes are case-insensitive in URLs (`/snapshot/KUH` works).

### `GET /rooms`

```json
{ "kuh": "Kitchen", "gos": "Living room" }
```

Language: `?lang=ru` → `Accept-Language` → `DEFAULT_LANG`.

### `GET /rooms/<code>`

```json
{
  "code": "kuh",
  "name": "Kitchen",
  "names": { "default": "Kitchen", "en": "Kitchen", "ru": "Кухня" },
  "ip": "192.168.1.105",
  "stream": "554/stream1",
  "url": "rtsp://***:***@192.168.1.105:554/stream1"
}
```

The URL is always masked; the real one is never exposed.

### `GET /snapshot/<code>`

| Parameter | Meaning |
|-----------|---------|
| `width` | Optional target width in pixels, `1..8000`. Height keeps the aspect ratio. |
| `fresh=1` | Bypass the cache and capture a new frame. `true` and `yes` also work. |

- Success: `200`, `Content-Type: image/jpeg`, plus `ETag` and
  `Cache-Control: private, max-age=<SNAPSHOT_CACHE_TTL>`.
- Send `If-None-Match: <etag>` (or `*`) to get `304 Not Modified` with no body.
- `400` — `width` is not an integer or out of range.
- `404` — unknown room code.
- `502` — ffmpeg could not produce a frame (camera offline, wrong path, bad
  credentials, unsupported codec).

```bash
curl -fsS -H "X-API-Key: $KEY" "http://localhost:5005/snapshot/kuh?width=640" -o kuh.jpg
```

Frames are cached in memory per `(room, width)` for a few seconds, so repeated
calls within the TTL are free. Different widths are captured separately.

### `GET /health`

```json
{
  "status": "healthy",
  "timestamp": 1760000000.0,
  "cameras_loaded": 2,
  "ffmpeg_available": true,
  "cameras": { "kuh": { "reachable": true }, "gos": { "reachable": false } }
}
```

`status` is `healthy` (all reachable), `degraded` (some) or `unhealthy` (none).
The HTTP status stays `200` on purpose so that a switched-off camera does not
trigger a container restart. Treat the body, not the code, as the health signal.

### `GET /info`

Returns the version, supported languages, the endpoint list and the MCP
transport/port/tools. Useful as a cheap connectivity and version probe.

## Errors

All errors are JSON:

```json
{ "error": "Not found", "message": "Room not found" }
```

| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid `width`) |
| 401 | Missing or wrong API key |
| 404 | Unknown room code |
| 500 | Internal error |
| 502 | Capture failed |

## Client notes

- Room codes come from `/rooms`; labels are for humans and change with the
  language.
- A snapshot reflects the moment of capture, not a live stream.
- Do not retry a `502` in a tight loop: one capture takes as long as the ffmpeg
  timeout in the worst case.
