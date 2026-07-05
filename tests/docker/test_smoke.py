import sys


def main() -> int:
    print("=== opencode-py Docker smoke test ===")
    sys.stdout.flush()

    print("\nStep 1: Verify imports...")
    from opencode import (  # noqa: F401
        Opencode,
        OpencodeClient,
        OpencodeServer,
        Session,
        ToolExecutor,
        async_opencode,
        opencode,
    )
    from opencode._async_client import AsyncOpendcodeClient  # noqa: F401
    from opencode._async_opencode import AsyncOpendcode  # noqa: F401
    from opencode._async_session import AsyncSession  # noqa: F401
    from opencode._errors import (  # noqa: F401
        APIError,
        BadRequestError,
        OpencodeError,
        RateLimitError,
    )
    from opencode._models import SessionMessage  # noqa: F401
    from opencode._response_models import (  # noqa: F401
        FileContentResponse,
        HealthResponse,
        SessionResponse,
        V1SessionResponse,
    )
    from opencode._tools import ToolExecutor as ToolExecutor2  # noqa: F401

    print("  All imports OK")

    print("\nStep 2: Verify package metadata...")
    from importlib.metadata import version

    v = version("opencode-py")
    print(f"  Package version: {v}")
    print("  OK")

    print("\nAll smoke tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
