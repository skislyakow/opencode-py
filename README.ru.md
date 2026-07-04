# Opencode Python SDK

<p align="center">
  <a href="https://pypi.org/project/opencode-py/"><img src="https://img.shields.io/pypi/v/opencode-py" alt="PyPI version"></a>
  <a href="https://pypi.org/project/opencode-py/"><img src="https://img.shields.io/pypi/pyversions/opencode-py" alt="Python versions"></a>
  <a href="https://github.com/skislyakow/opencode-py/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/opencode-py" alt="License"></a>
  <a href="https://pypi.org/project/opencode-py/"><img src="https://img.shields.io/pypi/dm/opencode-py" alt="Downloads"></a>
  <a href="https://github.com/skislyakow/opencode-py/actions/workflows/test.yml"><img src="https://github.com/skislyakow/opencode-py/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <img src="https://img.shields.io/badge/build-hatchling-4051b5" alt="Hatchling">
  <img src="https://img.shields.io/badge/http-httpx-blue" alt="httpx">
</p>

Python SDK для [Opencode](https://opencode.ai) — open source AI coding agent.

```bash
pip install opencode-py
```

После установки команда `opencode-py` становится доступна **общесистемно** — из любой директории в терминале, не обязательно внутри проекта:

```bash
opencode-py "What is the capital of France?"
# opencode-py <prompt>  — одноразовый запрос
# echo 'question' | opencode-py  — через pipe
```

## Быстрый старт

### One-shot (запускает сервер, спрашивает, закрывает)

```python
from opencode import opencode

answer = opencode("What is the capital of France?")
print(answer)
```

### Context manager (рекомендуется)

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

### Диалоги

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

# keep=True — сервер и сессия живут между вызовами
r1 = opencode("Меня зовут Вася", keep=True)
r2 = opencode("Какое имя я назвал?", keep=True)  # помнит диалог
r3 = opencode("Хватит", keep=False)  # keep=False закрывает сервер
```

### Auto-tools (агент с инструментами)

```python
r = opencode("Создай файл hello.txt", auto_tools=True)
```

Инструменты: `bash`, `write`, `edit`, `read`, `glob`, `grep`.

По умолчанию `bash` спрашивает разрешение в консоли, остальные выполняются без вопроса.

Кастомные пермишены через `Session.ask()`:

```python
from opencode import Opencode, ToolExecutor

with Opencode() as ai:
    session = ai.create_session()
    msg = session.ask(
        "Напиши test.py с кодом print('hello')",
        tool_executor=ToolExecutor(permissions={"write": "allow"}),
    )
```

### Низкоуровневый API (любой endpoint)

```python
with Opencode() as ai:
    content = ai.client.file_read("src/main.py")
    diff = ai.client.vcs_diff("HEAD~3")
    config = ai.client.config_get()
    session = ai.client.session_create()
    ai.client.v2_session_prompt(session["id"], {"text": "Hello"})
```

### Web UI (без зависимостей)

```bash
python web/server.py
# → открыть http://127.0.0.1:3000
```

Встроенный HTTP-сервер + прокси к `opencode serve` — никаких зависимостей кроме Python.

### Интерактивный диалог

```bash
python live.py
```

Многострочный диалог с `keep=True`, сервер чистится при выходе (`atexit`).

### Конфигурация

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

### Async диалоги

```python
async with AsyncOpendcode() as ai:
    session = await ai.create_session()
    msg1 = await session.prompt("Suggest a project name")
    msg2 = await session.prompt("Now write a tagline for it")
```

### Async низкоуровневый клиент

```python
from opencode import AsyncOpendcodeClient

async with AsyncOpendcodeClient() as client:
    health = await client.health()
    print(health)
```

## Разработка

```bash
# Установка в editable mode
pip install -e ".[dev]"

# Запуск тестов
pytest

# Сборка
python -m build --wheel
```
