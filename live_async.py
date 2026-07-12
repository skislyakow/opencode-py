import asyncio
import atexit
import sys
from typing import cast

from opencode._async_opencode import AsyncOpendcode
from opencode._models import SessionMessage
from opencode._opencode import _extract_text, _resolve_model

_ai: AsyncOpendcode | None = None
_pid: int | None = None


def _cleanup() -> None:
    global _ai, _pid
    if _pid is not None:
        print(f"\n[cleanup] killing PID {_pid}...", file=sys.stderr)
        import subprocess

        subprocess.run(["taskkill", "/F", "/PID", str(_pid)], capture_output=True)
        _pid = None


atexit.register(_cleanup)


async def main() -> None:
    global _ai, _pid

    _ai = AsyncOpendcode(port=4096)
    _ai.start()
    _pid = _ai.server.pid
    print(f"[server started] PID {_pid}", file=sys.stderr)

    print("Async dialog with opencode (Enter — send, Ctrl+C — exit)")
    print()

    while True:
        loop = asyncio.get_running_loop()
        try:
            prompt = await loop.run_in_executor(None, lambda: input(">>> "))
        except (EOFError, KeyboardInterrupt):
            break
        if not prompt:
            continue

        session = await _ai.create_session()
        msg = await session.prompt(
            prompt, model=_resolve_model(model=_ai._model, config=_ai._config)
        )
        print(_extract_text(cast("SessionMessage", msg)))


if __name__ == "__main__":
    asyncio.run(main())
