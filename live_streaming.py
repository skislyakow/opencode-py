import atexit
import sys

from opencode import Opencode, _opencode

_state = _opencode._opencode_state


def _cleanup() -> None:
    if _state:
        ai = _state.get("ai")
        if ai:
            ai.close()
        _state.clear()


atexit.register(_cleanup)

print("Streaming dialog with opencode (Enter — send, Ctrl+C — exit)")
print()

while True:
    try:
        prompt = input(">>> ")
    except (EOFError, KeyboardInterrupt):
        break
    if not prompt:
        continue

    # Start server and session on first call, reuse afterwards
    ai = _state.get("ai")
    if not ai:
        ai = Opencode(port=4096)
        ai.start()
        _state["ai"] = ai
        session = ai.create_session()
        _state["session"] = session
    else:
        session = _state.get("session")

    for chunk in ai.ask_stream(prompt, session=session):
        print(chunk, end="", flush=True)
    print()
