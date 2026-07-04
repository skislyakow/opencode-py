"""Compare upstream openapi.json with our Python SDK expectations.

Fetches the spec from GitHub's dev branch and checks for changes
that would require updating the Python SDK.

Run periodically (or before release) to stay in sync with upstream.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, cast

UPSTREAM_URL = "https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/sdk/openapi.json"


def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode()))


def get_inline_delivery_enum(spec: dict[str, Any]) -> list[str] | None:
    """Extract the delivery enum from the v2 prompt endpoint."""
    try:
        prompt = spec["paths"]["/api/session/{sessionID}/prompt"]["post"]
        props = prompt["requestBody"]["content"]["application/json"]["schema"]["properties"]
        delivery = props["delivery"]
        return cast(list[str] | None, delivery.get("enum"))
    except Exception:
        return None


def main() -> None:
    print("Fetching upstream openapi.json from GitHub dev branch...")
    try:
        upstream = fetch_json(UPSTREAM_URL)
    except Exception as e:
        print(f"FAILED to fetch upstream: {e}")
        return

    info = upstream.get("info", {})
    print(f"Upstream info: title={info.get('title')}, version={info.get('version')}")

    # Check 1: delivery enum
    delivery = get_inline_delivery_enum(upstream)
    our_delivery = "queue"  # default in _client.py and _async_client.py

    print()
    changes_needed: list[str] = []

    if delivery:
        print(f"Delivery enum (upstream): {delivery}")
        print(f'Delivery default (our SDK): "{our_delivery}"')
        if "deferred" in delivery and our_delivery != "deferred":
            changes_needed.append(
                f"Delivery enum changed to {delivery}. "
                "Update default in: _client.py:208, _async_client.py:208, test_live.py:98\n"
                '  from `delivery: str = "queue"` to `delivery: str = "deferred"`\n'
                '  and delivery="queue" to delivery="deferred" in test_live.py'
            )
        elif "queue" in delivery:
            print("  => No change needed (still 'queue' compatible).")
    else:
        changes_needed.append("Delivery enum not found in spec — endpoint may have changed.")

    # Check 2: structured output format
    schemas = upstream.get("components", {}).get("schemas", {})
    has_structured = "OutputFormatJsonSchema" in schemas
    if not has_structured:
        # Check inline in V1 session/message endpoint
        try:
            v1 = upstream["paths"]["/session/{sessionID}/message"]["post"]
            props = v1["requestBody"]["content"]["application/json"]["schema"]["properties"]
            has_structured = "format" in props
        except Exception:
            pass
    print(f"\nStructured output (format field): {'PRESENT' if has_structured else 'MISSING'}")
    if not has_structured:
        changes_needed.append(
            "'format' field in V1 prompt endpoint missing — structured output may have changed."
        )

    # Summary
    print()
    if changes_needed:
        print("=== CHANGES NEEDED ===")
        for i, c in enumerate(changes_needed, 1):
            print(f"{i}. {c}")
    else:
        print("All clear — no SDK changes needed.")


if __name__ == "__main__":
    main()
