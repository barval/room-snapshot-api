"""Shared camera health aggregation for the REST and MCP servers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .capture import probe_camera, stream_port
from .config import Camera


def camera_state(cameras: dict[str, Camera], timeout: float = 1.0) -> dict[str, dict]:
    """Probe every camera in parallel; return ``{code: {"reachable": bool}}``."""

    def probe(code: str) -> tuple[str, dict]:
        camera = cameras[code]
        try:
            reachable = probe_camera(camera.ip, stream_port(camera.stream), timeout)
        except ValueError:
            reachable = False
        return code, {"reachable": reachable}

    if not cameras:
        return {}
    with ThreadPoolExecutor(max_workers=min(8, len(cameras))) as pool:
        return dict(pool.map(probe, list(cameras)))


def overall_status(states: dict[str, dict]) -> str:
    """Aggregate per-camera reachability into ``healthy``/``degraded``/``unhealthy``."""
    reachable = [state["reachable"] for state in states.values()]
    if not reachable:
        return "unhealthy"
    if all(reachable):
        return "healthy"
    if any(reachable):
        return "degraded"
    return "unhealthy"
