# Opencode Python SDK — AGENTS.md

## Project Overview

Python SDK for [Opencode](https://opencode.ai) — a PyPI package (`opencode-py`) that launches an `opencode serve` subprocess and provides both high-level and low-level APIs.

**Current version**: 0.2.0-dev
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
ad54a39 feat(web): add zero-dependency web UI with proxy server
b8d205f feat(sdk): add auto_tools mode with ToolExecutor and permissions
2fd170c docs: update AGENTS.md with keep mode and live.py
67ae119 feat(sdk): add keep parameter for multi-turn conversations
514b0a2 fix(session): use V1 sync prompt with model support instead of V2
4323247 fix: resolve npm .cmd wrappers to real .exe binary on Windows
fb4b884 feat: initial Python SDK for Opencode
```

### What works
- Server starts/stops via subprocess (`opencode serve`)
- Binary auto-detection: PATH -> `~/.opencode/bin/` -> GitHub download
- Full REST API coverage (V1 + V2):
  - Global, config, sessions, files, VCS, find, MCP, auth, providers, models, LSP, formatter, tools, permissions, questions, PTY, worktree, workspace, sync, TUI
- Session prompt via V1 sync API (V2 `v2_session_wait` is broken, replaced with V1 `POST /session/:id/message`)
- `Opencode(config={"model": "opencode/big-pickle"}).ask("...")` — works end-to-end with free model
- `opencode(prompt, keep=True)` — multi-turn conversation in same session
- `opencode(prompt, auto_tools=True)` — agentic tool execution (bash, write, edit, read, glob, grep) with permission system
- `async_opencode(prompt, keep=True)` — async version of `opencode()`
- Structured output — `format={"type": "json_schema", "schema": {...}}` on `ask()` / `prompt()` / `opencode()`
- Async full support — `AsyncOpendcode`, `AsyncOpendcodeClient`, `AsyncSession`
- Streaming — `ask_stream()` (sync + async) via `/event` SSE, works with `big-pickle` (non-streaming model) and streaming models
- `scripts/check-upstream.py` — fetches upstream openapi.json, flags needed changes
- 38/38 live endpoints tested against opencode v1.17.13
- 31/31 unit tests passing (sync + async)
- Python 3.10 compatibility (`NotRequired` via `typing_extensions`)
- `live.py` (sync), `live_async.py`, `live_streaming.py` — interactive dialog scripts with `atexit` cleanup
- **Pydantic response models** — `HealthResponse`, `SessionResponse`, `FileContentResponse`, `ProviderResponse`, `V1SessionResponse` and more
- **Retry logic** — exponential backoff with jitter, retries on 408/409/429/5xx and timeouts
- **Typed error hierarchy** — `APIStatusError` → `BadRequestError`, `RateLimitError`, `InternalServerError`, etc.
- **Logging** — `OPENCODE_LOG=debug` enables httpx debug logging
- **`py.typed` marker** — PEP 561 compliance for type checkers
- **`copy()`/`with_options()`** — immutable client cloning with overrides

### Known issues to fix

1. **Delivery enum mismatch** — npm v1.17.13 uses `"steer"/"queue"`, but upstream `dev` branch source also uses `"steer"/"queue"`. The local clone (`C:\Code\opencode`) has been modified to use `"immediate"/"deferred"` but this is NOT yet upstream. When upstream switches, update `_client.py:delivery="queue"` and `_async_client.py` to `"deferred"`. Run `scripts/check-upstream.py` to monitor.

2. ~~**Config format** — `Opencode(config={"model": "anthropic/..."})` fails because config expects `provider.{id}.options.apiKey` format.~~ **FIXED**: `opencode(model=...)` no longer puts model in server config — passes it per-request.

3. **`v2_session_wait` broken** — `POST /api/session/{sessionID}/wait` returns "Session wait is not available yet" in v1.17.13. **FIXED**: `Session.prompt()` now polls `v2_session_context()` until an assistant message appears.

4. ~~**No async support** — `OpencodeClient` is sync-only.~~ **DONE**: Full async support.

5. **Streaming** — `ask_stream()` reads SSE events via `/event` but delta format may differ between server versions.

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

## Next Steps (priority order)

### Step B: Test `ask()` with free model (Big Pickle) ✅ DONE
1. Figure out correct config for free model usage
   - Check `/api/provider` on running server for "big-pickle" or free providers
   - Check if Big Pickle works without any API key/config
2. Test `Session.prompt()` with delivery="queue" + `v2_session_wait()`
3. Test `Opencode().ask()` end-to-end
4. Fix any response parsing issues
5. Add `keep=True` for multi-turn conversations in `opencode()` convenience function
   - Module-level `_opencode_state` for server/session reuse
   - `atexit` cleanup in `live.py`
   - 6 unit tests for `keep` / `_resolve_model`

### Step C: Publish v0.1.0 to PyPI
1. ~~Create `scripts/check-upstream.py` — fetches openapi.json, diffs with local~~ ✅ DONE
2. ~~Create GitHub Actions CI (tests on push)~~ ✅ DONE
3. Publish to TestPyPI first, then PyPI
   - `pip install build twine`
   - `python -m build`
   - `twine upload --repository testpypi dist/*` (check first)
   - `twine upload dist/*`
   - Or: push tag `v0.1.0` → GitHub Actions publishes via Trusted Publishing

### Step D: Async support ✅ DONE
1. `AsyncOpendcodeClient` using `httpx.AsyncClient` ✅
2. `AsyncSession` with `async prompt()` ✅
3. `AsyncOpendcode` with `async def ask()` ✅
4. `async_opencode()` convenience function ✅
5. 11 unit tests for async client ✅

### Step E: Streaming improvements
1. Better SSE parsing in `ask_stream()`
2. Handle `message.part.delta` and `message.updated` events

### Step F: Structured output ✅ DONE
1. `format` parameter on `prompt()` / `ask()` / `opencode()` / `async_opencode()` ✅
2. `_extract_text()` handles `structured` field ✅
3. 3 unit tests ✅

### Step G: Upstream monitoring ✅ DONE
1. `scripts/check-upstream.py` checks delivery enum + structured output ✅

## Next Steps

### Step H: Complete typed model coverage
1. Add `cast_to` to remaining client methods (vcs, config, project, etc.)
2. Add `with_raw_response` pattern for raw HTTP access
3. Consider `model_construct()` for faster deserialization (skip validation)

### Step I: Release v0.2.0
1. Bump version in `pyproject.toml` to `0.2.0`
2. Publish to PyPI via Trusted Publishing

## Release Process

Run `python scripts/check-release.py` to check if a new PyPI release is needed.
The script compares the version in `pyproject.toml` with the latest git tag
and reports unreleased commits.

**Release checklist:**
- [ ] `python scripts/check-release.py -v` — confirms release is due
- [ ] `git log --oneline v0.1.1..HEAD` — review unreleased changes
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
