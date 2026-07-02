# Opencode Python SDK — AGENTS.md

## Project Overview

Python SDK for [Opencode](https://opencode.ai) — a PyPI package (`opencode-ai`) that launches an `opencode serve` subprocess and provides both high-level and low-level APIs.

**Current version**: 0.1.0 (unreleased)
**Python**: >=3.10
**Dependencies**: only `httpx>=0.27.0`
**Build**: hatchling

## Repository

- `C:\Code\opencode-py\` (local)
- GitHub: https://github.com/[user]/opencode-py
- Upstream opencode: https://github.com/anomalyco/opencode
  - OpenAPI spec: `packages/sdk/openapi.json` (committed)
  - Raw URL: `https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/sdk/openapi.json`
  - Local copy of this repo: `C:\Code\opencode\`

## File Structure

```
opencode-py/
├── src/opencode/
│   ├── __init__.py        # Public API exports
│   ├── __main__.py        # python -m opencode "question"
│   ├── _opencode.py       # Opencode class (ask/ask_stream/context manager)
│   ├── _client.py         # OpencodeClient — all REST endpoints (528 lines)
│   ├── _server.py         # OpencodeServer — subprocess lifecycle
│   ├── _session.py        # Session — conversation management
│   ├── _binary.py         # Binary find in PATH + GitHub download
│   ├── _process.py        # Cross-platform process termination
│   ├── _models.py         # TypedDict types for API responses
│   └── _errors.py         # OpencodeError, ApiError, BinaryNotFound
├── tests/
│   └── test_client.py     # 11 unit tests (httpx MockTransport)
├── demo.py                # Live demo (38 endpoint checks)
├── test_live.py           # Live integration test
├── AGENTS.md              # This file
├── README.md
├── pyproject.toml
├── .gitignore
└── docs/
    └── opencode-docs-ru.md # Russian docs from opencode.ai
```

## Current State (commit history)

```
4323247 fix: resolve npm .cmd wrappers to real .exe binary on Windows
fb4b884 feat: initial Python SDK for Opencode
```

### What works
- Server starts/stops via subprocess (`opencode serve`)
- Binary auto-detection: PATH -> `~/.opencode/bin/` -> GitHub download
- Full REST API coverage (V1 + V2):
  - Global, config, sessions, files, VCS, find, MCP, auth, providers, models, LSP, formatter, tools, permissions, questions, PTY, worktree, workspace, sync, TUI
- Session prompt via V2 API with context polling (replaced broken `v2_session_wait`)
- `Opencode(config={"model": "opencode/big-pickle"}).ask("...")` — works end-to-end with free model
- 38/38 live endpoints tested against opencode v1.17.13
- 11/11 unit tests passing
- Python 3.10 compatibility (`NotRequired` via `typing_extensions`)

### Known issues to fix

1. **Delivery enum mismatch** — npm v1.17.13 uses `"steer"/"queue"`, but `dev` branch source uses `"immediate"/"deferred"`. Current code uses `"steer"/"queue"`. When opencode releases a new version, update `_client.py:delivery="queue"` and `_session.py` to use `"immediate"/"deferred"`.

2. ~~**Config format** — `Opencode(config={"model": "anthropic/..."})` fails because config expects `provider.{id}.options.apiKey` format.~~ **RESOLVED**: Free model `opencode/big-pickle` works without any API key. Just pass `config={"model": "opencode/big-pickle"}` to `Opencode()` or use the `opencode()` convenience function. The `opencode` provider has 50 models available including `deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, etc. Default model config (`"model": "opencode/big-pickle"`) is passed via `OPENCODE_CONFIG_CONTENT` env var to the server.

3. **`v2_session_wait` broken** — `POST /api/session/{sessionID}/wait` returns "Session wait is not available yet" in v1.17.13. **FIXED**: `Session.prompt()` now polls `v2_session_context()` until an assistant message appears (see `_session.py:_poll_response`).

4. **No async support** — `OpencodeClient` is sync-only. `httpx.AsyncClient` not wired up.

5. **Streaming** — `ask_stream()` reads SSE events via `/event` but delta format may differ between server versions.

6. **No upstream monitoring** — No script to compare local `openapi.json` with upstream.

## Architecture

### Opencode (high-level, context manager)
```
Opencode.__enter__()
  → OpencodeServer.start()          # subprocess: opencode serve --port=N
  → OpencodeClient(base_url, ...)   # httpx client
  → return self
Opencode.ask(prompt)
  → create_session()
  → Session.prompt(text)
    → v2_session_prompt(delivery="queue")  # send prompt
    → v2_session_context()                  # poll until assistant message
  → _extract_text(message)                  # extract text content
Opencode.__exit__()
  → OpencodeClient.close()
  → OpencodeServer.close()          # taskkill /T /F (win32) or SIGTERM (unix)
```

### OpencodeClient (low-level)
All HTTP methods follow the pattern:
```
_request("GET"|"POST"|"DELETE"|"PATCH", path, params, json_body)
```
with automatic `directory`/`workspace` query param injection via `_merge_params()`.

### Correct API paths (OpenAPI spec)
V2 session operations:
```
POST /api/session/{sessionID}/prompt    — send prompt
POST /api/session/{sessionID}/wait      — wait for idle (204, BROKEN in v1.17.13)
GET  /api/session/{sessionID}/context   — get context messages (used for polling)
GET  /api/session/{sessionID}/message   — list messages (paginated)
POST /api/session/{sessionID}/compact   — compact
GET  /api/session                       — list sessions
```

All other endpoints use V1 paths (see AGENTS.md of the upstream repo or inline comments in `_client.py`).

All other endpoints use V1 paths (see AGENTS.md of the upstream repo or inline comments in `_client.py`).

## Binary Management

```python
# Resolution order:
1. find_in_path() — shutil.which("opencode")
   - On Windows: resolves .cmd wrappers to actual .exe via _resolve_wrapper()
2. find_local()  — ~/.opencode/bin/opencode
3. download_opencode() — GitHub releases
```

**Key Windows fix**: `shutil.which("opencode")` returns `opencode.cmd` (npm wrapper). `_resolve_wrapper()` reads the .cmd file and extracts the `.exe` path from the line `"%dp0%\node_modules\opencode-ai\bin\opencode.exe"`.

Platform detection for download:
- `win32-x64`, `win32-arm64`, `darwin-x64`, `darwin-arm64`, `linux-x64`, `linux-arm64`

## Testing

```bash
# Install
pip install -e ".[dev]"

# Unit tests (no server needed)
pytest tests/ -v

# Live test (requires opencode in PATH or npm global install)
python test_live.py

# Demo
python demo.py
```

## Next Steps (priority order)

### Step B: Test `ask()` with free model (Big Pickle) ✅ DONE
1. Figure out correct config for free model usage
   - Check `/api/provider` on running server for "big-pickle" or free providers
   - Check if Big Pickle works without any API key/config
2. Test `Session.prompt()` with delivery="queue" + `v2_session_wait()`
3. Test `Opencode().ask()` end-to-end
4. Fix any response parsing issues

### Step C: Publish v0.1.0 to PyPI
1. Create `scripts/check-upstream.py` — fetches openapi.json, diffs with local
2. Create GitHub Actions CI (tests on push)
3. Publish to TestPyPI first, then PyPI

### Step D: Async support
1. `AsyncOpendcodeClient` using `httpx.AsyncClient`
2. `AsyncSession` with `async prompt()`
3. `AsyncOpendcode` with `async def ask()`
4. `async with Opencode() as ai: answer = await ai.ask("...")`

### Step E: Streaming improvements
1. Better SSE parsing in `ask_stream()`
2. Handle `message.part.delta` and `message.updated` events

## Style Guide

- Keep in one function unless composable/reusable
- No single-use helpers preemptively
- Avoid try/except where possible
- Prefer httpx over urllib/requests (HTTP client), except for `_binary.py` which uses `urllib.request` for download (stdlib, no extra deps)
- Method naming: snake_case, category prefix (e.g., `v2_session_*`, `file_*`, `config_*`)
- Type hints everywhere
- Avoid `Any` where possible — use `TypedDict` from `_models.py`

## Commit Convention

```
type(scope): summary
```

Types: feat, fix, docs, chore, refactor, test
Always include package scope.

Examples:
```
feat(server): add async context manager support
fix(binary): resolve npm .cmd wrappers to real .exe on Windows
refactor(client): extract error handling to _handle()
```

## Quick Reference for New Agent

```
# Setup
git clone <repo>  # or cd C:\Code\opencode-py
pip install -e ".[dev]"

# Check opencode availability
opencode serve --help           # should work
python -c "from opencode._binary import ensure_opencode; print(ensure_opencode())"

# Run live test
python test_live.py

# Run demo
python demo.py

# Try a simple interactive test
python -c "
from opencode import OpencodeClient, create_opencode_server
s = create_opencode_server(port=4097)
c = OpencodeClient(base_url=s.url)
print('Health:', c.health())
c.close()
s.close()
"
```
