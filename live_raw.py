import atexit
import logging
import os

# Ignore OPENCODE_LOG for this demo
os.environ.pop("OPENCODE_LOG", None)

from opencode import OpencodeClient
from opencode._server import create_opencode_server

# Suppress verbose debug logging in demo
for name in ("httpx", "httpcore", "opencode"):
    logging.getLogger(name).setLevel(logging.WARNING)

server = create_opencode_server(port=4096)
client = OpencodeClient(base_url=server.url)


def _cleanup() -> None:
    client.close()
    server.close()


atexit.register(_cleanup)

print("Raw response demo")
print("=" * 40)

# Normal mode
print("\n[1] Normal mode:")
h = client.health()
print(f"    {type(h).__name__}: ok={h.ok}")

# Raw response mode
print("\n[2] Raw response mode:")
with client.with_raw_response:
    raw = client.health()
print(f"    {type(raw).__name__}")
print(f"    .status_code = {raw.status_code}")
print(f"    .headers     = {dict(raw.headers).get('content-type')}")
print(f"    .parsed      = {type(raw.parsed).__name__}, ok={raw.parsed.ok}")

# Raw with JSON data
print("\n[3] Raw response — project/current:")
with client.with_raw_response:
    raw = client.project_current()
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed type: {type(raw.parsed).__name__}")
if raw.parsed:
    print(f"    project id: {raw.parsed.id[:20]}...")

# Raw with list response
print("\n[4] Raw response — agents (list):")
with client.with_raw_response:
    raw = client.app_agents()
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed type: {type(raw.parsed).__name__}")
print(f"    agents: {len(raw.parsed)}")

# Raw with stream (event)
print("\n[5] Raw response — event stream:")
with client.with_raw_response:
    raw = client.global_event()
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed type: {type(raw.parsed).__name__}")
raw.parsed.close()

# Raw with 204
print("\n[6] Raw response — 204 (clear prompt):")
with client.with_raw_response:
    raw = client.tui_clear_prompt()
print(f"    {type(raw).__name__}, status={raw.status_code}")
print(f"    .parsed = {raw.parsed!r}")

# Headers inspection
print("\n[7] Headers inspection:")
with client.with_raw_response:
    raw = client.health()
print(f"    Server:      {raw.headers.get('server', 'N/A')}")
print(f"    Content-Type: {raw.headers.get('content-type')}")
print(f"    Date:        {raw.headers.get('date', 'N/A')}")

print("\nDone!")
