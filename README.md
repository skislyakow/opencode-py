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
| `--port` / `-p` | Server port (default: 4096) |

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

### Conversations

```python
with Opencode() as ai:
    session = ai.create_session()
    msg1 = session.prompt("Suggest a project name")
    print(f"AI: {msg1}")
    msg2 = session.prompt("Now write a tagline for it")
    print(f"AI: {msg2}")
```

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
    session.abort()                # abort current generation
    session.compact()              # compact conversation
    session.fork()                 # fork into new session

    # Inspect
    session.diff()                 # file changes made by AI
    session.todo()                 # remaining TODOs
```

### Multi-turn (keep mode)

Reuses server and session across calls:

```python
from opencode import opencode

r1 = opencode("My name is Alice", keep=True)
r2 = opencode("What's my name?", keep=True)   # remembers conversation
r3 = opencode("That's all", keep=False)        # closes server

# Also accepts: model, format, port, directory, config, agent
```

### Auto-tools (agentic tool execution)

```python
r = opencode("Create a file called hello.txt", auto_tools=True)
```

Available tools: `bash`, `write`, `edit`, `read`, `glob`, `grep`.

By default `bash` asks for permission in the console, all others run without prompting.

Custom permissions via `Session.ask()`:

```python
from opencode import Opencode, ToolExecutor

with Opencode() as ai:
    session = ai.create_session()
    msg = session.ask(
        "Write test.py with print('hello')",
        tool_executor=ToolExecutor(
            permissions={"write": "allow"},
            workdir="/path/to/sandbox",      # restrict file operations
        ),
        max_tool_rounds=25,                    # safety limit
        quiet=True,                            # suppress tool logs
    )
```

The first AI response in `ask()` enters plan mode — the SDK auto-confirms with
`"Exit plan mode and proceed"` to make the model execute tools immediately.

### Low-level client (any endpoint)

```python
with Opencode() as ai:
    content = ai.client.file_read("src/main.py")
    diff = ai.client.vcs_diff("HEAD~3")
    config = ai.client.config_get()
    session = ai.client.session_create()
    ai.client.v2_session_prompt(session.id, {"text": "Hello"})
```

All client methods return typed Pydantic models — IDE autocomplete,
`.model_dump()`, `.model_dump_json()`.

#### Connecting to an existing server

Skip subprocess management by pointing at a running `opencode serve`:

```python
from opencode import OpencodeClient

client = OpencodeClient(base_url="http://127.0.0.1:4096", directory=".")
health = client.health()
```

```python
from opencode import AsyncOpendcodeClient

async with AsyncOpendcodeClient(base_url="http://127.0.0.1:4096") as client:
    health = await client.health()
```

#### Cloning a client

```python
client2 = client.copy(base_url="http://other:4096", timeout=60.0)

# Or via with_options:
faster = client.with_options(timeout=10.0, max_retries=0)
```

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
| `AuthenticationError` | 401 | Invalid or missing API key |
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

```python
with Opencode(model="anthropic/claude-sonnet-4") as ai:
    result = ai.ask(
        "Generate a user profile",
        format={
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
            },
        },
    )
    # result is a JSON string matching the schema
```

Works with `opencode()`, `async_opencode()`, `Session.prompt()`, and `Session.ask()`.

Requires a model that supports `tool_choice="required"` (Claude, GPT-4).
The free `opencode/big-pickle` (DeepSeek) does NOT support this.

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

### Interactive dialog

```bash
python live.py
```

Multi-turn dialog with `keep=True`, server cleaned up on exit via `atexit`.

### ToolExecutor reference

```python
from opencode import ToolExecutor

# Default permissions:
#   bash → "ask"   (prompts in console)
#   write → "allow"
#   edit  → "allow"
#   read  → "allow"
#   glob  → "allow"
#   grep  → "allow"

executor = ToolExecutor(
    permissions={
        "bash": "allow",      # always allow
        "write": "deny",       # always deny
        "grep": "ask",         # ask each time
    },
    workdir="/path/to/sandbox",  # restrict file operations here
    confirm=lambda name, inp: name != "bash",  # custom confirm function
)

# Use with Session.ask():
session.ask("Create a project", tool_executor=executor)
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
| `port` | `4096` | Port for the server |
| `directory` | `None` | Working directory passed to all API calls |
| `workspace` | `None` | Workspace directory for the session |
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
    async for chunk in ai.ask_stream("Write a poem"):
        print(chunk, end="")
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

# Also accepts: model, format, port, directory, config, agent, auto_tools
```

## OpenAPI response models

```python
from opencode._response_models import HealthResponse, SessionResponse, FileContentResponse

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

# Build
python -m build --wheel
```
