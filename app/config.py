"""Configuration loading for the Room Snapshot API.

Installation-specific data (cameras, credentials, translations) lives outside
version control; only ``*.example`` templates are tracked.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.getenv("CONFIG_DIR", "/app/config")


def resolve_config_path(env_var: str | None, filename: str) -> str:
    """Resolve a config file: env override, then CONFIG_DIR, then repo ``config/``."""
    if env_var:
        override = os.getenv(env_var)
        if override:
            return override
    primary = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(primary):
        return primary
    return os.path.join(REPO_ROOT, "config", filename)


def build_rtsp_url(ip: str, stream: str, auth: str) -> str:
    """Build an RTSP URL, URL-encoding credentials; omit userinfo when there is none."""
    host = f"[{ip}]" if ":" in ip else ip
    if not auth:
        return f"rtsp://{host}:{stream}"
    user, sep, password = auth.partition(":")
    if sep:
        userinfo = f"{quote(user, safe='')}:{quote(password, safe='')}@"
    else:
        userinfo = f"{quote(user, safe='')}@"
    return f"rtsp://{userinfo}{host}:{stream}"


@dataclass
class Camera:
    """A single camera and its RTSP endpoint."""

    code: str
    ip: str
    stream: str
    name: str
    url: str
    username: str = ""
    password: str = ""

    def masked_url(self) -> str:
        """Return the URL with credentials hidden."""
        if self.username or self.password:
            host = f"[{self.ip}]" if ":" in self.ip else self.ip
            return f"rtsp://***:***@{host}:{self.stream}"
        return self.url


class Config:
    """Environment-backed configuration and installation file loading."""

    RTSP_AUTH = os.getenv("RTSP_AUTH", "")
    API_KEY = os.getenv("API_KEY", "")
    API_VERSION = "1.4.0"
    API_TITLE = "Room Snapshot API"
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
    CORS_ORIGINS = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
    ]
    SNAPSHOT_CACHE_TTL = float(os.getenv("SNAPSHOT_CACHE_TTL", "5"))
    SNAPSHOT_TIMEOUT = int(os.getenv("SNAPSHOT_TIMEOUT", "15"))
    MAX_CONCURRENT_CAPTURES = int(os.getenv("MAX_CONCURRENT_CAPTURES", "4"))
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "0"))
    MCP_PORT = int(os.getenv("MCP_PORT", "8000"))

    @staticmethod
    def load_camera_auth(path: str | None = None) -> dict[str, str]:
        """Load per-camera credentials from ``cameras.auth`` (``code=user:password``)."""
        auth_path = path or resolve_config_path("CAMERAS_AUTH", "cameras.auth")
        credentials: dict[str, str] = {}
        if not os.path.exists(auth_path):
            return credentials
        try:
            with open(auth_path, encoding="utf-8") as handle:
                for line_num, raw in enumerate(handle, 1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        logger.warning("cameras.auth line %d: invalid format", line_num)
                        continue
                    code, value = line.split("=", 1)
                    code = code.strip().lower()
                    value = value.strip()
                    if not code or not value:
                        logger.warning("cameras.auth line %d: empty code or value", line_num)
                        continue
                    credentials[code] = value
        except OSError as exc:
            logger.error("Error reading %s: %s", auth_path, exc)
        return credentials

    @classmethod
    def load_cameras(
        cls, cameras_path: str | None = None, auth_path: str | None = None
    ) -> dict[str, Camera]:
        """Load cameras from ``cameras.conf`` (``code=ip:port/path[:name]``)."""
        conf_path = cameras_path or resolve_config_path("CAMERAS_CONF", "cameras.conf")
        cameras: dict[str, Camera] = {}
        if not os.path.exists(conf_path):
            logger.warning("Camera config %s not found", conf_path)
            return cameras

        auth_map = cls.load_camera_auth(auth_path)
        global_auth = getattr(cls, "RTSP_AUTH", "") or ""

        try:
            with open(conf_path, encoding="utf-8") as handle:
                for line_num, raw in enumerate(handle, 1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        logger.warning("cameras.conf line %d: missing '='", line_num)
                        continue
                    code, params = line.split("=", 1)
                    code = code.strip().lower()
                    params = params.strip()
                    if params.startswith("["):
                        end = params.find("]")
                        if end == -1:
                            logger.warning(
                                "cameras.conf line %d: unterminated IPv6 address", line_num
                            )
                            continue
                        ip = params[1:end].strip()
                        rest = params[end + 1:]
                        if not rest.startswith(":"):
                            logger.warning(
                                "cameras.conf line %d: expected ip:stream[:name]", line_num
                            )
                            continue
                        stream, _, name = rest[1:].partition(":")
                    else:
                        ip, sep, remainder = params.partition(":")
                        if not sep:
                            logger.warning(
                                "cameras.conf line %d: expected ip:stream[:name]", line_num
                            )
                            continue
                        stream, _, name = remainder.partition(":")
                    ip, stream, name = ip.strip(), stream.strip(), name.strip()
                    if not code or not ip or not stream:
                        logger.warning("cameras.conf line %d: missing ip or stream", line_num)
                        continue
                    port, _, _path = stream.partition("/")
                    if not port.isdigit():
                        logger.warning(
                            "cameras.conf line %d: stream %r has no numeric port", line_num, stream
                        )
                        continue
                    auth = auth_map.get(code) or global_auth
                    username, sep, password = auth.partition(":") if auth else ("", "", "")
                    cameras[code] = Camera(
                        code=code,
                        ip=ip,
                        stream=stream,
                        name=name or code,
                        url=build_rtsp_url(ip, stream, auth),
                        username=username,
                        password=password if sep else "",
                    )
        except OSError as exc:
            logger.error("Error reading %s: %s", conf_path, exc)
        return cameras

    @staticmethod
    def load_i18n(path: str | None = None) -> dict[str, dict[str, str]]:
        """Load localized room names from ``rooms.i18n.json``."""
        i18n_path = path or resolve_config_path("ROOMS_I18N", "rooms.i18n.json")
        if not os.path.exists(i18n_path):
            return {}
        try:
            with open(i18n_path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Error reading %s: %s", i18n_path, exc)
            return {}
        if not isinstance(data, dict):
            logger.error("%s must contain a JSON object", i18n_path)
            return {}
        return {
            str(code).lower(): {str(lang).lower(): str(name) for lang, name in names.items()}
            for code, names in data.items()
            if isinstance(names, dict)
        }
