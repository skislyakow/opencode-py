#!/usr/bin/env python3
"""Demo of the opencode Python SDK capabilities (opencode v2 API)."""

from __future__ import annotations

from opencode import OpencodeClient, create_opencode_server

print("=" * 60)
print("  Opencode Python SDK — Demo")
print("=" * 60)

# 1. Start the server (random port + password)
print("\n[1] Starting opencode serve...")
server = create_opencode_server()
print(f"    Server at {server.url} (pid={server.pid})")

client = OpencodeClient(base_url=server.url, password=server.password)

# 2. Server info
info = client.health()
print(f"\n[2] Server: version={info.version}, pid={info.pid}")

# 3. Current location / project
loc = client.location_get()
print(f"\n[3] Directory: {loc.directory}, project={(loc.project or {}).get('id', '')[:12]}...")

# 4. Session management
print("\n[4] Creating session...")
sid = client.session_create(title="demo").id or ""
print(f"    Session ID: {sid}")

# 5. File read
print("\n[5] Reading file...")
content = client.fs_read("README.md")
print(f"    File: {len(content)} chars")

# 6. VCS info
print("\n[6] VCS status...")
print(f"    {len(client.vcs_status())} changed files")

# 7. Available models
print("\n[7] Available models...")
models = client.model_list()
providers = sorted({m.providerID for m in models if m.providerID})
print(f"    Providers: {providers[:5]} ({len(models)} models)")

# 8. File search
print("\n[8] Finding files...")
print(f"    Found: {len(client.fs_find('README'))}")

# 9. Queue a prompt (returns immediately; processing needs a model)
print("\n[9] Queueing prompt...")
sent = client.session_prompt(sid, "Hello! Answer in one word.")
print(f"    Queued user message {sent.id}")
client.session_interrupt(sid)

# 10. Session context messages
print("\n[10] Session messages...")
print(f"     Messages: {len(client.session_context(sid))}")

# 11. Extra capabilities
print("\n[11] Additional:")
print(f"     Commands: {len(client.command_list())}")
print(f"     Agents: {len(client.agent_list())}")
print(f"     Skills: {len(client.skill_list())}")

# 12. Cleanup
print("\n[12] Stopping server...")
client.session_delete(sid)
client.close()
server.close()
print("     Done!")

print("\n" + "=" * 60)
print("  SDK is working correctly!")
print("=" * 60)
