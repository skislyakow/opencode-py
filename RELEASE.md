# Release Process

## When to release

Run `python scripts/check-release.py` — it compares the current version in
`pyproject.toml` with the latest git tag and reports if a release is due.

A new release should be made when:

- New features are added (Pydantic models, retry, streaming, etc.)
- Breaking changes to the public API
- Significant bug fixes
- The dependency list changes (adds/removes a required package)
- CI has been green on master for the current changeset

## How to release

```bash
# 1. Update version in pyproject.toml
#    Follow semver: MAJOR.MINOR.PATCH
#    Pre-release: 0.2.0-dev, 0.2.0rc1

# 2. Commit the version bump
git add pyproject.toml
git commit -m "chore(release): bump version to X.Y.Z"

# 3. Tag
git tag vX.Y.Z

# 4. Build
python -m build

# 5. Publish to PyPI
#    Option A — via twine:
pip install twine
twine check dist/*
twine upload dist/*        # prod
# twine upload --repository testpypi dist/*  # test first

#    Option B — push tag (if CI/CD is set up):
git push origin vX.Y.Z

# 6. Push commits
git push
```

## Version history

| Version | Date | Highlights |
|---------|------|------------|
| 0.5.0   | 2026-07-05 | Typed SSE event models (~75 types, 60+ `*Props` models), `parse_stream_event()`, `parse_typed_event()`, `ask_stream` refactored to use typed models, `live_stream_events.py` demo |
| 0.4.1   | 2026-07-05 | `model_construct()` speedup, mypy fix in demo, 23 new unit tests |
| 0.4.0   | 2026-07-05 | `with_raw_response` pattern (RawResponse wrapper), streaming fix (no reasoning leakage, no echo, no duplicates) |
| 0.3.0   | 2026-07-05 | Typed Pydantic models for all client methods (cast_to), 30+ new model classes, _construct_type handles list[X] generics and {"data": [...]} format |
| 0.2.2   | 2026-07-04 | Comprehensive README documentation (EN/RU), Pydantic fixes in demo.py, mypy fixes |
| 0.2.1   | 2026-07-04 | Fix: rename entry point to `opencode-py` to avoid conflict with the real `opencode` binary |
| 0.2.0   | 2026-07-03 | Pydantic models, retry, typed errors, logging, async, streaming, auto-tools, web UI |
| 0.1.1   | 2026-07-03 | Fix author/URLs, add keywords, Docker smoke test, badges |
| 0.1.0   | 2026-06-30 | Initial PyPI release |
