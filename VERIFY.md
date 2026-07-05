# Verification Checklist — v0.3.0-dev

Перед повышением версии и публикацией нужно проверить:

## 1. Unit-тесты (без сервера)

```bash
pytest tests/ -v
```

Ожидается: **31 passed**.

## 2. Линтер и типы

```bash
ruff check src/ tests/
mypy src/
```

Ожидается: `ruff` — All checks passed, `mypy` — Success.

## 3. Демо

```bash
python demo.py
```

Должен пройти все 12 шагов без ошибок, завершиться "SDK is working correctly!".

## 4. Живой тест

```bash
python test_live.py
```

Запускает `opencode serve`, проходит 38 endpoint-чеков.

## 5. Интерактивный режим

```bash
python live.py
```

Проверить multi-turn (Ctrl+C для выхода).

## 6. Streaming

```bash
python live_streaming.py
```

## 7. Web UI

```bash
python web/server.py
```

Открыть браузер на `http://localhost:3000`.

## 8. Async

```bash
python live_async.py
```

## 9. Проверка upstream

```bash
python scripts/check-upstream.py
```

Ожидается: "No SDK changes needed" (если upstream не менялся).

---

После успешной проверки скажи — я подниму версию в `pyproject.toml`, сделаю тег `v0.3.0` и опубликую:

```bash
git tag v0.3.0
git push origin master --tags
python -m build
twine check dist/*
twine upload dist/*
```
