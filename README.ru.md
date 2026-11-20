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

`ask_stream()` подписывается на SSE эндпоинт сервера (`GET /api/event`),
отправляет запрос и выдаёт каждый фрагмент `session.text.delta` по мере
поступления. Reasoning не выдаётся.

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

`Session.prompt()` также использует поток событий внутри — отправляет
`POST /api/session/{id}/prompt`, следит за `/api/event` до завершения запуска
(`session.execution.succeeded` / `interrupted`, или выбрасывает исключение при
`failed`), затем читает ответ из `GET /api/session/{id}/context`.

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
from opencode._stream_events import SessionTextDeltaProps, parse_stream_event

with Opencode() as ai:
    session = ai.create_session()
    stream = ai.client.event_subscribe()        # сырой SSE поток (GET /api/event)
    ai.client.session_prompt(session.id, "Hi")  # неблокирующий

    for line in stream.iter_lines():
        if not line.startswith("data:"):
            continue
        event = parse_stream_event(line[5:].strip())
        if event.session_id != session.id:     # пропускаем другие сессии
            continue
        if event.type == "session.text.delta":
            p = SessionTextDeltaProps.model_construct(**event.properties)
            print(p.delta, end="")              # типизированный доступ к .delta
        elif event.type in ("session.execution.succeeded", "session.execution.failed"):
            break
    stream.close()
```

Модели есть для всех ~100 типов событий v2 (сгенерированы из `/openapi.json`
сервера): `session.text.delta`, `session.tool.called`,
`session.execution.succeeded`, `permission.asked`, `form.created`, ...
`StreamEvent.properties` содержит объект `data` события.

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

Модель сессии фиксируется при её создании (`Opencode(model=...)` или
`create_session(model=...)`); `session.prompt(text, model=...)` сначала
переключает её. `wait=False` только ставит промпт в очередь и возвращает
сообщение пользователя.

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
    session.abort()                # прервать текущее выполнение
    session.compact()              # сжать историю
    session.fork()                 # форкнуть в новую сессию
    session.delete()               # удалить сессию

    # Инспекция
    session.info()                 # SessionResponse (модель, стоимость, токены, ...)
    session.diff()                 # файловые изменения от AI
```

Откат доступен через клиент: `session_revert_stage()`,
`session_revert_commit()`, `session_revert_clear()`.

### Multi-turn (keep mode)

Переиспользует сервер и сессию между вызовами:

```python
from opencode import opencode

r1 = opencode("Меня зовут Вася", keep=True)
r2 = opencode("Какое имя я назвал?", keep=True)  # помнит диалог
r3 = opencode("Хватит", keep=False)               # закрывает сервер

# Также принимает: model, port, directory, config, agent
```

### Инструменты и разрешения

Инструменты (`shell`, `write`, `edit`, `read`, ...) выполняются **на сервере
opencode**. Когда правила разрешений сервера говорят `ask`, он отправляет
`permission.asked`; `Session.prompt()` отвечает на него с помощью переданного
`tool_executor`, а если его нет — отклоняет. Отклонённое разрешение завершает
запуск.

```python
r = opencode("Создай файл hello.txt", auto_tools=True)
```

`auto_tools=True` (и `Session.ask()`) используют `ToolExecutor` по умолчанию,
который спрашивает в консоли перед `shell`/`bash` и разрешает всё остальное.

```python
from opencode import Opencode, ToolExecutor

with Opencode() as ai:
    session = ai.create_session(
        # опционально: сервер спрашивает перед каждой shell-командой
        permissions=[{"action": "shell", "resource": "*", "effect": "ask"}],
    )
    msg = session.ask(
        "Напиши test.py с кодом print('hello') и запусти его",
        tool_executor=ToolExecutor(permissions={"shell": "allow"}),
        quiet=True,                             # скрыть логи инструментов
    )
```

### Низкоуровневый клиент (любой endpoint)

```python
with Opencode() as ai:
    content = ai.client.fs_read("src/main.py")
    diff = ai.client.vcs_diff()
    models = ai.client.model_list()
    session = ai.client.session_create(model="opencode/big-pickle")
    ai.client.session_prompt(session.id, "Hello")   # неблокирующий
    ai.client.session_wait(session.id)              # ждать до простоя
    messages = ai.client.session_context(session.id)
```

Все методы клиента работают с v2 API opencode (`/api/*`) и возвращают
типизированные Pydantic модели — IDE автодополнение, `.model_dump()`,
`.model_dump_json()`. Обёртка `{"data": ...}` разворачивается; пагинированные
списки (`session_list()`, `session_messages()`) возвращают `PageResponse` с
`.data` и `.cursor`. `directory` клиента передаётся как `location[directory]`.

#### Подключение к существующему серверу

Без запуска подпроцесса — напрямую к работающему `opencode serve`. Сервер v2
требует HTTP Basic auth (пользователь `opencode`); передайте пароль сервера или
задайте `OPENCODE_SERVER_PASSWORD`:

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

`create_opencode_server()` генерирует случайный пароль и предоставляет его как
`server.password`:

```python
from opencode import OpencodeClient, create_opencode_server

server = create_opencode_server()
client = OpencodeClient(base_url=server.url, password=server.password)
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
raw.parsed                   # ServerInfoResponse (типизированная модель)
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
| `AuthenticationError` | 401 | Отсутствующий или неверный пароль сервера |
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

Не поддерживается v2 API opencode — передача `format=` выбрасывает
`OpencodeError`.

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

> **Примечание**: web UI ещё не портирован на v2 API opencode.

### Интерактивный диалог

```bash
python live.py            # синхронный многошаговый диалог
python live_async.py      # асинхронный многошаговый диалог
python live_streaming.py  # стриминг диалог (переиспользование сессии)
python live_raw.py        # демо with_raw_response (7 сценариев)
python live_stream_events.py "Ваш запрос"  # инспекция SSE событий
python demo.py            # краткий обзор v2 API
python test_live.py       # живая проверка 36 эндпоинтов без LLM
```

Все скрипты чистят сервер при выходе через `atexit`.

### ToolExecutor (справочник)

```python
from opencode import ToolExecutor

# Ключи — действия разрешений, о которых спрашивает сервер.
# По умолчанию: shell/bash -> "ask" (вопрос в консоли), всё остальное -> "allow".
executor = ToolExecutor(
    permissions={
        "shell": "allow",     # всегда разрешать
        "edit": "deny",       # всегда отклонять
        "read": "ask",        # вызвать confirm()
    },
    confirm=lambda action, request: "rm" not in " ".join(request["resources"]),
)

session.ask("Create a project", tool_executor=executor)
executor.decide({"action": "edit"})   # -> "reject"
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
| `directory` | `None` | Рабочая директория (`location` сессии и `location[directory]` во всех API вызовах) |
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
    session = await ai.create_session()   # async ask_stream требует сессию
    async for chunk in ai.ask_stream("Write a poem", session=session):
        print(chunk, end="")
```

Асинхронный стриминг тоже поддерживает `collect`:

```python
async with AsyncOpendcode() as ai:
    session = await ai.create_session()
    stream = ai.ask_stream("Write a poem", session=session, collect=True)
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

# Также принимает: model, port, directory, config, agent, auto_tools
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
from opencode._response_models import ServerInfoResponse, SessionResponse, PageResponse

# Сгенерированы из /openapi.json сервера; все поля опциональны, лишние сохраняются.
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
