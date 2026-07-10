"""Demo: ephemeral port selection — two servers, auto ports, cleanup on exit."""

import atexit
import time

from opencode import create_opencode_server, OpencodeClient

servers = []


def cleanup() -> None:
    for s in servers:
        if s.running:
            print(f"  Closing {s.url}...")
            s.close()
            print(f"  {s.url} closed")
    print("All servers stopped")


atexit.register(cleanup)

print("Starting server A (auto-port)...")
s1 = create_opencode_server()
servers.append(s1)
print(f"  Server A -> {s1.url}")

print("Starting server B (auto-port)...")
s2 = create_opencode_server()
servers.append(s2)
print(f"  Server B -> {s2.url}")

if s1.url == s2.url:
    print("  ERROR: both got the same port!")
else:
    print("  OK: ports differ")

print(f"\nBoth running: {s1.running and s2.running}")

print("\nHealth check A:")
c1 = OpencodeClient(base_url=s1.url)
print(f"  {c1.health()}")

print("Health check B:")
c2 = OpencodeClient(base_url=s2.url)
print(f"  {c2.health()}")

c1.close()
c2.close()

print("\nExiting — cleanup will close both servers...")
