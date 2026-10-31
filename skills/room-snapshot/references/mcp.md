# MCP server

Transport: **streamable HTTP** at `http://<host>:5006/mcp`, authenticated with the
same key as the REST API (`X-API-Key` header or `Authorization: Bearer`).

Tools:

| Tool | Arguments | Returns |
|------|-----------|---------|
| `list_rooms` | `lang?` | `{code: label}` |
| `get_snapshot` | `room`, `width?` | JPEG as image content |
| `room_info` | `room`, `lang?` | Room details with a masked URL |
| `health` | — | Status, camera reachability, ffmpeg availability |

Errors (unknown room, capture failure, bad `width`) come back as tool errors with
a readable message, so the agent can explain the problem instead of showing an
empty image.

## Claude Code

```bash
claude mcp add --transport http room-snapshot http://localhost:5006/mcp \
  --header "X-API-Key: <your-api-key>"
claude mcp list
```

## Cursor

`~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project):

```json
{
  "mcpServers": {
    "room-snapshot": {
      "url": "http://localhost:5006/mcp",
      "headers": { "X-API-Key": "<your-api-key>" }
    }
  }
}
```

## Any client that accepts a URL transport

```json
{
  "mcpServers": {
    "room-snapshot": {
      "url": "http://192.168.1.10:5006/mcp",
      "headers": { "X-API-Key": "<your-api-key>" }
    }
  }
}
```

## Claude Desktop and other stdio-only clients

The same server can run over stdio with `--stdio`. This is for a local checkout:
it bypasses the API key because the pipe is local and trusted, and it needs
Python, the runtime requirements and ffmpeg on the machine.

```json
{
  "mcpServers": {
    "room-snapshot": {
      "command": "python",
      "args": ["-m", "app.mcp_server", "--stdio"],
      "cwd": "/path/to/room-snapshot-api"
    }
  }
}
```

No API key is needed: the stdio pipe is local and trusted. Config files are read
from `./config` inside the checkout.

## Docker: exposing MCP beyond localhost

The container listens on `0.0.0.0:8000`, published as `5006` on the host. To use
it from another machine, put it behind TLS and keep the API key private. Never
expose it to the internet without a proxy.

## Notes

- One server instance is enough for both REST and MCP clients; they share config
  and the cache only within their own process.
- `get_snapshot` returns an image content block, not a URL. The client renders it.
- Tool names and room codes are part of the integration contract; do not rename
  them casually.
