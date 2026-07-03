import atexit

from opencode import _opencode, opencode

_state = _opencode._opencode_state


def _cleanup() -> None:
    if _state:
        ai = _state.get("ai")
        if ai:
            ai.close()
        _state.clear()


atexit.register(_cleanup)

print("Dialog with opencode (Enter — send, Ctrl+C — exit)")
print()

while True:
    try:
        prompt = input(">>> ")
    except (EOFError, KeyboardInterrupt):
        break
    if not prompt:
        continue
    result = opencode(prompt, keep=True)
    print(result)
