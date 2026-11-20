# Opencode Python SDK

<p align="center">
  <a href="https://pypi.org/project/opencode-py/"><img src="https://img.shields.io/pypi/v/opencode-py" alt="PyPI version"></a>
  <a href="https://pypi.org/project/opencode-py/"><img src="https://img.shields.io/pypi/pyversions/opencode-py" alt="Python versions"></a>
  <a href="https://github.com/skislyakow/opencode-py/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/opencode-py" alt="License"></a>
  <a href="https://pypi.org/project/opencode-py/"><img src="https://img.shields.io/pypi/dm/opencode-py" alt="Downloads"></a>
  <a href="https://github.com/skislyakow/opencode-py/actions/workflows/test.yml"><img src="https://github.com/skislyakow/opencode-py/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <img src="https://img.shields.io/badge/build-hatchling-4051b5" alt="Hatchling">
  <img src="https://img.shields.io/badge/http-httpx-blue" alt="httpx">
  <img src="https://img.shields.io/badge/models-pydantic-E92063" alt="pydantic">
</p>

Python SDK for [Opencode](https://opencode.ai) — the open source AI coding agent.

```bash
pip install opencode-py
```

**Do I need Opencode pre-installed?** No. The SDK automatically downloads the
`opencode` binary for your OS (Windows/macOS/Linux, x64/arm64) on first use to
`~/.opencode/bin/`. The binary is only used internally by the SDK — it is NOT
added to PATH, NOT registered system-wide, and NOT shown in the Start Menu.

**What if I install the official Opencode later?** If you install Opencode
via `npm install -g opencode-ai` or another method, the SDK will use the
PATH version instead — no conflict.

*See [Binary management](#binary-management) for details.*

## CLI

After installation, the `opencode-py` command is available **system-wide** from any directory:

```bash
opencode-py "What is the capital of France?"   # one-shot prompt
echo "What is the capital of France?" | opencode-py  # via pipe
opencode-py --help                              # show all options
```

All CLI flags:

| Flag | Description |
|------|-------------|
| `prompt` (positional) | Prompt text or read from stdin |
| `--model` / `-m` | Model name (e.g. `opencode/big-pickle`) |
| `--keep` / `-k` | Keep session alive between calls |
| `--auto-tools` | Enable agentic tool execution |
| `--directory` / `-d` | Working directory |
| `--port` / `-p` | Server port (default: auto — first free port) |

You can also use `python -m opencode`:

```bash
python -m opencode "Explain dependency injection"
python -m opencode --model "opencode/big-pickle" "Hello"
```

## Client library reference

### One-shot (spawns server, asks, cleans up)

```python
from opencode import opencode

answer = opencode("What is the capital of France?")
print(answer)
```

### Context manager (recommended)

```python
from opencode import Opencode

with Opencode() as ai:
    answer = ai.ask("Explain dependency injection")
    print(answer)
```

### Streaming

```python
with Opencode() as ai:
    for chunk in ai.ask_stream("Write a Python function"):
        print(chunk, end="")
```

`ask_stream()` subscribes to the server's SSE endpoint (`GET /api/event`), sends
the prompt, and yields each `session.text.delta` chunk as it arrives. Reasoning
is not yielded.

When called with `collect=True`, `ask_stream()` returns a `StreamResult`
wrapper (or `AsyncStreamResult` for async) that exposes `.events` and `.text`
after iteration:

```python
with Opencode() as ai:
    stream = ai.ask_stream("Write a function", collect=True)
    for chunk in stream:
        print(chunk, end="")
    # After consumption:
    print(stream.text)     # full response text
    print(stream.events)   # all raw SSE events
```

`Session.prompt()` also uses the event stream internally — it sends
`POST /api/session/{id}/prompt`, follows `/api/event` until the run ends
(`session.execution.succeeded` / `interrupted`, or raises on `failed`), then
reads the reply from `GET /api/session/{id}/context`.

#### Response with raw events (`collect`)

All high-level methods accept `collect=True` to return an `OpendcodeResponse`
dataclass containing both the response text and all raw SSE events:

```python
from opencode import opencode

# Get text + raw events
response = opencode("Hello", collect=True)
print(response.text)       # "Hello! How can I help you?"
print(response.events)     # all SSE events received during the prompt
```

```python
from opencode import Opencode

with Opencode() as ai:
    session = ai.create_session()
    result = session.prompt("Say hi", collect=True)
    print(result.text)      # "Hi!"
    print(result.events)    # [StreamEvent, ...] — full event log
```

Works with: `Session.prompt()`, `Session.ask()`, `Opencode.ask()`,
`opencode()`, `async_opencode()`, `ask_stream(collect=True)`, and their
async counterparts.

#### Typed stream events

For advanced use, the SDK exposes the full SSE event stream as typed Pydantic
models via `parse_stream_event()`:

```python
from opencode._stream_events import SessionTextDeltaProps, parse_stream_event

with Opencode() as ai:
    session = ai.create_session()
    stream = ai.client.event_subscribe()        # raw SSE stream (GET /api/event)
    ai.client.session_prompt(session.id, "Hi")  # non-blocking

    for line in stream.iter_lines():
        if not line.startswith("data:"):
            continue
        event = parse_stream_event(line[5:].strip())
        if event.session_id != session.id:     # skip other sessions
            continue
        if event.type == "session.text.delta":
            p = SessionTextDeltaProps.model_construct(**event.properties)
            print(p.delta, end="")              # typed access to .delta
        elif event.type in ("session.execution.succeeded", "session.execution.failed"):
            break
    stream.close()
```

Models exist for all ~100 v2 event types (generated from the server's
`/openapi.json`): `session.text.delta`, `session.tool.called`,
`session.execution.succeeded`, `permission.asked`, `form.created`, ...
`StreamEvent.properties` holds the event's `data` object.

Use `parse_typed_event()` for automatic property validation. See
[`live_stream_events.py`](#interactive-dialog) for a complete demo.

### Conversations

```python
with Opencode() as ai:
    session = ai.create_session()
    msg1 = session.prompt("Suggest a project name")
    print(f"AI: {msg1}")
    msg2 = session.prompt("Now write a tagline for it")
    print(f"AI: {msg2}")
```

The session's model is fixed when it is created (`Opencode(model=...)` or
`create_session(model=...)`); `session.prompt(text, model=...)` switches it
first. `wait=False` only queues the prompt and returns the user message.

### Session methods

Every `Session` object provides additional methods:

```python
with Opencode() as ai:
    session = ai.create_session()
    session.prompt("Hello")

    # Get conversation history
    ctx = session.context()        # list of all messages
    msgs = session.messages()      # paginated message list

    # Control
    session.abort()                # interrupt current execution
    session.compact()              # compact conversation
    session.fork()                 # fork into new session
    session.delete()               # delete the session

    # Inspect
    session.info()                 # SessionResponse (model, cost, tokens, ...)
    session.diff()                 # file changes made by AI
```

Reverting is available on the client: `session_revert_stage()`,
`session_revert_commit()`, `session_revert_clear()`.

### Multi-turn (keep mode)

Reuses server and session across calls:

```python
from opencode import opencode

r1 = opencode("My name is Alice", keep=True)
r2 = opencode("What's my name?", keep=True)   # remembers conversation
r3 = opencode("That's all", keep=False)        # closes server

# Also accepts: model, port, directory, config, agent
```

### Tools and permissions

Tools (`shell`, `write`, `edit`, `read`, ...) run **on the opencode server**.
When the server's permission rules say `ask`, it emits `permission.asked`;
`Session.prompt()` answers it with the given `tool_executor`, and rejects it
when there is none. A rejected permission ends the run.

```python
r = opencode("Create a file called hello.txt", auto_tools=True)
```

`auto_tools=True` (and `Session.ask()`) use a default `ToolExecutor`, which
asks in the console before `shell`/`bash` and allows everything else.

```python
from opencode import Opencode, ToolExecutor

with Opencode() as ai:
    session = ai.create_session(
        # optional: make the server ask before every shell command
        permissions=[{"action": "shell", "resource": "*", "effect": "ask"}],
    )
    msg = session.ask(
        "Write test.py with print('hello') and run it",
        tool_executor=ToolExecutor(permissions={"shell": "allow"}),
        quiet=True,                            # suppress tool logs
    )
```

### Low-level client (any endpoint)

```python
with Opencode() as ai:
    content = ai.client.fs_read("src/main.py")
    diff = ai.client.vcs_diff()
    models = ai.client.model_list()
    session = ai.client.session_create(model="opencode/big-pickle")
    ai.client.session_prompt(session.id, "Hello")   # non-blocking
    ai.client.session_wait(session.id)              # block until idle
    messages = ai.client.session_context(session.id)
```

All client methods target the opencode v2 API (`/api/*`) and return typed
Pydantic models — IDE autocomplete, `.model_dump()`, `.model_dump_json()`.
The `{"data": ...}` envelope is unwrapped; paginated lists
(`session_list()`, `session_messages()`) return a `PageResponse` with `.data`
and `.cursor`. The client's `directory` is sent as `location[directory]`.

#### Connecting to an existing server

Skip subprocess management by pointing at a running `opencode serve`. The v2
server requires HTTP Basic auth (user `opencode`); pass the server password or
set `OPENCODE_SERVER_PASSWORD`:

```python
from opencode import OpencodeClient

client = OpencodeClient(base_url="http://127.0.0.1:4096", password="...", directory=".")
info = client.health()   # GET /api/info -> ServerInfoResponse
```

```python
from opencode import AsyncOpendcodeClient

async with AsyncOpendcodeClient(base_url="http://127.0.0.1:4096", password="...") as client:
    info = await client.health()
```

`create_opencode_server()` generates a random password and exposes it as
`server.password`:

```python
from opencode import OpencodeClient, create_opencode_server

server = create_opencode_server()
client = OpencodeClient(base_url=server.url, password=server.password)
```

#### Cloning a client

```python
client2 = client.copy(base_url="http://other:4096", timeout=60.0)

# Or via with_options:
faster = client.with_options(timeout=10.0, max_retries=0)
```

#### Raw HTTP response

Wraps any client method to also return the raw `httpx.Response`:

```python
from opencode import RawResponse

with client.with_raw_response:
    raw: RawResponse = client.health()

raw.status_code              # 200
raw.headers                  # httpx.Headers
raw.content                  # bytes
raw.parsed                   # ServerInfoResponse (typed model)
raw.response                 # httpx.Response (full)
```

The context manager resets automatically after one call. Works with every
client method (sync and async). See `live_raw.py` for a full demo.

### Retry & error handling

Typed exception hierarchy. All errors are importable from `opencode`:

```python
from opencode import OpencodeClient, RateLimitError, InternalServerError

client = OpencodeClient(max_retries=3)  # exponential backoff with jitter

try:
    health = client.health()
    print(health.version)
except RateLimitError:
    print("too many requests — retried but failed")
except InternalServerError:
    print("server error")
```

Full error class hierarchy:

| Class | HTTP status | When raised |
|-------|-------------|-------------|
| `OpencodeError` | — | Base for all SDK errors |
| `APIConnectionError` | — | Network / connection failure |
| `APITimeoutError` | — | Request timed out |
| `APIResponseValidationError` | — | Response doesn't match schema |
| `APIStatusError` | 4xx/5xx | Base for HTTP error responses |
| `BadRequestError` | 400 | Malformed request |
| `AuthenticationError` | 401 | Missing or wrong server password |
| `PermissionDeniedError` | 403 | Access denied |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Resource conflict |
| `UnprocessableEntityError` | 422 | Validation error in request body |
| `RateLimitError` | 429 | Rate limit exceeded |
| `InternalServerError` | 500+ | Server-side error |
| `BinaryNotFoundError` | — | `opencode` binary not on PATH |
| `ServerStartupTimeoutError` | — | Server didn't start in time |

Retry policy: 408, 409, 429, 5xx and timeouts are retried with exponential
backoff + jitter. `Retry-After` and `retry-after-ms` headers are respected.

### Structured output

Not supported by the opencode v2 API — passing `format=` raises
`OpencodeError`.

### Debug logging

```bash
# Linux / macOS (bash/zsh)
OPENCODE_LOG=debug python my_script.py

# Windows (PowerShell)
$env:OPENCODE_LOG="debug"; python my_script.py

# Windows (cmd)
set OPENCODE_LOG=debug && python my_script.py
```

Shows all HTTP requests/responses with timing.

### Web UI (zero dependencies)

```bash
python web/server.py
# → open http://127.0.0.1:3000
```

Built-in HTTP server + proxy to `opencode serve` — no extra dependencies.

> **Note**: the web UI has not been ported to the opencode v2 API yet.

### Interactive dialog

```bash
python live.py            # sync multi-turn dialog
python live_async.py      # async multi-turn dialog
python live_streaming.py  # streaming dialog (reuse session)
python live_raw.py        # with_raw_response demo (7 scenarios)
python live_stream_events.py "Your prompt"  # typed SSE event inspection
python demo.py            # quick tour of the v2 API
python test_live.py       # live check of 36 non-LLM endpoints
```

All scripts clean up the server on exit via `atexit`.

### ToolExecutor reference

```python
from opencode import ToolExecutor

# Keyed by the permission action the server asks about.
# Default: shell/bash -> "ask" (console prompt), everything else -> "allow".
executor = ToolExecutor(
    permissions={
        "shell": "allow",     # always allow
        "edit": "deny",       # always reject
        "read": "ask",        # call confirm()
    },
    confirm=lambda action, request: "rm" not in " ".join(request["resources"]),
)

session.ask("Create a project", tool_executor=executor)
executor.decide({"action": "edit"})   # -> "reject"
```

### Binary management

When `opencode` is not on PATH, the SDK auto-downloads it to
`~/.opencode/bin/opencode`.

Resolution order:
1. `PATH` — `shutil.which("opencode")`
2. `~/.opencode/bin/opencode` — previously downloaded copy
3. GitHub releases — download for current platform

Supported platforms: `win32-x64`, `win32-arm64`, `darwin-x64`, `darwin-arm64`,
`linux-x64`, `linux-arm64`.

Override the binary path directly:

```python
with Opencode(opencode_binary="/custom/path/opencode") as ai:
    ...
```

### OpencodeServer (low-level server control)

```python
from opencode import OpencodeServer, create_opencode_server

server = create_opencode_server(
    port=4096,
    hostname="127.0.0.1",
    timeout=30.0,
    config={"model": "opencode/big-pickle"},
    opencode_binary="/path/to/opencode",
)
print(server.url)  # "http://127.0.0.1:4096"

# Later:
server.close()  # kills the subprocess
```

## Configuration reference

All parameters for `Opendcode()` / `AsyncOpendcode()`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model` | `None` | Model name, e.g. `"opencode/big-pickle"` or `"provider/model"` |
| `hostname` | `"127.0.0.1"` | Bind address for the server |
| `port` | `None` (auto) | Port for the server; `None` picks first free port |
| `directory` | `None` | Working directory (session `location` and `location[directory]` on all API calls) |
| `server_timeout` | `30.0` | Seconds to wait for server startup |
| `client_timeout` | `300.0` | Seconds before HTTP request timeout |
| `config` | `None` | Server config dict (see opencode docs) |
| `opencode_binary` | `None` | Path to opencode binary (auto-downloaded if not set) |

All parameters are keyword-only.

## Async API

### Basic

```python
import asyncio
from opencode import AsyncOpendcode

async def main():
    async with AsyncOpendcode() as ai:
        answer = await ai.ask("Explain async/await in Python")
        print(answer)

asyncio.run(main())
```

### Async streaming

```python
async with AsyncOpendcode() as ai:
    session = await ai.create_session()   # async ask_stream needs a session
    async for chunk in ai.ask_stream("Write a poem", session=session):
        print(chunk, end="")
```

Async streaming also supports `collect`:

```python
async with AsyncOpendcode() as ai:
    session = await ai.create_session()
    stream = ai.ask_stream("Write a poem", session=session, collect=True)
    async for chunk in stream:
        print(chunk, end="")
    print(stream.events)  # raw SSE events
    print(stream.text)    # full response text
```

### Async conversations

```python
async with AsyncOpendcode() as ai:
    session = await ai.create_session()
    msg1 = await session.prompt("Suggest a project name")
    msg2 = await session.prompt("Now write a tagline for it")
```

### Async low-level client

```python
from opencode import AsyncOpendcodeClient

async with AsyncOpendcodeClient() as client:
    health = await client.health()
    print(health.version)  # typed Pydantic model
```

### Async convenience function

```python
from opencode import async_opencode

result = await async_opencode("Hello", keep=True)
result2 = await async_opencode("Still there?", keep=True)
result3 = await async_opencode("Bye")

# Also accepts: model, port, directory, config, agent, auto_tools
```

## Key types

### OpencodeResponse

```python
from opencode import OpencodeResponse

response = session.prompt("Hello", collect=True)
# response.text    -> str              (extracted response text)
# response.events  -> list[StreamEvent]  (raw SSE events)
```

Returned by `Session.prompt()`, `Session.ask()`, `Opencode.ask()`,
`opencode()`, `async_opencode()`, and their async counterparts when
`collect=True`.

### StreamResult / AsyncStreamResult

```python
from opencode import StreamResult, AsyncStreamResult

stream = ai.ask_stream("Hello", collect=True)
# for chunk in stream:    — iterate text chunks
# stream.events           -> list[StreamEvent]  (after iteration)
# stream.text             -> str                (full response text)
```

`StreamResult` (sync) and `AsyncStreamResult` (async) wrap the
`ask_stream(collect=True)` iteration, collecting all SSE events for
later inspection.

### Pydantic response models

```python
from opencode._response_models import ServerInfoResponse, SessionResponse, PageResponse

# Generated from the server's /openapi.json; all fields optional, extras kept.
# These are Pydantic BaseModel classes with:
#   .model_dump() -> dict
#   .model_dump_json() -> str
#   .model_validate(dict) -> classmethod
```

## Development

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint & typecheck
ruff check src/
mypy src/

# Build
python -m build --wheel
```
