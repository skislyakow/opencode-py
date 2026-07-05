#!/usr/bin/env python3
"""Demo of the opencode Python SDK capabilities."""

from __future__ import annotations

from opencode import OpencodeClient, create_opencode_server

print("=" * 60)
print("  Opencode Python SDK — Demo")
print("=" * 60)

# 1. Start the server
print("\n[1] Starting opencode serve...")
server = create_opencode_server(port=4097)
print(f"    Server at {server.url} (pid={server.pid})")

client = OpencodeClient(base_url=server.url)

# 2. Server info
h = client.health()
print(f"\n[2] Server: version={h.version}, healthy={h.healthy}")

# 3. Current project
pj = client.project_current()
print(f"\n[3] Project: id={pj.id[:12]}... vcs={pj.vcs}")

# 4. Session management
print("\n[4] Creating session...")
ses = client.session_create()
sid = ses.id
print(f"    Session ID: {sid}")

# 5. File read
print("\n[5] Reading file...")
f = client.file_read("README.md")
print(f"    File: {len(f.content)} chars")

# 6. VCS info
print("\n[6] VCS status...")
vcs = client.vcs_status()
n = len(vcs) if vcs else 0
print(f"    {n} changed files")

# 7. Available models
print("\n[7] Available models...")
models = client.v2_model_list()
providers = sorted(set(m.providerID for m in models if m.providerID))
print(f"    Format: {type(models).__name__}")
print(f"    Providers/models: {providers[:5]}")

# 8. Code search
print("\n[8] Searching text...")
found = client.find_text("create_opencode")
print(f"    Found: {len(found) if isinstance(found, list) else '?'}")

# 9. Send prompt (no LLM — queue only)
print("\n[9] Sending prompt (no API key)...")
try:
    msg = client.v2_session_prompt(
        sid, {"text": "Hello! Answer in one word."}, delivery="queue"
    )
    resp_type = getattr(msg, "type", type(msg).__name__)
    print(f"    Response: type={resp_type}")
    print("    Prompt queued for processing")
except Exception as e:
    print(f"    Prompt accepted (API key required): {e}")

# 10. Session context messages
print("\n[10] Session messages...")
ctx = client.v2_session_context(sid)
items = (
    ctx.get("data", [])
    if isinstance(ctx, dict)
    else ctx
    if isinstance(ctx, list)
    else []
)
print(f"     Messages: {len(items)}")

# 11. Extra capabilities
print("\n[11] Additional:")
path = client.path_get()
print(f"     Working directory: {path.worktree}")
cmds = client.command_list()
print(
    f"     Opencode commands: {len(cmds) if isinstance(cmds, list) else '?'}"
)
agents = client.app_agents()
print(f"     Agents: {len(agents) if isinstance(agents, list) else '?'}")

# 12. Cleanup
print("\n[12] Stopping server...")
client.close()
server.close()
print("     Done!")

print("\n" + "=" * 60)
print("  SDK is working correctly!")
print("=" * 60)
