# Cameras

## Tested hardware

The project is tested with **TP-Link Tapo C100, C200 and C500** IP cameras over
RTSP. Other ONVIF/RTSP cameras should work as long as ffmpeg can read their
stream, but only those models are verified.

| Model | Typical use | Notes |
|-------|-------------|-------|
| Tapo C100 | Indoor, fixed | 1080p, RTSP available after enabling a camera account |
| Tapo C200 | Indoor, pan/tilt | 1080p, RTSP available after enabling a camera account |
| Tapo C500 | Outdoor, pan/tilt | 1080p, same RTSP setup |

## Tapo RTSP setup

1. In the Tapo app open the camera → **Settings → Advanced Settings → Camera
   Account** and create a camera account (user and password). This is separate
   from the TP-Link cloud account.
2. Use that account in `config/cameras.auth`, not the TP-Link login.
3. RTSP listens on port `554`. Tapo cameras normally expose two paths:
   - `/stream1` — high quality;
   - `/stream2` — lower quality, faster to capture.
4. Confirm the exact path in the camera settings or the vendor documentation; if
   ffmpeg cannot open the stream, the path is the first thing to check.

Example:

```text
# config/cameras.conf
kuh=192.168.1.105:554/stream1:Kitchen
hall=192.168.1.106:554/stream2:Hallway
```

```text
# config/cameras.auth
kuh=camera-user:camera-password
hall=camera-user:camera-password
```

## Network requirements

- The container must reach each camera's IP and TCP port 554. On Docker Desktop
  the container network usually reaches the LAN; on Linux bridge networks the
  camera must route back to the host.
- Cameras with DHCP need a static lease, otherwise a reboot changes their address
  and the room silently breaks.
- Do not put cameras on a network that requires a VPN the container does not have.

## Diagnostics

```bash
# from the host
ffprobe -rtsp_transport tcp "rtsp://user:pass@192.168.1.105:554/stream1"

# from inside the container (proves the container can route to the camera)
docker compose exec api sh -c 'nc -z -w 2 192.168.1.105 554 && echo reachable'
```

ffprobe is not installed in the image; use it on the host. `nc` may be absent
too — in that case rely on `/health`, which performs a TCP probe from inside the
container.

## Snapshot quality

`width` scales the frame; without it the camera's native resolution is used.
Lower widths are captured and transferred faster. `stream2` plus `width=640` is
a good default for an agent that only needs to recognise a scene.

## Not used

ONVIF discovery, PTZ control, audio, recording and motion events are out of
scope for v1.4. Do not promise them.
