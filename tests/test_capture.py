"""Tests for snapshot capture and camera probing."""

import os
import socket
import subprocess
import threading
import time

import app.capture as capture_mod
from app.capture import (
    capture_snapshot,
    check_ffmpeg,
    mask_secrets,
    probe_camera,
    stream_port,
)


class _Completed:
    def __init__(self, stderr=b""):
        self.stderr = stderr


def test_check_ffmpeg_true(monkeypatch):
    monkeypatch.setattr(capture_mod.subprocess, "run", lambda *a, **k: _Completed())
    assert check_ffmpeg() is True


def test_check_ffmpeg_false_when_missing(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(capture_mod.subprocess, "run", _raise)
    assert check_ffmpeg() is False


def test_stream_port():
    assert stream_port("554/stream1") == 554
    assert stream_port("8554") == 8554


def test_capture_writes_file_returns_bytes_and_cleans_up(monkeypatch):
    seen = []

    def fake_run(*args, **kwargs):
        command = args[0] if args else kwargs["command"]
        seen.append(command)
        with open(command[-1], "wb") as handle:
            handle.write(b"\xff\xd8jpeg")
        return _Completed()

    monkeypatch.setattr(capture_mod.subprocess, "run", fake_run)
    data = capture_snapshot("rtsp://x", timeout=5)
    assert data == b"\xff\xd8jpeg"
    assert seen and not os.path.exists(seen[0][-1])


def test_capture_returns_none_on_process_error(monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"boom")

    monkeypatch.setattr(capture_mod.subprocess, "run", fail)
    assert capture_snapshot("rtsp://x", timeout=5) is None


def test_capture_returns_none_on_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(["ffmpeg"], 5)

    monkeypatch.setattr(capture_mod.subprocess, "run", timeout)
    assert capture_snapshot("rtsp://x", timeout=5) is None


def test_capture_passes_width_filter(monkeypatch):
    seen = []

    def fake_run(*args, **kwargs):
        command = args[0] if args else kwargs["command"]
        seen.append(command)
        with open(command[-1], "wb") as handle:
            handle.write(b"x")
        return _Completed()

    monkeypatch.setattr(capture_mod.subprocess, "run", fake_run)
    capture_snapshot("rtsp://x", timeout=5, width=320)
    assert "-vf" in seen[0]
    assert seen[0][seen[0].index("-vf") + 1] == "scale=320:-1"


def test_capture_places_timeout_before_input(monkeypatch):
    seen = []

    def fake_run(*args, **kwargs):
        command = args[0] if args else kwargs["command"]
        seen.append(command)
        with open(command[-1], "wb") as handle:
            handle.write(b"x")
        return _Completed()

    monkeypatch.setattr(capture_mod.subprocess, "run", fake_run)
    capture_snapshot("rtsp://x", timeout=5)
    assert seen[0].index("-timeout") < seen[0].index("-i")


def test_mask_secrets_hides_credentials():
    masked = mask_secrets("rtsp://u:p@host/s", ["u:p"])
    assert "u:p" not in masked
    assert "***" in masked


def test_probe_camera_true_for_open_port():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert probe_camera("127.0.0.1", port, timeout=1.0) is True
    finally:
        server.close()


def test_probe_camera_false_for_closed_port():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    assert probe_camera("127.0.0.1", port, timeout=0.2) is False


def test_capture_respects_concurrency_limit(monkeypatch):
    monkeypatch.setattr(capture_mod, "_semaphore", threading.BoundedSemaphore(1))
    state = {"active": 0, "peak": 0}
    lock = threading.Lock()

    def fake_run(*args, **kwargs):
        command = args[0] if args else kwargs["command"]
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        time.sleep(0.05)
        with lock:
            state["active"] -= 1
        with open(command[-1], "wb") as handle:
            handle.write(b"x")
        return _Completed()

    monkeypatch.setattr(capture_mod.subprocess, "run", fake_run)
    threads = [threading.Thread(target=capture_snapshot, args=("rtsp://x", 5)) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert state["peak"] == 1
