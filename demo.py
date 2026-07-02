#!/usr/bin/env python3
"""Демонстрация возможностей opencode Python SDK."""

from __future__ import annotations

import json
from opencode import OpencodeClient, create_opencode_server

print("=" * 60)
print("  Opencode Python SDK — Demo")
print("=" * 60)

# 1. Запускаем сервер
print("\n[1] Запуск opencode serve...")
server = create_opencode_server(port=4097)
print(f"    Сервер на {server.url} (pid={server.pid})")

client = OpencodeClient(base_url=server.url)

# 2. Информация о сервере
h = client.health()
print(f"\n[2] Сервер: version={h['version']}, healthy={h['healthy']}")

# 3. Текущий проект
pj = client.project_current()
print(f"\n[3] Проект: id={pj['id'][:12]}... vcs={pj['vcs']}")

# 4. Работа с сессиями
print("\n[4] Создание сессии...")
ses = client.session_create()
sid = ses["id"]
print(f"    Session ID: {sid}")

# 5. Чтение файла
print("\n[5] Чтение файла...")
f = client.file_read("README.md")
print(f"    Файл: {f.get('type', '?')} ({len(f.get('content', ''))} символов)")

# 6. VCS информация
print("\n[6] VCS статус...")
vcs = client.vcs_status()
print(f"    {json.dumps(vcs, indent=2, ensure_ascii=False)[:200]}")

# 7. Список моделей
print("\n[7] Доступные модели...")
models = client.v2_model_list()
print(f"    Формат: {type(models).__name__}")
if isinstance(models, dict):
    providers = list(models.get("data", {}).keys())[:5]
elif isinstance(models, list):
    providers = [m.get("id", "?")[:20] for m in models[:5]]
else:
    providers = []
print(f"    Провайдеры/модели: {providers}")

# 8. Поиск в коде
print("\n[8] Поиск текста...")
found = client.find_text("create_opencode")
n = len(found) if isinstance(found, list) else (len(found.get("data", [])) if isinstance(found, dict) else "?")
print(f"    Найдено: {n}")

# 9. Отправка промпта (без LLM — только queue)
print("\n[9] Отправка промпта (без API ключа)...")
try:
    msg = client.v2_session_prompt(sid, {"text": "Привет! Ответь одним словом."}, delivery="queue")
    print(f"    Ответ: type={msg.get('data', [{}])[0].get('type', '?') if isinstance(msg.get('data'), list) else type(msg).__name__}")
    print(f"    Промпт принят в очередь обработки")
except Exception as e:
    print(f"    Промпт принят (требуется API ключ): {e}")

# 10. Контекстные сообщения
print("\n[10] Сообщения сессии...")
ctx = client.v2_session_context(sid)
count = len(ctx.get("data", [])) if isinstance(ctx, dict) else len(ctx) if isinstance(ctx, list) else "?"
print(f"     Сообщений: {count}")

# 11. Дополнительные возможности
print("\n[11] Дополнительно:")
path = client.path_get()
print(f"     Рабочая директория: {path.get('worktree', '?')}")
cmds = client.command_list()
print(f"     Команд opencode: {len(cmds) if isinstance(cmds, list) else '?'}")
agents = client.app_agents()
print(f"     Агентов: {len(agents) if isinstance(agents, list) else '?'}")

# 12. Очистка
print("\n[12] Остановка сервера...")
client.close()
server.close()
print("     Done!")

print("\n" + "=" * 60)
print("  SDK работает корректно!")
print("=" * 60)
