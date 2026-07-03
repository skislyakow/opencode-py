"""Check if a new PyPI release is needed.

Compares the version in pyproject.toml with the latest git tag.
Exits with code 0 if no release needed, 1 if a release is recommended.

Usage:
    python scripts/check-release.py
    python scripts/check-release.py --verbose
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def get_current_version() -> str:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    text = pyproject.read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if m:
        return m.group(1)
    raise RuntimeError("Could not find version in pyproject.toml")


def get_latest_tag() -> str | None:
    result = subprocess.run(
        ["git", "tag", "--list", "v*", "--sort=-version:refname"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
    return tags[0] if tags else None


def get_commit_count_since_tag(tag: str) -> int:
    result = subprocess.run(
        ["git", "rev-list", f"{tag}..HEAD", "--count"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    return int(result.stdout.strip() or "0")


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    current = get_current_version()
    latest_tag = get_latest_tag()

    print(f"Current version (pyproject.toml): {current}")

    if latest_tag is None:
        print("No git tags found — this would be the first release.")
        return 0

    tag_version = latest_tag.lstrip("v")
    print(f"Latest git tag:                  {latest_tag}")

    commits_since = get_commit_count_since_tag(latest_tag)

    if current == tag_version:
        if commits_since > 0:
            print(f"\n==> {commits_since} commit(s) since {latest_tag}, "
                  f"but version hasn't been bumped ({current}).")
            if verbose:
                result = subprocess.run(
                    ["git", "log", f"{latest_tag}..HEAD", "--oneline"],
                    capture_output=True, text=True,
                    cwd=Path(__file__).parent.parent,
                )
                print("\nUnreleased commits:")
                for line in result.stdout.splitlines():
                    print(f"  {line}")
            print("\n=> Run `python -m build` and publish when ready:")
            print("  python -m build")
            print("  twine upload dist/*")
            return 1
        else:
            print("\n[ok] Everything is up to date. No release needed.")
            return 0
    else:
        print(f"\n=> Version in pyproject.toml ({current}) differs from "
              f"latest tag ({tag_version}).")
        print("  A new release may be ready to publish.")
        if verbose:
            print("\n  To publish:")
            print("  git tag v" + current)
            print("  git push origin v" + current)
            print("  python -m build && twine upload dist/*")
        return 0


if __name__ == "__main__":
    sys.exit(main())
