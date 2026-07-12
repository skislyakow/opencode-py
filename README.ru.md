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

**Нужен ли предустановленный Opencode?** Нет. SDK автоматически скачивает
бинарник `opencode` под вашу ОС (Windows/macOS/Linux, x64/arm64) при первом
запуске в `~/.opencode/bin/`. Бинарник используется только внутри SDK — он
НЕ добавляется в PATH, НЕ устанавливается системно и НЕ появляется в меню Пуск.

**Что если позже установить официальный Opencode?** Если вы установите opencode
через `npm install -g opencode-ai` или другим способом, SDK будет использовать
версию из PATH — конфликтов нет.

*Подробнее в разделе [Управление бинарником](#управление-бинарником).*

## CLI

После установки команда `opencode-py` доступна **общесистемно** из любой директории:

```bash
opencode-py "What is the capital of France?"   # одноразовый запрос
echo "What is the capital of France?" | opencode-py  # через pipe
opencode-py --help                              # все флаги
```

Флаги CLI:

| Флаг | Описание |
|------|----------|
| `prompt` (позиционный) | Текст запроса или чтение из stdin |
| `--model` / `-m` | Имя модели (например `opencode/big-pickle`) |
| `--keep` / `-k` | Сохранять сессию между вызовами |
| `--auto-tools` | Агентное выполнение инструментов |
| `--directory` / `-d` | Рабочая директория |
| `--port` / `-p` | Порт сервера (по умолчанию авто — первый свободный) |

Также доступен `python -m opencode`:

```bash
python -m opencode "Explain dependency injection"
python -m opencode --model "opencode/big-pickle" "Hello"
```

## Справочник клиентской библиотеки

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

`ask_stream()` подписывается на SSE (`/event`) эндпоинт сервера, отправляет
запрос и выдаёт каждый текстовый фрагмент по мере поступления. Reasoning-блоки,
эхо пользователя и дублирующийся текст автоматически фильтруются.

С `collect=True` `ask_stream()` возвращает `StreamResult` (или
`AsyncStreamResult` для async), который сохраняет `.events` и `.text`:

```python
with Opencode() as ai:
    stream = ai.ask_stream("Напиши функцию", collect=True)
    for chunk in stream:
        print(chunk, end="")
    # После итерации:
    print(stream.text)     # полный текст ответа
    print(stream.events)   # все сырые SSE события
```

V2 `Session.prompt()` также использует `/event` SSE внутри — отправляет
неблокирующий V2 запрос, подписывается на события и ждёт
`session.next.step.ended` перед сборкой ответа. V1 блокирующий промпт
используется как fallback, когда указаны `model` или `format`.

#### Ответ с сырыми событиями (`collect`)

Все высокоуровневые методы принимают `collect=True` и возвращают
датакласс `OpendcodeResponse` с текстом ответа и сырыми SSE событиями:

```python
from opencode import opencode, OpencodeResponse

response = opencode("Hello", collect=True)
print(response.text)       # "Hello! How can I help you?"
print(response.events)     # все SSE события из диалога
# response имеет тип OpencodeResponse
```

```python
from opencode import Opencode

with Opencode() as ai:
    session = ai.create_session()
    result = session.prompt("Say hi", collect=True)
    print(result.text)      # "Hi!"
    print(result.events)    # [StreamEvent, ...] — полный лог событий
```

Работает с: `Session.prompt()`, `Session.ask()`, `Opencode.ask()`,
`opencode()`, `async_opencode()`, `ask_stream(collect=True)`.

#### Типизированные события стриминга

Для продвинутого использования SDK предоставляет полный SSE-поток в виде
типизированных Pydantic-моделей через `parse_stream_event()`:

```python
from opencode._stream_events import (
    MessagePartDeltaProps,
    MessagePartUpdatedProps,
    MessageUpdatedProps,
    SessionStatusProps,
    parse_stream_event,
)

with Opencode() as ai:
    session = ai.create_session()
    response = ai.client.event_subscribe()  # сырой SSE поток
    ai.client.session_send(session.id, {"parts": [{"type": "text", "text": "Hi"}]})

    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        event = parse_stream_event(line[6:])
        props = event.properties

        # Пропускаем события других сессий
        if props.get("sessionID") not in (None, session.id):
            continue

        if event.type == "message.part.delta":
            p = MessagePartDeltaProps.model_construct(**props)
            print(p.delta, end="")  # типизированный доступ к .delta, .partID и т.д.

        elif event.type == "session.status":
            p = SessionStatusProps.model_construct(**props)
            if p.status.get("type") == "idle":
                break
```

Работает для всех ~75 типов событий: `message.updated`, `session.status`,
`session.next.text.delta`, `permission.asked`, `question.asked`, `file.edited`
и других.

> **Примечание**: Пример выше использует V1 блокирующий промпт (`session_send`).
> V2 `Session.prompt()` внутри использует события `session.next.*`
> (`session.next.prompted`, `session.next.step.ended`, и т.д.) через
> тот же `/event` SSE эндпоинт.

Используйте `parse_typed_event()` для автоматической валидации. Полный пример
в [`live_stream_events.py`](#интерактивный-диалог).

### Диалоги

```python
with Opencode() as ai:
    session = ai.create_session()
    msg1 = session.prompt("Suggest a project name")
    print(f"AI: {msg1}")
    msg2 = session.prompt("Now write a tagline for it")
    print(f"AI: {msg2}")
```

`Session.prompt()` использует V2 неблокирующий промпт + SSE подписку для
более быстрых ответов. Падает на V1 блокирующий промпт когда указаны
`model` или `format` (например structured output).

### Методы Session

Каждый объект `Session` предоставляет дополнительные методы:

```python
with Opencode() as ai:
    session = ai.create_session()
    session.prompt("Hello")

    # История диалога
    ctx = session.context()        # список всех сообщений
    msgs = session.messages()      # пагинированный список

    # Управление
    session.abort()                # прервать генерацию
    session.delete_message("msg_xxx")  # перманентно удалить сообщение
    session.compact()              # сжать историю
    session.fork()                 # форкнуть в новую сессию

    # Инспекция
    session.diff()                 # файловые изменения от AI
    session.todo()                 # оставшиеся задачи
```

Удаление сообщения перманентно — сообщение и его части удаляются без отката файловых изменений. Чтобы отменить изменения, сделанные сообщением, используйте `session.revert()` (или `session.fork()` для ответвления).

### Multi-turn (keep mode)

Переиспользует сервер и сессию между вызовами:

```python
from opencode import opencode

r1 = opencode("Меня зовут Вася", keep=True)
r2 = opencode("Какое имя я назвал?", keep=True)  # помнит диалог
r3 = opencode("Хватит", keep=False)               # закрывает сервер

# Также принимает: model, format, port, directory, config, agent
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
        tool_executor=ToolExecutor(
            permissions={"write": "allow"},
            workdir="/path/to/sandbox",       # ограничить файловые операции
        ),
        max_tool_rounds=25,                     # лимит безопасности
        quiet=True,                             # скрыть логи инструментов
    )
```

Первый ответ AI в `ask()` входит в plan mode — SDK автоматически подтверждает
`"Exit plan mode and proceed"`, чтобы модель сразу выполняла инструменты.

### Низкоуровневый клиент (любой endpoint)

```python
with Opencode() as ai:
    content = ai.client.file_read("src/main.py")
    diff = ai.client.vcs_diff("HEAD~3")
    config = ai.client.config_get()
    session = ai.client.session_create()
    ai.client.v2_session_prompt(session.id, {"text": "Hello"})
```

Все методы возвращают типизированные Pydantic модели — IDE автодополнение,
`.model_dump()`, `.model_dump_json()`.

#### Подключение к существующему серверу

Без запуска подпроцесса — напрямую к работающему `opencode serve`:

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

#### Клонирование клиента

```python
client2 = client.copy(base_url="http://other:4096", timeout=60.0)

# Через with_options:
faster = client.with_options(timeout=10.0, max_retries=0)
```

#### Сырой HTTP ответ

Оборачивает любой метод клиента, чтобы также вернуть сырой `httpx.Response`:

```python
from opencode import RawResponse

with client.with_raw_response:
    raw: RawResponse = client.health()

raw.status_code              # 200
raw.headers                  # httpx.Headers
raw.content                  # bytes
raw.parsed                   # HealthResponse (типизированная модель)
raw.response                 # httpx.Response (полный)
```

Контекстный менеджер сбрасывается автоматически после одного вызова. Работает
с любым методом клиента (sync и async). См. `live_raw.py` для полного примера.

### Retry & обработка ошибок

Типизированная иерархия исключений. Все ошибки импортируются из `opencode`:

```python
from opencode import OpencodeClient, RateLimitError, InternalServerError

client = OpencodeClient(max_retries=3)  # exponential backoff + jitter

try:
    health = client.health()
    print(health.version)
except RateLimitError:
    print("too many requests — retried but failed")
except InternalServerError:
    print("server error")
```

Полная иерархия ошибок:

| Класс | HTTP статус | Когда возникает |
|-------|-------------|----------------|
| `OpencodeError` | — | Базовый класс для всех SDK ошибок |
| `APIConnectionError` | — | Ошибка сети / соединения |
| `APITimeoutError` | — | Таймаут запроса |
| `APIResponseValidationError` | — | Ответ не соответствует схеме |
| `APIStatusError` | 4xx/5xx | Базовый для HTTP ошибок |
| `BadRequestError` | 400 | Некорректный запрос |
| `AuthenticationError` | 401 | Неверный или отсутствующий API ключ |
| `PermissionDeniedError` | 403 | Доступ запрещён |
| `NotFoundError` | 404 | Ресурс не найден |
| `ConflictError` | 409 | Конфликт ресурсов |
| `UnprocessableEntityError` | 422 | Ошибка валидации тела запроса |
| `RateLimitError` | 429 | Превышен лимит запросов |
| `InternalServerError` | 500+ | Ошибка сервера |
| `BinaryNotFoundError` | — | Бинарник opencode не найден в PATH |
| `ServerStartupTimeoutError` | — | Сервер не запустился вовремя |

Политика retry: 408, 409, 429, 5xx и таймауты повторяются с экспоненциальной
задержкой + jitter. Заголовки `Retry-After` и `retry-after-ms` учитываются.

### Structured output

```python
with Opencode(model="anthropic/claude-sonnet-4") as ai:
    result = ai.ask(
        "Сгенерируй профиль пользователя",
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
    # result — JSON строка, соответствующая схеме
```

Работает с `opencode()`, `async_opencode()`, `Session.prompt()` и `Session.ask()`.

Требует модель с поддержкой `tool_choice="required"` (Claude, GPT-4).
Бесплатная модель `opencode/big-pickle` (DeepSeek) НЕ поддерживает.

### Отладка

```bash
# Linux / macOS (bash/zsh)
OPENCODE_LOG=debug python my_script.py

# Windows (PowerShell)
$env:OPENCODE_LOG="debug"; python my_script.py

# Windows (cmd)
set OPENCODE_LOG=debug && python my_script.py
```

Включает подробное логирование HTTP-запросов (метод, URL, заголовки, время выполнения).

### Web UI (без зависимостей)

```bash
python web/server.py
# → открыть http://127.0.0.1:3000
```

Встроенный HTTP-сервер + прокси к `opencode serve` — никаких зависимостей кроме Python.

### Интерактивный диалог

```bash
python live.py            # синхронный многошаговый диалог
python live_async.py      # асинхронный многошаговый диалог
python live_streaming.py  # стриминг диалог (переиспользование сессии)
python live_raw.py        # демо with_raw_response (7 сценариев)
python live_stream_events.py "Ваш запрос"  # инспекция SSE событий
python demo.py            # полное тестирование API (38 эндпоинтов)
```

Все скрипты чистят сервер при выходе через `atexit`.

### ToolExecutor (справочник)

```python
from opencode import ToolExecutor

# Пермишены по умолчанию:
#   bash  → "ask"   (спрашивать в консоли)
#   write → "allow"
#   edit  → "allow"
#   read  → "allow"
#   glob  → "allow"
#   grep  → "allow"

executor = ToolExecutor(
    permissions={
        "bash": "allow",       # всегда разрешать
        "write": "deny",        # всегда запрещать
        "grep": "ask",          # спрашивать каждый раз
    },
    workdir="/path/to/sandbox",   # ограничить файловые операции
    confirm=lambda name, inp: name != "bash",  # кастомная функция
)

# Использование с Session.ask():
session.ask("Create a project", tool_executor=executor)
```

### Управление бинарником

Если `opencode` не найден в PATH, SDK автоматически скачивает его в
`~/.opencode/bin/opencode`.

Порядок разрешения:
1. `PATH` — `shutil.which("opencode")`
2. `~/.opencode/bin/opencode` — ранее скачанная копия
3. GitHub releases — скачивание под текущую платформу

Поддерживаемые платформы: `win32-x64`, `win32-arm64`, `darwin-x64`,
`darwin-arm64`, `linux-x64`, `linux-arm64`.

Явное указание пути:

```python
with Opencode(opencode_binary="/custom/path/opencode") as ai:
    ...
```

### OpencodeServer (низкоуровневое управление сервером)

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

# Позже:
server.close()  # убивает подпроцесс
```

## Справочник конфигурации

Все параметры `Opendcode()` / `AsyncOpendcode()`:

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `model` | `None` | Имя модели, например `"opencode/big-pickle"` или `"provider/model"` |
| `hostname` | `"127.0.0.1"` | Адрес для привязки сервера |
| `port` | `None` (авто) | Порт сервера; `None` выбирает первый свободный |
| `directory` | `None` | Рабочая директория для всех API вызовов |
| `workspace` | `None` | Директория workspace для сессии |
| `server_timeout` | `30.0` | Секунд ожидания запуска сервера |
| `client_timeout` | `300.0` | Секунд до таймаута HTTP запроса |
| `config` | `None` | Словарь конфигурации сервера |
| `opencode_binary` | `None` | Путь к бинарнику opencode (авто-скачивание если не указан) |

Все параметры keyword-only.

## Async API

### Базовое использование

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

Асинхронный стриминг тоже поддерживает `collect`:

```python
async with AsyncOpendcode() as ai:
    stream = ai.ask_stream("Write a poem", collect=True)
    async for chunk in stream:
        print(chunk, end="")
    print(stream.events)  # сырые SSE события
    print(stream.text)    # полный текст ответа
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
    print(health.version)  # типизированная Pydantic модель
```

### Async функция-утилита

```python
from opencode import async_opencode

result = await async_opencode("Hello", keep=True)
result2 = await async_opencode("Still there?", keep=True)
result3 = await async_opencode("Bye")

# Также принимает: model, format, port, directory, config, agent, auto_tools
```

## Ключевые типы

### OpencodeResponse

```python
from opencode import OpencodeResponse

response = session.prompt("Hello", collect=True)
# response.text    -> str                 (извлечённый текст ответа)
# response.events  -> list[StreamEvent]   (сырые SSE события)
```

Возвращается `Session.prompt()`, `Session.ask()`, `Opencode.ask()`,
`opencode()`, `async_opencode()` и их async-версиями при `collect=True`.

### StreamResult / AsyncStreamResult

```python
from opencode import StreamResult, AsyncStreamResult

stream = ai.ask_stream("Hello", collect=True)
# for chunk in stream:     — итерация по фрагментам текста
# stream.events            -> list[StreamEvent]  (после итерации)
# stream.text              -> str                (полный текст ответа)
```

`StreamResult` (sync) и `AsyncStreamResult` (async) оборачивают
`ask_stream(collect=True)`, собирая все SSE события для последующего
просмотра.

### Pydantic response модели

```python
from opencode._response_models import HealthResponse, SessionResponse, FileContentResponse

# Это классы BaseModel с методами:
#   .model_dump() -> dict
#   .model_dump_json() -> str
#   .model_validate(dict) -> classmethod
```

## Разработка

```bash
# Установка в editable mode
pip install -e ".[dev]"

# Запуск тестов
pytest

# Линтинг и проверка типов
ruff check src/
mypy src/

# Сборка
python -m build --wheel
```
