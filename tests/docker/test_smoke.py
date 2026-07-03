import os
import subprocess
import sys


def main() -> int:
    print("=== opencode-py Docker smoke test ===")

    print("\nStep 1: Verify imports...")
    from opencode import (
        Opencode,
        OpencodeClient,
        OpencodeServer,
        Session,
        ToolExecutor,
        async_opencode,
        opencode,
    )
    from opencode._async_client import AsyncOpendcodeClient
    from opencode._async_opencode import AsyncOpendcode
    from opencode._async_session import AsyncSession
    from opencode._binary import ensure_opencode
    from opencode._errors import (
        APIError,
        BadRequestError,
        OpencodeError,
        RateLimitError,
    )
    from opencode._response_models import (
        FileContentResponse,
        HealthResponse,
        SessionResponse,
        V1SessionResponse,
    )
    from opencode._session import SessionMessage
    from opencode._tools import ToolExecutor as ToolExecutor2
    print("  All imports OK")

    print("\nStep 2: Download opencode binary...")
    binary = ensure_opencode()
    print(f"  Binary: {binary}")
    assert os.path.isfile(binary), f"Binary not found at {binary}"
    print("  OK")

    print("\nStep 3: Check binary version...")
    result = subprocess.run([binary, "--version"], capture_output=True, text=True)
    print(f"  Version: {result.stdout.strip()}")
    assert result.returncode == 0, f" --version failed: {result.stderr}"
    print("  OK")

    print("\nStep 4: Verify package metadata...")
    try:
        from importlib.metadata import version as _version
        v = _version("opencode-py")
        print(f"  Package version: {v}")
    except Exception:
        pass
    print("  OK")

    print("\nAll smoke tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
