from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any

from opencode._binary import ensure_opencode
from opencode._errors import ServerStartupTimeoutError
from opencode._process import stop


class OpencodeServer:
    def __init__(self, proc: subprocess.Popen[bytes], url: str, binary: str):
        self._proc = proc
        self.url = url
        self.binary = binary

    def close(self) -> None:
        stop(self._proc)

    @property
    def pid(self) -> int | None:
        return self._proc.pid

    @property
    def running(self) -> bool:
        return self._proc.poll() is None


def create_opencode_server(
    *,
    hostname: str = "127.0.0.1",
    port: int = 4096,
    timeout: float = 30.0,
    config: dict[str, Any] | None = None,
    opencode_binary: str | None = None,
) -> OpencodeServer:
    binary = opencode_binary or ensure_opencode()

    args = [binary, "serve", f"--hostname={hostname}", f"--port={port}"]
    env = os.environ.copy()
    if config:
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    start_time = time.monotonic()
    output = ""
    url: str | None = None

    while time.monotonic() - start_time < timeout:
        line = proc.stdout.readline() if proc.stdout else b""
        if not line:
            if proc.poll() is not None:
                stderr_output = ""
                if proc.stderr:
                    stderr_output = proc.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"opencode exited with code {proc.returncode}"
                    f"\nstdout: {output}"
                    f"\nstderr: {stderr_output}"
                )
            time.sleep(0.05)
            continue

        decoded = line.decode("utf-8", errors="replace").strip()
        output += decoded + "\n"

        m = re.search(r"on\s+(https?://[^\s]+)", decoded)
        if m:
            url = m.group(1)
            break

    if not url:
        stop(proc)
        stderr_output = ""
        if proc.stderr:
            try:
                stderr_output = proc.stderr.read().decode("utf-8", errors="replace")
            except Exception:
                pass
        raise ServerStartupTimeoutError(
            f"Timeout waiting for opencode server after {timeout}s"
            f"\nstdout: {output}"
            f"\nstderr: {stderr_output}",
        )

    return OpencodeServer(proc, url, binary)
