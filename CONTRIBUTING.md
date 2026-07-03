# Contributing

## Development setup

```bash
pip install -e ".[dev]"
```

## Code style

- Type hints everywhere
- Avoid `Any` where possible — use `TypedDict` from `_models.py`
- Avoid single-use helper functions
- Prefer httpx over urllib/requests
- Method naming: snake_case with category prefix (e.g., `v2_session_*`, `file_*`)
- No comments unless absolutely necessary

## Testing

```bash
# Unit tests (no server needed)
pytest tests/ -v

# Live integration test (requires opencode in PATH)
python test_live.py
```

## Commit convention

```
type(scope): summary
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

## Pre-commit checks

Before committing, run:

```bash
ruff check .
mypy src/
pytest tests/ -v
```
