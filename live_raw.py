import atexit
import logging
import os
from typing import Any, cast

# Ignore OPENCODE_LOG for this demo
os.environ.pop("OPENCODE_LOG", None)

from opencode import OpencodeClient, RawResponse
from opencode._server import create_opencode_server

# Suppress verbose debug logging in demo
for name in ("httpx", "httpcore", "opencode"):
    logging.getLogger(name).setLevel(logging.WARNING)

server = create_opencode_server()
client = OpencodeClient(base_url=server.url, password=server.password)


def _cleanup() -> None:
    client.close()
    server.close()


atexit.register(_cleanup)

print("Raw response demo")
print("=" * 40)

# Normal mode
print("\n[1] Normal mode:")
h = client.health()
print(f"    {type(h).__name__}: version={h.version}")

# Raw response mode
print("\n[2] Raw response mode:")
with client.with_raw_response:
    raw = cast(RawResponse[Any], client.health())
print(f"    {type(raw).__name__}")
print(f"    .status_code = {raw.status_code}")
print(f"    .headers     = {dict(raw.headers).get('content-type')}")
print(f"    .parsed      = {type(raw.parsed).__name__}, version={raw.parsed.version}")

# Raw with JSON data
print("\n[3] Raw response — location:")
with client.with_raw_response:
    raw = cast(RawResponse[Any], client.location_get())
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed type: {type(raw.parsed).__name__}")
if raw.parsed:
    print(f"    directory: {raw.parsed.directory}")

# Raw with list response
print("\n[4] Raw response — agents (list):")
with client.with_raw_response:
    raw = cast(RawResponse[Any], client.agent_list())
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed type: {type(raw.parsed).__name__}")
print(f"    agents: {len(raw.parsed)}")

# Raw with stream (event)
print("\n[5] Raw response — event stream:")
with client.with_raw_response:
    raw = cast(RawResponse[Any], client.event_subscribe())
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed type: {type(raw.parsed).__name__}")
raw.parsed.close()

# Raw with 204
print("\n[6] Raw response — compact empty session:")
session_id = client.session_create().id or ""
with client.with_raw_response:
    raw = cast(RawResponse[Any], client.session_compact(session_id))
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed = {raw.parsed!r}")

# Headers inspection
print("\n[7] Headers inspection:")
with client.with_raw_response:
    raw = cast(RawResponse[Any], client.health())
print(f"    Server:      {raw.headers.get('server', 'N/A')}")
print(f"    Content-Type: {raw.headers.get('content-type')}")
print(f"    Date:        {raw.headers.get('date', 'N/A')}")

print("\nDone!")
