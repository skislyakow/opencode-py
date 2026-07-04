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

После установки команда `opencode-py` становится доступна **общесистемно** — из любой директории в терминале:

```bash
opencode-py "What is the capital of France?"
# opencode-py <prompt>  — одноразовый запрос
# echo 'question' | opencode-py  — через pipe
```

## Quick start

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

### Multi-turn (keep mode)

```python
from opencode import opencode

# keep=True — server and session stay alive between calls
r1 = opencode("My name is Alice", keep=True)
r2 = opencode("What's my name?", keep=True)   # remembers the conversation
r3 = opencode("That's all", keep=False)        # keep=False closes the server
```

### Auto-tools (agentic tool execution)

```python
r = opencode("Create a file called hello.txt", auto_tools=True)
```

Available tools: `bash`, `write`, `edit`, `read`, `glob`, `grep`.

By default, `bash` asks for permission in the console, all others run without prompting.

Custom permissions via `Session.ask()`:

```python
from opencode import Opencode, ToolExecutor

with Opencode() as ai:
    session = ai.create_session()
    msg = session.ask(
        "Write test.py with print('hello')",
        tool_executor=ToolExecutor(permissions={"write": "allow"}),
    )
```

### Low-level API (any endpoint)

```python
with Opencode() as ai:
    content = ai.client.file_read("src/main.py")
    diff = ai.client.vcs_diff("HEAD~3")
    config = ai.client.config_get()
    session = ai.client.session_create()
    ai.client.v2_session_prompt(session.id, {"text": "Hello"})
```

All client methods return typed Pydantic models — IDE autocomplete, validation, `.model_dump()`, `.model_dump_json()`.

### Retry & error handling

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

### Debug logging

```bash
OPENCODE_LOG=debug python my_script.py
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

### Configuration

```python
with Opencode(
    model="claude-sonnet-4-20250514",
    directory="/path/to/project",
    port=4096,
) as ai:
    ...
```

## Async API

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

## Development

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run tests
pytest

# Build
python -m build --wheel
```
