from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
from pathlib import Path
from typing import Optional

from opencode._errors import BinaryNotFound


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


def find_in_path(name: str = "opencode") -> Optional[str]:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    if sys.platform == "win32":
        for ext in (".cmd", ".bat", ".exe"):
            resolved = shutil.which(name + ext)
            if resolved:
                return resolved
    return None


def binary_dir() -> Path:
    return Path.home() / ".opencode" / "bin"


def find_local(name: str = "opencode") -> Optional[str]:
    candidates = [name]
    if sys.platform == "win32":
        candidates = [f"{name}.exe", f"{name}.cmd", name]
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
    dest: Optional[Path] = None,
) -> str:
    import urllib.request
    import json
    import io
    import zipfile
    import tarfile

    dest = dest or binary_dir()
    dest.mkdir(parents=True, exist_ok=True)
    suffix = _platform_suffix()

    if version == "latest":
        url = "https://api.github.com/repos/anomalyco/opencode/releases/latest"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "opencode-py"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            version = data["tag_name"]

    ext = ".zip" if sys.platform == "win32" else ".tar.gz"
    archive_url = f"https://github.com/anomalyco/opencode/releases/download/{version}/opencode-{suffix}{ext}"

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
