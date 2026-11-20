"""Check that every endpoint the SDK calls exists in an opencode OpenAPI spec.

Usage:
    python scripts/check-upstream.py                 # spec of the local `opencode` binary
    python scripts/check-upstream.py --spec FILE|URL # e.g. a saved /openapi.json

Without ``--spec`` an ``opencode serve`` is started and its ``/openapi.json``
is checked. Exits non-zero when the SDK uses a path/method the spec lacks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

CLIENT = Path(__file__).resolve().parent.parent / "src" / "opencode" / "_client.py"
CALL = re.compile(r'_request(?:_stream)?\(\s*"(GET|POST|PUT|PATCH|DELETE)",\s*f?"(/[^"]*)"')


def local_spec() -> dict[str, Any]:
    from opencode import OpencodeClient, create_opencode_server

    server = create_opencode_server()
    client = OpencodeClient(base_url=server.url, password=server.password)
    try:
        spec: dict[str, Any] = client._client.get(
            f"{server.url}/openapi.json", auth=client._auth
        ).json()
        return spec
    finally:
        client.close()
        server.close()


def load_spec(source: str | None) -> dict[str, Any]:
    if source is None:
        return local_spec()
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=15) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
            return data
    loaded: dict[str, Any] = json.loads(Path(source).read_text())
    return loaded


def normalize(path: str) -> str:
    """``/api/session/{session_id}`` and ``/api/session/{sessionID}`` -> ``/api/session/{}``."""
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return path.replace("/*", "/{}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", help="spec file path or URL (default: local opencode)")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    info = spec.get("info", {})
    print(f"Spec: {args.spec or 'local opencode serve'}")
    print(f"  title={info.get('title')} version={info.get('version')}")

    available = {
        (method.upper(), normalize(path))
        for path, ops in spec.get("paths", {}).items()
        for method in ops
    }
    used = sorted({(m, normalize(p)) for m, p in CALL.findall(CLIENT.read_text())})
    missing = [(m, p) for m, p in used if (m, p) not in available]

    print(f"  SDK calls {len(used)} endpoints; spec has {len(available)} operations")
    if missing:
        print("\n=== MISSING FROM SPEC (SDK update needed) ===")
        for method, path in missing:
            print(f"  {method} {path}")
        return 1
    print("All clear — every SDK endpoint exists in the spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
