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
| 0.1.1   | —    | Initial PyPI release |
| 0.2.0   | TBD  | Pydantic models, retry, typed errors, logging, async, streaming, auto-tools, web UI |
