from __future__ import annotations

import sys

from opencode import opencode


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: opencode-py <prompt>")
        print("   or: python -m opencode <prompt>")
        print("   or: echo 'question' | opencode-py")
        sys.exit(1)
    prompt = " ".join(args)
    result = opencode(prompt)
    print(result)


if __name__ == "__main__":
    main()
