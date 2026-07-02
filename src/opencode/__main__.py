from __future__ import annotations

import sys

from opencode import opencode


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m opencode <prompt>")
        print("   or: echo 'question' | python -m opencode")
        sys.exit(1)
    prompt = " ".join(args)
    result = opencode(prompt)
    print(result)


if __name__ == "__main__":
    main()
