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

Ожидается: `ruff` — только N815 (camelCase поля из API, предустановленные), `mypy` — Success.

## 3. Живой тест (с opencode в PATH)

```bash
python test_live.py
```

Запускает `opencode serve`, проходит 38 endpoint-чеков.

## 4. Демо (один вопрос)

```bash
python demo.py
```

Должен ответить на "What is the capital of France?".

## 5. Интерактивный режим

```bash
python live.py
```

Проверить multi-turn (ctrl+C для выхода).

## 6. Streaming

```bash
python live_streaming.py
```

## 7. Web UI

```bash
python web/server.py
```

Открыть браузер на `http://localhost:8000`.

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

После успешной проверки:
```bash
git tag v0.3.0
git push origin master --tags
python -m build
twine check dist/*
twine upload dist/*
```
