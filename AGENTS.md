# Opencode Python SDK — AGENTS.md

## Project

Python SDK for [Opencode](https://opencode.ai) — a PyPI package (`opencode-ai`) that
launches an `opencode serve` subprocess and provides both high-level and low-level APIs
to interact with any Opencode HTTP API endpoint.

## Repository

- GitHub: https://github.com/[user]/opencode-py
- Upstream: https://github.com/anomalyco/opencode
- OpenAPI spec: https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/sdk/openapi.json

## Key Decisions

### SDK architecture

- Package name: `opencode-ai`
- Build system: `hatchling`
- Min Python: 3.10
- Only hard dependency: `httpx>=0.27.0`
- Pydantic models NOT required for MVP — use TypedDict from `typing`
- Two API versions supported:
  - **V1** — session create/delete/list, file, VCS, config, MCP, LSP, etc.
  - **V2** — session prompt, wait, context, messages, models, providers

### High-level API (import from `opencode`)

```python
from opencode import Opencode, opencode

with Opencode() as ai:
    answer = ai.ask("What is the capital of France?")

async with Opencode() as ai:
    answer = await ai.ask("Explain async")

result = opencode("Quick one-shot question")
```

### Low-level API

```python
with Opencode() as ai:
    session = ai.create_session()
    msg = session.prompt("Hello")
    session.prompt("Second question")
    for m in session.messages():
        print(m)

    ai.client.file_read("src/main.py")
    ai.client.vcs_diff("HEAD~3")
```

### Binary management

- First try `opencode` in PATH
- If not found, download from GitHub releases:
  `https://github.com/anomalyco/opencode/releases`
- Platform detection: `{os}-{arch}` → win32-x64, darwin-x64, darwin-arm64, linux-x64, linux-arm64
- Store in `~/.opencode/bin/`
- Config passed via `OPENCODE_CONFIG_CONTENT` env var

### Communication

- HTTP REST to `http://127.0.0.1:{port}`
- Server started via `opencode serve --hostname=... --port=...`
- Wait for stdout line containing `"opencode server listening on"`
- Stop via `taskkill /T /F` (win32) or `SIGTERM` (others)

## Correct API Paths (from OpenAPI spec)

### V2 (session operations)
```
POST   /api/session/{sessionID}/prompt    — send prompt
POST   /api/session/{sessionID}/wait      — wait for idle (204)
GET    /api/session/{sessionID}/context   — get context messages
GET    /api/session/{sessionID}/message   — list messages (paginated)
POST   /api/session/{sessionID}/compact   — compact session
GET    /api/session                      — list sessions (paginated)
GET    /api/model                        — list models
GET    /api/provider                     — list providers
GET    /api/provider/{providerID}        — get provider
```

### V1 (session lifecycle + everything else)
```
POST   /session                          — create session
GET    /session                          — list sessions
GET    /session/{sessionID}              — get session
DELETE /session/{sessionID}              — delete session
PATCH  /session/{sessionID}              — update session
POST   /session/{sessionID}/message      — send V1 prompt
POST   /session/{sessionID}/fork         — fork session
POST   /session/{sessionID}/abort        — abort session
POST   /session/{sessionID}/share        — share session
DELETE /session/{sessionID}/share        — unshare
POST   /session/{sessionID}/init         — init session
POST   /session/{sessionID}/summarize     — summarize
GET    /session/{sessionID}/children     — child sessions
GET    /session/{sessionID}/todo         — todos
GET    /session/{sessionID}/diff         — file diff
GET    /session/{sessionID}/message      — list messages
GET    /session/{sessionID}/message/{messageID} — get message
DELETE /session/{sessionID}/message/{messageID} — delete message
POST   /session/{sessionID}/prompt_async  — async prompt
POST   /session/{sessionID}/command       — send command
POST   /session/{sessionID}/shell         — run shell
POST   /session/{sessionID}/revert        — revert
POST   /session/{sessionID}/unrevert      — restore reverted
```

### File
```
GET /file/content?path=...     — read file content
GET /file?path=...             — list directory
GET /file/status?path=...      — file status
```

### Find
```
GET /find?pattern=...&include=...  — find text
GET /find/file?query=...           — find files
GET /find/symbol?query=...         — find symbols
```

### VCS
```
GET /vcs                         — VCS info
GET /vcs/status?mode=git         — status
GET /vcs/diff?mode=git&base=...  — diff
POST /vcs/apply?mode=git         — apply patch
```

### Config
```
GET  /config
PATCH /config   { config: {...} }
GET  /config/providers
GET  /global/config
PATCH /global/config
```

### Global
```
GET   /global/health
GET   /global/event     (SSE)
POST  /global/dispose
POST  /global/upgrade    { target?: string }
```

### Auth
```
PUT    /auth/{providerID}    { auth: ... }
DELETE /auth/{providerID}
```

### App
```
POST /log     { level, message, ... }
GET  /agent   list agents
```

### MCP
```
GET    /mcp
PUT    /mcp         { config: ... }
POST   /mcp/{name}/connect
DELETE /mcp/{name}/connect
GET    /mcp/status
```

### Provider
```
GET /provider
GET /provider/{providerID}/auth
```

### Tool
```
GET /experimental/tool
GET /experimental/tool/ids
```

### Permission
```
GET  /permission
POST /permission/{permissionID}  { ... }
```

### Question
```
GET    /question
POST   /question/{questionID}   { answer: ... }
DELETE /question/{questionID}
```

### LSP / Formatter
```
GET /lsp
GET /formatter
```

### PTY
```
GET    /pty
POST   /pty
GET    /pty/{ptyID}
DELETE /pty/{ptyID}
PATCH  /pty/{ptyID}
GET    /pty/shells
```

### Path
```
GET /path
```

### Instance
```
POST /instance/dispose
```

### Command
```
GET /command
```

### Project
```
GET    /project
GET    /project/current
PATCH  /project
POST   /project/init-git
```

### Worktree (experimental)
```
GET    /experimental/worktree
POST   /experimental/worktree
DELETE /experimental/worktree
POST   /experimental/worktree/reset
```

### Workspace (experimental)
```
GET    /experimental/workspace
POST   /experimental/workspace
GET    /experimental/workspace/status
DELETE /experimental/workspace/{workspaceID}
POST   /experimental/workspace/warp
```

### Sync (experimental)
```
POST /experimental/sync/start
POST /experimental/sync/steal
POST /experimental/sync/replay/{sessionID}
GET  /experimental/sync/history/{sessionID}
```

### TUI
```
POST /tui/submit
POST /tui/append
POST /tui/clear
POST /tui/command
POST /tui/toast
POST /tui/session
POST /tui/sessions
POST /tui/models
POST /tui/themes
POST /tui/help
POST /tui/publish
POST /tui/control/response
POST /tui/control/next/{sessionID}
```

## Style Guide

- Keep everything in one function unless composable or reusable
- Do not extract single-use helpers preemptively
- Avoid try/except where possible
- Prefer httpx over urllib/requests
- Method naming: snake_case, matching API category prefixes when appropriate
- Type hints everywhere (Python 3.10+)
- Avoid `Any` where possible

## Upstream Monitoring

- Weekly check: compare local `openapi.json` with upstream
- If paths or models changed, update `_client.py` accordingly
- Version bumps: if API breaks → major, adds → minor

## Commit Convention

Same as upstream: `type(scope): summary`

Valid types: feat, fix, docs, chore, refactor, test

Package scope: always include in commit messages.
