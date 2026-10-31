---
name: room-snapshot
description: >-
  Use when the user wants to see, check or watch a room through an IP or RTSP
  camera: take a snapshot, list rooms, check whether cameras are online, or
  install, configure and run the Room Snapshot API (Flask REST + MCP server).
  Covers both a fresh Docker deployment on the user's machine and an already
  running instance on a local server, NAS or VPS.
---

# Room Snapshot API

Turns RTSP surveillance cameras into `GET /snapshot/<room>` (JPEG) and an MCP
server with four tools: `list_rooms`, `get_snapshot`, `room_info`, `health`.
Every endpoint requires an API key.

## Pick the mode before touching anything

| The user already has the service running | Mode |
|------------------------------------------|------|
| Yes, on this machine or a reachable host | **B — use it** |
| No, or they ask to install it | **A — deploy it** |
| Unclear | Ask: "Is the service already running, or should I install it?" |

Do not redeploy, restart or reconfigure an instance you were only asked to use.
If the user gives a URL and a key, that is mode B even if the repo is present.

## Mode B — use an existing installation

Inputs (from the user, the environment, or `.env` of that installation):

- `ROOM_SNAPSHOT_URL` — base URL, e.g. `http://192.168.1.10:5005`
- `ROOM_SNAPSHOT_API_KEY` — the shared key

Verify and read the rooms first, then take snapshots by room code:

```bash
curl -fsS -H "X-API-Key: $ROOM_SNAPSHOT_API_KEY" "$ROOM_SNAPSHOT_URL/rooms"
curl -fsS -H "X-API-Key: $ROOM_SNAPSHOT_API_KEY" "$ROOM_SNAPSHOT_URL/snapshot/kuh" -o /tmp/kuh.jpg
curl -fsS -H "X-API-Key: $ROOM_SNAPSHOT_API_KEY" "$ROOM_SNAPSHOT_URL/health"
```

Room codes come from `/rooms`; never invent one. If the image is delivered by an
MCP tool, show or describe the frame itself.

Rules for this mode:

- Never echo the API key or camera credentials into the answer or a log.
- Take room codes from `/rooms`, not from guesses or translations.
- If `/health` reports a camera unreachable, say so instead of retrying forever.
- A `502` means the camera did not deliver a frame (offline, wrong path, bad
  credentials); a `404` means the room code is wrong.
- Do not run `docker compose down`, edit `.env` or restart services on someone
  else's installation without explicit permission.

Details: `references/rest-api.md`, `references/mcp.md`.

## Mode A — deploy from scratch

Target: a machine with Docker and network access to the cameras. Cameras must be
reachable from the container, and each one needs an RTSP URL and credentials.

1. **Preflight.** `sh skills/room-snapshot/scripts/preflight.sh --local`
   checks docker, the compose plugin, ffmpeg and free ports. Fix what it reports.
2. **Get the code.** Clone the repository (ask for the fork/URL if it is not the
   default) and enter it.
3. **Install.** Run `./install.sh`. It creates `.env` with a generated `API_KEY`,
   copies the config templates, builds the image and waits for `/health`. It is
   idempotent and never overwrites existing files.
4. **Add cameras.** Edit `config/cameras.conf` (`code=ip:port/path:name`), and
   `config/cameras.auth` when per-camera credentials differ from `RTSP_AUTH`.
   Translations go into `config/rooms.i18n.json`. Then
   `docker compose restart api mcp`.
5. **Verify.** `/rooms` lists the codes, `/snapshot/<code>` returns JPEG bytes,
   `/health` shows every camera reachable. If a camera fails, see
   `references/troubleshooting.md` before changing credentials blindly.
6. **Register the MCP server** in the user's agent (Claude Code, Cursor, Claude
   Desktop) if they want tools instead of curl — see `references/mcp.md`.

Before stopping, report the REST URL, the MCP URL, which rooms exist and which
cameras are reachable. Do not print the API key unless the user asks for it.

Details: `references/deploy.md`, `references/configure.md`,
`references/cameras.md`.

## Reference map

| File | Use it for |
|------|------------|
| `references/deploy.md` | fresh install, prerequisites, ports, teardown |
| `references/configure.md` | cameras, credentials, translations, restart |
| `references/rest-api.md` | endpoints, parameters, status codes, caching |
| `references/mcp.md` | MCP tools and client registration |
| `references/cameras.md` | tested hardware, RTSP paths, Tapo specifics |
| `references/troubleshooting.md` | 401/404/502, ffmpeg, offline cameras |

The project is MIT licensed. Contributions and forks are welcome.
