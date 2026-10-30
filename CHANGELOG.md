# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-10-31

### Added

- Agent skill in `skills/room-snapshot/` covering both a fresh deployment and the
  use of an existing installation, with focused references and a preflight script.
- `install.sh`: idempotent first-run installer that generates an API key, copies
  the config templates, builds the image and waits for a healthy API.
- MCP stdio transport (`python -m app.mcp_server --stdio`) for clients without
  remote HTTP support, such as Claude Desktop.
- `.env.example` entries for `CONFIG_DIR`, `CAMERAS_CONF`, `CAMERAS_AUTH` and
  `ROOMS_I18N`.
- Documentation: tested hardware (TP-Link Tapo C100, C200, C500), Claude Code and
  Cursor registration examples, this changelog.

### Changed

- `GET /snapshot/<code>` sets `Cache-Control: private` (was `public`) because
  every response requires an API key and must not be stored by shared proxies.
- MCP tools raise a readable tool error for an unknown room, a failed capture or
  an invalid `width` instead of returning `null`.
- The unused `lang` parameter was removed from the MCP `get_snapshot` tool; it
  never affected a JPEG.
- Importing a submodule such as `app.mcp_server` no longer creates the Flask app,
  so `API_KEY` is not needed for the stdio transport.
- The MCP middleware decodes header bytes as latin-1, so a malformed header gets a
  `401` instead of an internal error.

### Fixed

- `README`, `README-ru` and `AGENTS.md` now match version 1.4.

## [1.3.0]

Version 1.3 introduced the shared API key, per-camera credentials, the MCP server,
localized room names, the snapshot cache with ETags and the Docker Compose setup.
