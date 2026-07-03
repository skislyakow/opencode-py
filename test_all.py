"""
Manual test script — run each section after committing changes.

Usage:
    python test_all.py          # run all tests
    python test_all.py --unit   # only unit tests
    python test_all.py --live   # live integration (requires opencode binary)
"""

import subprocess
import sys


def run(cmd, label):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print(f"  FAILED (exit code {result.returncode})")
    else:
        print("  OK")
    return result.returncode


def main():
    tests = []

    if "--unit" in sys.argv or not any(a.startswith("--") for a in sys.argv[1:]):
        tests.append(("python -m pytest tests/ -v", "Unit tests (17 tests)"))

    if "--live" in sys.argv or not any(a.startswith("--") for a in sys.argv[1:]):
        tests.extend(
            [
                (
                    "python -c \"from opencode import opencode; r = opencode('say hi', keep=True); print('R1:', r); r2 = opencode('what did you say?', keep=True); print('R2:', r2); r3 = opencode('translate to russian', keep=False); print('R3:', r3)\"",
                    "Keep mode (multi-turn)",
                ),
                (
                    "python -c \"from opencode import opencode; r = opencode('create file _test_auto.txt with content AutoTest', auto_tools=True, keep=True); print('R:', r)\"",
                    "Auto-tools (file creation)",
                ),
            ]
        )

    failed = 0
    for cmd, label in tests:
        rc = run(cmd, label)
        if rc != 0:
            failed += 1

    print(f"\n{'=' * 60}")
    if failed:
        print(f"  {failed} test(s) FAILED")
    else:
        print("  All tests passed!")
    print(f"{'=' * 60}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
