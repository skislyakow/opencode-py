# Документация Opencode (русская)

Источник: https://opencode.ai/docs/ru
Дата: 2026-07-02

---

## 1. Введение

**opencode** — это агент кодирования искусственного интеллекта с открытым исходным кодом. Доступен в виде интерфейса на базе терминала, настольного приложения или расширения IDE.

### Системные требования
- Современный эмулятор терминала (WezTerm, Alacritty, Ghostty, Kitty)
- Ключи API для провайдеров LLM

### Установка
```bash
curl -fsSL https://opencode.ai/install | bash
npm install -g opencode-ai
bun install -g opencode-ai
brew install anomalyco/tap/opencode
choco install opencode      # Windows
scoop install opencode       # Windows
```

### Настройка провайдера
```bash
# В TUI:
/connect  # выбрать провайдера, перейти по ссылке авторизации
```

### Инициализация проекта
```bash
cd /path/to/project
opencode
/init  # создаёт AGENTS.md
```

---

## 2. Конфигурация

Файлы: `opencode.json` или `opencode.jsonc`.

### Порядок приоритета (объединение)
1. Удаленная конфигурация (`.well-known/opencode`)
2. Глобальная (`~/.config/opencode/opencode.json`)
3. Пользовательская (`OPENCODE_CONFIG` env var)
4. Проектная (`opencode.json` в проекте)
5. Каталоги `.opencode` (агенты, команды, плагины)
6. Встроенная (`OPENCODE_CONFIG_CONTENT` env var)

### Схема конфигурации
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "theme": "opencode",
  "model": "anthropic/claude-sonnet-4-5",
  "small_model": "anthropic/claude-haiku-4-5",
  "autoupdate": true,
  "server": {
    "port": 4096,
    "hostname": "0.0.0.0",
    "mdns": true,
    "cors": ["http://localhost:5173"]
  },
  "provider": {
    "anthropic": {
      "options": {
        "apiKey": "{env:ANTHROPIC_API_KEY}",
        "timeout": 600000
      }
    }
  },
  "permission": {
    "edit": "allow",
    "bash": "ask"
  },
  "tools": {
    "write": false,
    "bash": false
  },
  "agent": {
    "code-reviewer": {
      "description": "Reviews code",
      "model": "anthropic/claude-sonnet-4-5",
      "prompt": "You are a code reviewer.",
      "tools": { "write": false, "edit": false }
    }
  },
  "default_agent": "plan",
  "command": {
    "test": {
      "template": "Run full test suite with coverage...",
      "description": "Run tests with coverage"
    }
  },
  "instructions": ["CONTRIBUTING.md", "docs/guidelines.md"],
  "disabled_providers": ["openai", "gemini"],
  "enabled_providers": ["anthropic", "openai"],
  "compaction": { "auto": true, "prune": false, "reserved": 10000 },
  "share": "manual",
  "mcp": {},
  "plugin": ["opencode-helicone-session"],
  "formatter": {
    "prettier": { "disabled": true }
  }
}
```

### Конфигурация TUI
Файл `tui.json`:
```json
{
  "$schema": "https://opencode.ai/tui.json",
  "theme": "tokyonight",
  "scroll_speed": 3,
  "diff_style": "auto"
}
```

### Переменные окружения
- `OPENCODE_CONFIG`, `OPENCODE_TUI_CONFIG`, `OPENCODE_CONFIG_DIR`
- `OPENCODE_CONFIG_CONTENT` — встроенный JSON
- `OPENCODE_SERVER_PASSWORD` — базовая аутентификация
- `OPENCODE_SERVER_USERNAME` — имя пользователя (по умолч. `opencode`)
- `OPENCODE_DISABLE_AUTOUPDATE`, `OPENCODE_DISABLE_PRUNE`
- `OPENCODE_ENABLE_EXA` — веб-поиск
- `OPENCODE_EXPERIMENTAL` — экспериментальные функции

---

## 3. Сервер (HTTP API)

```bash
opencode serve [--port 4096] [--hostname 127.0.0.1] [--cors http://localhost:5173]
```

OpenAPI spec: `http://<hostname>:<port>/doc`

### API endpoints

#### Глобальные
- `GET /global/health` — статус и версия
- `GET /global/event` — SSE поток событий

#### Проект
- `GET /project` — список проектов
- `GET /project/current` — текущий проект

#### Конфигурация
- `GET /config` — конфигурация
- `PATCH /config` — обновить конфиг
- `GET /config/providers` — провайдеры и модели по умолчанию

#### Провайдеры
- `GET /provider` — список провайдеров
- `GET /provider/auth` — методы аутентификации
- `POST /provider/{id}/oauth/authorize` — OAuth авторизация

#### Сессии (V1)
- `GET /session` — список сессий
- `POST /session` — создать сессию
- `GET /session/:id` — детали сессии
- `DELETE /session/:id` — удалить сессию
- `PATCH /session/:id` — обновить сессию
- `GET /session/:id/children` — дочерние сессии
- `GET /session/:id/todo` — задачи сессии
- `POST /session/:id/init` — анализ приложения / AGENTS.md
- `POST /session/:id/fork` — ответвление
- `POST /session/:id/abort` — прервать сессию
- `POST /session/:id/share` — поделиться
- `DELETE /session/:id/share` — отменить шару
- `GET /session/:id/diff` — дифф
- `POST /session/:id/summarize` — суммаризация
- `POST /session/:id/revert` — отменить сообщение
- `POST /session/:id/unrevert` — восстановить сообщение

#### Сообщения
- `GET /session/:id/message` — список сообщений
- `POST /session/:id/message` — отправить + ждать ответ
- `GET /session/:id/message/:messageID` — детали сообщения
- `POST /session/:id/prompt_async` — отправить асинхронно (204)
- `POST /session/:id/command` — выполнить слэш-команду
- `POST /session/:id/shell` — запустить shell-команду

#### Файлы и поиск
- `GET /file?path=<path>` — список файлов
- `GET /file/content?path=<path>` — читать файл
- `GET /file/status` — статус файлов
- `GET /find?pattern=<pat>` — поиск текста
- `GET /find/file?query=<q>` — поиск файлов
- `GET /find/symbol?query=<q>` — поиск символов

#### Прочее
- `GET /command` — список команд
- `GET /lsp` — статус LSP
- `GET /formatter` — статус форматтера
- `GET /mcp` — статус MCP
- `POST /mcp` — добавить MCP-сервер
- `GET /agent` — список агентов
- `GET /experimental/tool/ids` — ID инструментов
- `GET /experimental/tool` — инструменты со схемами
- `POST /log` — записать лог
- `POST /auth/:id` — установить учетные данные
- `GET /event` — SSE поток событий
- `POST /instance/dispose` — удалить инстанс
- `GET /vcs` — информация о VCS
- `GET /path` — текущий путь

#### TUI endpoints
- `POST /tui/submit-prompt`, `/tui/append-prompt`, `/tui/clear-prompt`
- `POST /tui/execute-command`, `/tui/show-toast`
- `POST /tui/open-help`, `/tui/open-sessions`, `/tui/open-models`, `/tui/open-themes`
- `POST /tui/control/response`, `GET /tui/control/next`

---

## 4. SDK (JavaScript/TypeScript)

```bash
npm install @opencode-ai/sdk
```

```typescript
import { createOpencode } from "@opencode-ai/sdk"
const { client } = await createOpencode({
  hostname: "127.0.0.1",
  port: 4096,
  config: { model: "anthropic/claude-3-5-sonnet-20241022" }
})
```

### Client-only mode
```typescript
import { createOpencodeClient } from "@opencode-ai/sdk"
const client = createOpencodeClient({ baseUrl: "http://localhost:4096" })
```

### Типы ответов
```typescript
import type { Session, Message, Part } from "@opencode-ai/sdk"
```

### Структурированный вывод
```typescript
const result = await client.session.prompt({
  path: { id: sessionId },
  body: {
    parts: [{ type: "text", text: "Research Anthropic" }],
    format: {
      type: "json_schema",
      schema: {
        type: "object",
        properties: {
          company: { type: "string" },
          founded: { type: "number" }
        },
        required: ["company", "founded"]
      }
    }
  }
})
```

---

## 5. CLI

```bash
opencode                    # TUI
opencode run "question"     # неинтерактивный режим
opencode serve              # HTTP-сервер
opencode web                # сервер + веб-интерфейс
opencode attach <url>       # подключение к серверу
opencode agent create       # создание агента
opencode agent list         # список агентов
opencode auth login         # настроить провайдера
opencode auth list          # список провайдеров
opencode auth logout        # удалить провайдера
opencode github install     # установка GitHub Actions
opencode mcp add            # добавить MCP
opencode mcp list           # список MCP
opencode models             # список моделей
opencode session list       # список сессий
opencode stats              # статистика токенов/стоимости
opencode export <id>        # экспорт сессии
opencode import <file>      # импорт сессии
opencode upgrade            # обновление
opencode uninstall          # удаление
```

### Флаги `run`
- `--model` / `-m` — модель (provider/model)
- `--agent` — агент
- `--file` / `-f` — прикрепить файл(ы)
- `--continue` / `-c` — продолжить сессию
- `--session` / `-s` — ID сессии
- `--fork` — ответвление
- `--share` — поделиться
- `--attach` — подключиться к серверу
- `--format` — `default` или `json`
- `--title` — название сессии
- `--dir` — каталог
- `--thinking` — показать размышления

---

## 6. Инструменты (встроенные)

| Инструмент | Описание | Разрешение |
|---|---|---|
| `bash` | Shell-команды | `allow` |
| `edit` | Точная замена строк | `allow` |
| `write` | Создание/перезапись файлов | `edit` |
| `patch` | Применение патчей | `edit` |
| `read` | Чтение файлов | `allow` |
| `grep` | Поиск regex | `allow` |
| `glob` | Поиск файлов по шаблону | `allow` |
| `webfetch` | Получение URL | `allow` |
| `websearch` | Веб-поиск (Exa) | `allow` |
| `question` | Вопросы пользователю | `allow` |
| `todowrite` | Список задач | `allow` |
| `skill` | Загрузка SKILL.md | `allow` |
| `lsp` | LSP-серверы (эксперим.) | `allow` |

---

## 7. Провайдеры

Opencode поддерживает 75+ провайдеров через AI SDK и Models.dev.

Популярные: Anthropic, OpenAI, Google Vertex AI, Amazon Bedrock, DeepSeek, Groq, Ollama (локальные), LM Studio, GitHub Copilot, GitLab Duo, OpenRouter, Azure OpenAI, Together AI, Fireworks AI, Hugging Face.

### OpenCode Zen
Рекомендуемый провайдер от команды opencode. `/connect` → opencode.ai/auth

### OpenCode Go
Недорогая подписка с открытыми моделями.

---

## 8. Архитектура

```
TUI/CLI/SDK  ←→  HTTP (REST + SSE)  ←→  opencode server  ←→  LLM providers
                   │
              OpenAPI spec
              (http://localhost:4096/doc)
```

- Сервер публикует OpenAPI 3.1 спецификацию по `/doc`
- SSE события по `/event` (первое событие: `server.connected`)
- TUI — клиент, который общается с сервером
- `opencode serve` — standalone сервер без TUI
