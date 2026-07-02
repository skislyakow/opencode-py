import os
import sys

from opencode import opencode
from opencode._binary import ensure_opencode


def main() -> int:
    print("=== opencode-py Docker smoke test ===")

    print("\nStep 1: Download opencode binary...")
    binary = ensure_opencode()
    print(f"  Binary: {binary}")
    assert os.path.isfile(binary), f"Binary not found at {binary}"

    print("\nStep 2: Test opencode() convenience function...")
    result = opencode("Say hello in exactly five words", keep=False)
    print(f"  Result: {result}")
    assert len(result) > 0, "Empty response"
    assert "hello" in result.lower(), f"Response doesn't contain 'hello': {result}"
    print("  OK")

    print("\nStep 3: Test multi-turn with keep=True...")
    r1 = opencode("My name is Alice", keep=True)
    print(f"  Turn 1: {r1}")
    assert len(r1) > 0
    r2 = opencode("What is my name?", keep=True)
    print(f"  Turn 2: {r2}")
    assert len(r2) > 0
    assert "alice" in r2.lower(), f"Doesn't remember name: {r2}"
    r3 = opencode("Bye", keep=False)
    print(f"  Turn 3: {r3}")
    print("  OK")

    print("\nAll smoke tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
