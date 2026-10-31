# Agent skills

`room-snapshot/` teaches an AI agent how to use — and, when needed, install — this
project. It works in any agent that supports `SKILL.md` skills with progressive
disclosure (Claude Code, Cursor, Copilot, and others).

## Install

Copy or link the directory into the skills folder of your agent:

```bash
# Claude Code, user level
mkdir -p ~/.claude/skills
cp -r skills/room-snapshot ~/.claude/skills/

# or project level (shared through the repository)
mkdir -p .claude/skills
cp -r skills/room-snapshot .claude/skills/
```

For agents that read skills from a different folder, copy the same directory
there; the layout is self-contained and has no runtime dependencies.

## What the skill does

- **Mode A — deploy:** checks prerequisites, runs `./install.sh`, adds cameras,
  verifies the endpoints, registers the MCP server.
- **Mode B — use:** given a base URL and an API key, lists rooms, takes snapshots,
  reads health, and explains failures, without touching the deployment.

The skill points at focused references instead of loading everything at once:

| File | Contents |
|------|----------|
| `references/deploy.md` | fresh install, ports, upgrades, teardown |
| `references/configure.md` | cameras, credentials, translations, restart |
| `references/rest-api.md` | endpoints, parameters, errors, caching |
| `references/mcp.md` | MCP tools and client registration |
| `references/cameras.md` | tested hardware (TP-Link Tapo C100/C200/C500) |
| `references/troubleshooting.md` | 401/404/502, ffmpeg, offline cameras |
| `scripts/preflight.sh` | local prerequisites or live instance check |

## Smoke test the skill

Ask an agent with the skill installed:

> "What does the kitchen camera see right now?"

With a running instance it should call `/rooms`, then `/snapshot/<code>`, and
show the frame. Without one it should ask whether to install the service.

## Licence and listing

MIT, like the rest of the project: the skill may be copied, modified, bundled and
redistributed. It is published for free — no paid tier, no exclusivity.
