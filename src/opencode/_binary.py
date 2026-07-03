from __future__ import annotations

import os
import platform
import re
import shutil
import stat
import sys
from pathlib import Path


def _system() -> str:
    raw = platform.system().lower()
    if raw == "darwin":
        return "darwin"
    if raw == "windows":
        return "win32"
    return "linux"


def _arch() -> str:
    raw = platform.machine().lower()
    if raw in ("amd64", "x86_64"):
        return "x64"
    if raw in ("aarch64", "arm64"):
        return "arm64"
    return raw


def _platform_suffix() -> str:
    return f"{_system()}-{_arch()}"


def _resolve_wrapper(path: str) -> str:
    """If *path* is a .cmd/.bat wrapper (npm-style), return the real .exe it launches."""
    if not path.lower().endswith((".cmd", ".bat")):
        return path
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            m = re.search(r'"([^"]+\.exe)"', line)
            if m:
                rel = m.group(1)
                full = rel.replace("%dp0%", os.path.dirname(path)).replace("/", "\\")
                if os.path.isfile(full):
                    return os.path.realpath(full)
    except Exception:
        pass
    return path


def find_in_path(name: str = "opencode") -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return _resolve_wrapper(resolved)
    if sys.platform == "win32":
        for ext in (".exe", ".cmd", ".bat"):
            resolved = shutil.which(name + ext)
            if resolved:
                return _resolve_wrapper(resolved)
    return None


def binary_dir() -> Path:
    return Path.home() / ".opencode" / "bin"


def find_local(name: str = "opencode") -> str | None:
    candidates = [name]
    if sys.platform == "win32":
        candidates = [f"{name}.exe", name]
    for candidate in candidates:
        full = binary_dir() / candidate
        if full.exists():
            return str(full.resolve())
    return None


def ensure_opencode(name: str = "opencode") -> str:
    existing = find_in_path(name)
    if existing:
        return existing
    existing = find_local(name)
    if existing:
        return existing
    path = download_opencode(name)
    return path


def download_opencode(
    name: str = "opencode",
    version: str = "latest",
    dest: Path | None = None,
) -> str:
    import io
    import json
    import tarfile
    import urllib.request
    import zipfile

    dest = dest or binary_dir()
    dest.mkdir(parents=True, exist_ok=True)
    suffix = _platform_suffix()

    if version == "latest":
        url = "https://api.github.com/repos/anomalyco/opencode/releases/latest"
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "opencode-py"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            version = data["tag_name"]

    ext = ".zip" if sys.platform == "win32" else ".tar.gz"
    archive_url = (
        f"https://github.com/anomalyco/opencode/releases/download/{version}/opencode-{suffix}{ext}"
    )

    print(f"Downloading opencode {version} ({suffix})...")
    req = urllib.request.Request(archive_url, headers={"User-Agent": "opencode-py"})
    with urllib.request.urlopen(req) as resp:
        body = resp.read()

    if ext == ".zip":
        zf = zipfile.ZipFile(io.BytesIO(body))
        zf.extractall(str(dest))
    else:
        tf = tarfile.open(fileobj=io.BytesIO(body), mode="r:gz")
        tf.extractall(str(dest))

    final = dest / (name + (".exe" if sys.platform == "win32" else ""))
    if final.exists():
        final.chmod(final.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Downloaded opencode to {final}")
    return str(final.resolve())
