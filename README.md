# Opencode Python SDK

Python SDK for [Opencode](https://opencode.ai) — the open source AI coding agent.

```bash
pip install opencode-ai
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

### Low-level API (any endpoint)

```python
with Opencode() as ai:
    # Read files
    content = ai.client.file_read("src/main.py")
    # VCS operations
    diff = ai.client.vcs_diff("HEAD~3")
    # Config
    config = ai.client.config_get()
    # Custom session operations
    session = ai.client.session_create()
    ai.client.v2_session_prompt(session["id"], {"text": "Hello"})
```

### Configuration

```python
with Opencode(
    model="claude-sonnet-4-20250514",
    directory="/path/to/project",
    port=4096,
) as ai:
    ...
```

## Development

```bash
# Install in editable mode
pip install -e .

# Run tests
pytest

# Build
python -m build --wheel
```
