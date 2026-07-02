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

print("Диалог с opencode (Enter — отправить, Ctrl+C — выход)")
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
