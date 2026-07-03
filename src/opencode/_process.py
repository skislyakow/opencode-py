from __future__ import annotations

import signal
import subprocess
import sys


def stop(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32" and proc.pid:
        try:
            subprocess.run(
                ["taskkill", "/pid", str(proc.pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
            )
            return
        except Exception:
            pass
    try:
        proc.send_signal(signal.SIGTERM)
    except Exception:
        pass
