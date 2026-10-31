# Troubleshooting

Start with the two cheap checks:

```bash
docker compose ps
curl -i -H "X-API-Key: $KEY" http://localhost:5005/health
```

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| `401 Unauthorized` | Wrong key, quotes kept, or the wrong header | Compare with `.env`; strip quotes; use `X-API-Key` |
| Every request 401 even with the key | `FLASK_DEBUG` was on when the app started, or the key changed after start | Restart: `docker compose restart api mcp` |
| Container exits immediately | `api`: empty `API_KEY`; `mcp`: same | Set it in `.env`, restart |
| `404 Room not found` | Code typo, or `cameras.conf` not mounted | `GET /rooms`; check the volume and the logs |
| `/rooms` is `{}` but the file has entries | Malformed lines, missing port, duplicate codes | `docker compose logs api` shows the line number |
| `502 Snapshot capture failed` | Camera offline, wrong path, bad credentials, unsupported codec | See below |
| `/health` is 200 but `status` is `degraded` | Some camera TCP ports do not answer | Check the camera and the network |
| `ffmpeg_available: false` | Local run without ffmpeg | Install ffmpeg or use Docker |
| Snapshot is old | Cache TTL | Add `?fresh=1` or lower `SNAPSHOT_CACHE_TTL` |
| First snapshot is slow | ffmpeg opens the stream and waits for a keyframe | Use `stream2`, a smaller `width`, or raise `SNAPSHOT_TIMEOUT` |
| MCP client cannot connect | Wrong URL or missing header | URL must end in `/mcp`; add `X-API-Key` |
| `429` for every client behind a proxy | The limit counts the proxy address | Keep the app limit at `0` and limit in the proxy, or configure trusted proxy headers |
| MCP tool returns an error about an unknown room | Code not in `cameras.conf` | Call `list_rooms` first |

## Diagnosing a 502

1. Is the room code correct? `curl /rooms`.
2. Is the camera reachable from the container? `/health` uses a TCP probe:
   `"reachable": true` already proves the port is open.
3. Is the stream path right? Check the vendor app or documentation. Tapo cameras
   use `/stream1` or `/stream2`.
4. Are the credentials the **camera account**, not the cloud account?
5. Test the exact URL on the host with `ffprobe`:

   ```bash
   ffprobe -rtsp_transport tcp "rtsp://user:pass@192.168.1.105:554/stream1"
   ```

   A `401`/`403` from the camera means credentials; a timeout means network or
   path; an unsupported-codec error means ffmpeg cannot decode that profile.
6. Only then increase `SNAPSHOT_TIMEOUT` — slow streams are common on Wi-Fi.

Never paste a real RTSP URL with credentials into a bug report. Replace the user
and password first.

## Port conflicts

```bash
ss -ltn | grep -E ':(5005|5006)'
```

Change the host side in `docker-compose.yml` and the URLs you use.

## Logs

```bash
docker compose logs -f api
docker compose logs -f mcp
```

Logs are JSON lines. Camera credentials are masked; the API key never appears.

## Resetting

```bash
docker compose down
docker compose up -d --build
```

If configuration looks corrupted, re-copy the templates (`config/*.example`) to a
new name, fill them in, and restart. Never commit the result.

## When to stop and ask

- The camera rejects credentials and the user is not present to supply new ones.
- The deployment is on someone else's network or machine.
- A fix requires changing ports, DNS or firewall rules.
- The user asks for live video, PTZ, audio or recording — that is not implemented.
