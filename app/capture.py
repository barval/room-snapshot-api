"""Snapshot capture via ffmpeg and lightweight camera probing."""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.error("ffmpeg check failed: %s", exc)
        return False


def mask_secrets(text: str, secrets: list[str]) -> str:
    """Replace each non-empty secret occurrence in ``text`` with ``***``."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def stream_port(stream: str) -> int:
    """Return the port part of a stream spec such as ``554/stream1``."""
    return int(stream.split("/", 1)[0])


def capture_snapshot(url: str, timeout: int = 15, width: int | None = None) -> bytes | None:
    """Capture a single JPEG frame from ``url``; return its bytes or None on failure."""
    descriptor, path = tempfile.mkstemp(suffix=".jpg")
    os.close(descriptor)
    command = [
        "ffmpeg",
        "-y",
        "-rtsp_transport",
        "tcp",
        "-timeout",
        "5000000",
        "-i",
        url,
        "-vframes",
        "1",
        "-q:v",
        "2",
    ]
    if width:
        command += ["-vf", f"scale={width}:-1"]
    command.append(path)

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        with open(path, "rb") as handle:
            data = handle.read()
        if data:
            return data
        logger.error("Captured frame is empty")
        return None
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else "unknown error"
        logger.error("ffmpeg failed: %s", mask_secrets(stderr, [url]))
        return None
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out after %ss", timeout)
        return None
    except OSError as exc:
        logger.error("ffmpeg I/O error: %s", mask_secrets(str(exc), [url]))
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def probe_camera(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to ``host:port`` succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
