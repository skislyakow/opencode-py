# Opencode Python SDK — AGENTS.md

## Project Overview

Python SDK for [Opencode](https://opencode.ai) — a PyPI package (`opencode-py`) that launches an `opencode serve` subprocess and provides both high-level and low-level APIs.

**Current version**: 0.7.0
**Python**: >=3.10
**Dependencies**: `httpx>=0.27.0`, `pydantic>=2.0.0`, `typing-extensions>=4.6.0`
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
│   ├── __init__.py            # Public API exports, calls setup_logging()
│   ├── __main__.py            # python -m opencode "question"
│   ├── _opencode.py           # Opencode class + opencode() convenience fn
│   ├── _async_opencode.py     # AsyncOpendcode class + async_opencode()
│   ├── _client.py             # OpencodeClient — sync REST (typed models, retry)
│   ├── _async_client.py       # AsyncOpendcodeClient — async REST (typed models, retry)
│   ├── _server.py             # OpencodeServer — subprocess lifecycle
│   ├── _session.py            # Session — sync conversation management
│   ├── _async_session.py      # AsyncSession — async conversation management
│   ├── _binary.py             # Binary find in PATH + GitHub download
│   ├── _process.py            # Cross-platform process termination
│   ├── _models.py             # TypedDict types (SessionMessage, etc.)
│   ├── _response_models.py    # Pydantic BaseModel response types (all endpoints)
│   ├── _types.py              # NotGiven sentinel
│   ├── _logs.py               # Logging via OPENCODE_LOG env var
│   ├── _stream_events.py       # Typed Pydantic models for all SSE events (~75 types)
│   ├── _tools.py              # ToolExecutor — run tools locally with permissions
│   ├── _errors.py             # Typed exception hierarchy (10+ classes)
│   └── py.typed               # PEP 561 marker for type checkers
├── tests/
│   ├── test_client.py         # 11 unit tests (sync, httpx MockTransport)
│   ├── test_async_client.py   # 11 unit tests (async, httpx MockTransport)
│   └── test_opencode.py       # 9 tests (resolve_model, keep, structured, format)
├── scripts/
│   └── check-upstream.py      # Compare openapi.json with upstream GitHub
├── demo.py                    # Live demo (38 endpoint checks)
├── live.py                    # Interactive multi-turn dialog (sync)
├── live_async.py              # Interactive multi-turn dialog (async)
├── live_streaming.py          # Streaming interactive dialog
├── test_live.py               # Live integration test
├── web/
│   ├── server.py              # Start opencode + proxy for web UI
│   └── index.html             # Chat interface (vanilla JS)
├── AGENTS.md                  # This file
├── README.md
├── README.ru.md
├── pyproject.toml
├── .gitignore
└── docs/
    └── opencode-docs-ru.md    # Russian docs from opencode.ai
```

## Current State (commit history)

```
44d23f0 feat(session): V2 session prompt via SSE subscription
491c3d4 feat(opencode): add OpencodeResponse dataclass with collect param
e14ea7b docs: update AGENTS.md for v0.6.0 and Task 2 completion
014fe7f feat(server): ephemeral port selection — auto-pick free port when port=None
685a77c chore(release): bump to v0.5.1
56d3522 feat(client): add session_delete_message endpoint
20ca9a7 fix(client): replace type: ignore with cast for RawResponse return
```

### What works
- Server starts/stops via subprocess (`opencode serve`)
- Binary auto-detection: PATH -> `~/.opencode/bin/` -> GitHub download
- Full REST API coverage (V1 + V2):
  - Global, config, sessions, files, VCS, find, MCP, auth, providers, models, LSP, formatter, tools, permissions, questions, PTY, worktree, workspace, sync, TUI
- Session prompt via V2 SSE subscription (`POST /api/session/{id}/prompt` + `/event`), falls back to V1 blocking prompt when model/format is specified
- `Opencode(config={"model": "opencode/big-pickle"}).ask("...")` — works end-to-end with free model
- `opencode(prompt, keep=True)` — multi-turn conversation in same session
- `opencode(prompt, auto_tools=True)` — agentic tool execution (bash, write, edit, read, glob, grep) with permission system
- `async_opencode(prompt, keep=True)` — async version of `opencode()`
- Structured output — `format={"type": "json_schema", "schema": {...}}` on `ask()` / `prompt()` / `opencode()`
- Async full support — `AsyncOpendcode`, `AsyncOpendcodeClient`, `AsyncSession`
- Streaming — `ask_stream()` (sync + async) via `/event` SSE, typed event models (`_stream_events.py` ~75 types), `collect=True` via `StreamResult`/`AsyncStreamResult`
- V2 session prompt via SSE — `Session.prompt()` uses `POST /api/session/{id}/prompt` + `/event` SSE subscription with V1 fallback
- Ephemeral port — auto-picks free port when `port=None` (default)
- `session_delete_message()` — `DELETE /session/{sessionID}/message/{messageID}` with `Session.delete_message()` convenience method
- `scripts/check-upstream.py` — fetches upstream openapi.json, flags needed changes
- `OpendcodeResponse` dataclass with `collect=True` — returns `text` + raw events from all high-level APIs
- `collect` param on `Session.prompt()`, `Session.ask()`, `AsyncSession.prompt()`, `AsyncSession.ask()`, `opencode()`, `async_opencode()`
- `StreamResult` / `AsyncStreamResult` — `ask_stream(collect=True)` returns iterable wrapper with `.events` and `.text`
- 38/38 live endpoints tested against opencode v1.17.13
- 61/61 unit tests passing (sync + async)
- `StreamResult` / `AsyncStreamResult` — wrappers for `ask_stream(collect=True)` exposing `.events` and `.text`
- Python 3.10 compatibility (`NotRequired` via `typing_extensions`)
- `live.py`, `live_async.py`, `live_streaming.py`, `live_raw.py`, `live_stream_events.py` — interactive dialog scripts with `atexit` cleanup
- **Pydantic response models** — `HealthResponse`, `SessionResponse`, `FileContentResponse`, `ProviderResponse`, `V1SessionResponse` and more
- **Retry logic** — exponential backoff with jitter, retries on 408/409/429/5xx and timeouts
- **Typed error hierarchy** — `APIStatusError` → `BadRequestError`, `RateLimitError`, `InternalServerError`, etc.
- **Logging** — `OPENCODE_LOG=debug` enables httpx debug logging
- **`py.typed` marker** — PEP 561 compliance for type checkers
- **`copy()`/`with_options()`** — immutable client cloning with overrides

### Known issues to fix

1. **Delivery enum mismatch** — npm v1.17.13 uses `"steer"/"queue"`, but upstream `dev` branch source also uses `"steer"/"queue"`. The local clone (`C:\Code\opencode`) has been modified to use `"immediate"/"deferred"` but this is NOT yet upstream. When upstream switches, update `_client.py:delivery="queue"` and `_async_client.py` to `"deferred"`. Run `scripts/check-upstream.py` to monitor.

2. ~~**Config format** — `Opencode(config={"model": "anthropic/..."})` fails because config expects `provider.{id}.options.apiKey` format.~~ **FIXED**: `opencode(model=...)` no longer puts model in server config — passes it per-request.

3. **`v2_session_wait` broken** — `POST /api/session/{sessionID}/wait` returns "Session wait is not available yet" in v1.17.13. **FIXED**: `Session.prompt()` now uses V2 prompt + `/event` SSE subscription, waits for `session.next.step.ended` event. Old fix (polling `v2_session_context()`) replaced.

4. ~~**No async support** — `OpencodeClient` is sync-only.~~ **DONE**: Full async support.

5. **Streaming delta format** — `ask_stream()` reads SSE events via `/event` but delta format may differ between server versions. Current implementation tested against opencode v1.17.13.

6. ~~**No upstream monitoring**~~ **DONE**: `scripts/check-upstream.py` fetches upstream.

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

### opencode() — convenience function with keep
```
_opencode_state = {"ai": ..., "session": ..., "config": ...}
opencode(prompt, keep=True)
  → reuse existing session.prompt(prompt)
  → return _extract_text(msg)            # server stays alive
opencode(prompt)            # keep=False by default
  → Opencode.__enter__()
  → create_session().prompt(prompt)
  → _extract_text(msg)
  → Opencode.__exit__()                  # server closed
```
When `keep=True`, state is reused across calls (same session, same server).
Warns if different config/model passed. Clean up with `atexit` in scripts.

### async_opencode() — async convenience function
Identical to `opencode()` but uses `AsyncOpendcode` and `await`.
Module-level `_async_opencode_state` for server/session reuse.
```python
r1 = await async_opencode("hello", keep=True)
r2 = await async_opencode("what's my name?", keep=True)
r3 = await async_opencode("bye")
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

### Tool Execution
```
Session.ask(text, tool_executor=ToolExecutor())
  → send user message (POST /session/:id/message)
  → if tool-use parts: execute via ToolExecutor, send results, loop
  → if no tool-use and not confirmed: auto-confirm "Exit plan mode"
  → if no tool-use and confirmed: return text

ToolExecutor:
  - permissions: allow/ask/deny per tool
  - default: bash=ask, others=allow
  - tools: bash, write, edit, read, glob, grep
```

### Structured Output
```
prompt() / ask() / opencode() / async_opencode()
  accept: format={"type": "json_schema", "schema": {...}, "retryCount": 2}
  → body["format"] = format  (passed to V1 POST /session/:id/message)
  → server injects StructuredOutput tool with toolChoice: "required"
  → response may include "structured" field with parsed JSON
  → _extract_text() returns JSON string when structured present

Schema: opencode/big-pickle (DeepSeek) does NOT support tool_choice="required"
        Need Claude/GPT-4 with API key.
```

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

# Check upstream openapi for changes
python scripts/check-upstream.py

# Live test (requires opencode in PATH or npm global install)
python test_live.py

# Demo
python demo.py

# Interactive dialog
python live.py          # sync
python live_async.py    # async
python live_streaming.py

# Web UI (zero deps, opens browser)
python web/server.py
```

## Release Process

Run `python scripts/check-release.py` to check if a new PyPI release is needed.
The script compares the version in `pyproject.toml` with the latest git tag
and reports unreleased commits.

**Release checklist:**
- [ ] `python scripts/check-release.py -v` — confirms release is due
- [ ] `git log --oneline v0.2.0..HEAD` — review unreleased changes
- [ ] Version bumped in `pyproject.toml`
- [ ] CI green on master
- [ ] `python -m build && twine check dist/*` — wheel is valid

**Proactive behavior**: 
- At the start of each session, I will run `python scripts/check-release.py`
  automatically and alert you if a release is due (commits since last tag
  without version bump).
- **Before every commit**, I will check if the staged changes include anything
  "user-facing" (feat, fix, refactor, or dependency changes — anything beyond
  chore/docs/style). If there has been no version bump since the last tagged
  release, I will warn you and ask whether to bump the version before
  committing.

### Step J: Compare with official SDK
1. Evaluate `opencode-ai` (official Stainless SDK) for low-level layer
2. Consider using their client as base with our high-level wrapper

## Style Guide

- Keep in one function unless composable/reusable
- No single-use helpers preemptively
- Avoid try/except where possible
- Prefer httpx over urllib/requests (HTTP client), except for `_binary.py` which uses `urllib.request` for download (stdlib, no extra deps)
- Method naming: snake_case, category prefix (e.g., `v2_session_*`, `file_*`, `config_*`)
- Type hints everywhere
- Avoid `Any` where possible — use Pydantic models from `_response_models.py`

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

## Borrow from opencode-runtime — plan

### Task 1: Ephemeral port selection ✅
- [x] `port=None` → auto-pick free port via `socket.bind(("", 0))`
- [x] Explicit port still works (backward compat)
- [x] README updated

### Task 2: Response dataclass with raw events ✅
- [x] Add `OpencodeResponse` dataclass: `text: str`, `events: list[Any]`
- [x] `ask_stream()` collect via `StreamResult`/`AsyncStreamResult`
- [x] Add `collect=True/False` param
- [x] `Session.prompt()` can optionally return `OpencodeResponse` instead of bare string
- [x] Tests for event collection

### Task 3: V2 session prompt via SSE (replace V1 polling) ✅
- [x] Audit `/global/event` SSE endpoint reliability in current opencode server
- [x] If reliable: rework `Session.prompt()` to use `POST /api/session/{id}/prompt` + `/event` subscription
- [x] Keep V1 as fallback (when model/format specified or SSE fails)
- [ ] Benchmark: polling vs SSE latency difference (pending)

### Not planned
- Multi-tenant pool, HOME isolation, registry, materials CLI fleet management — overkill for single-user SDK

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
s = create_opencode_server()  # auto-port
c = OpencodeClient(base_url=s.url)
print('Health:', c.health())
c.close()
s.close()
"
```

## Future ideas

### TUI application (opencode-py[tui])

A full-featured TUI chat client using [Textual](https://textual.textualize.io/), powered entirely by `opencode-py` as backend — no Node.js required:

- Chat input/output, SSE streaming, tool execution, file changes view
- Modal permission dialogs instead of console prompts
- Optional dependency: `pip install opencode-py[tui]`
- Separate project that consumes `opencode-py` as a library

Prerequisites: Task 3 (V2 SSE prompt).
