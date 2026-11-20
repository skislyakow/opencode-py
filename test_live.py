"""Test the non-LLM endpoints of the opencode SDK against a live v2 server."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from opencode import OpencodeClient, create_opencode_server

server = create_opencode_server()
print(f"Server URL: {server.url}")

client = OpencodeClient(base_url=server.url, password=server.password)

results: list[str] = []
failures = 0


def check(num: int, label: str, fn: Callable[[], Any]) -> Any:
    global failures
    try:
        result = fn()
    except Exception as e:
        failures += 1
        results.append(f"[{num:>2}] {label}: FAIL — {type(e).__name__}: {e}")
        return None
    if isinstance(result, list):
        pretty = f"list len={len(result)}"
    elif hasattr(result, "model_dump"):
        pretty = f"{type(result).__name__}"
    elif isinstance(result, dict):
        pretty = f"dict keys={list(result)[:5]}"
    else:
        pretty = repr(result)[:60]
    results.append(f"[{num:>2}] {label}: OK — {pretty}")
    return result


check(1, "Health", lambda: client.health().version)
check(2, "Location", lambda: client.location_get())
check(3, "Config", lambda: client.config_get())
check(4, "Config shells", lambda: client.config_shells())
check(5, "Models", lambda: client.model_list())
check(6, "Default model", lambda: client.model_default())
check(7, "Providers", lambda: client.provider_list())
check(8, "Agents", lambda: client.agent_list())
check(9, "Commands", lambda: client.command_list())
check(10, "Skills", lambda: client.skill_list())
check(11, "Integrations", lambda: client.integration_list())
check(12, "Credentials", lambda: client.credential_list())
check(13, "MCP servers", lambda: client.mcp_list())
check(14, "Projects", lambda: client.project_list())
location = client.location_get()
project_id = (location.project or {}).get("id", "")
check(15, "Worktrees", lambda: client.worktree_list(project_id))
check(16, "VCS", lambda: client.vcs_get())
check(17, "VCS status", lambda: client.vcs_status())
check(18, "VCS branches", lambda: client.vcs_branches())
check(19, "FS list", lambda: client.fs_list())
check(20, "FS find", lambda: client.fs_find("README"))
check(21, "FS read", lambda: len(client.fs_read("README.md")))
check(22, "Permission requests", lambda: client.permission_list())
check(23, "Forms", lambda: client.form_list())
check(24, "PTY list", lambda: client.pty_list())
check(25, "Shell list", lambda: client.shell_list())

ses = check(26, "Session create", lambda: client.session_create(title="test_live"))
sid = ses.id if ses else ""
check(27, "Session get", lambda: client.session_get(sid))
check(28, "Session list", lambda: client.session_list(limit=5))
check(29, "Session update", lambda: client.session_update(sid, title="renamed"))
check(30, "Session context", lambda: client.session_context(sid))
check(31, "Session messages", lambda: client.session_messages(sid))
check(32, "Session diff", lambda: client.session_diff(sid))
check(33, "Session permissions", lambda: client.session_permissions(sid))
check(34, "Session inbox", lambda: client.session_inbox(sid))
check(37, "Session delete", lambda: client.session_delete(sid))


def first_event() -> str:
    stream = client.event_subscribe()
    try:
        return next(line for line in stream.iter_lines() if line.startswith("data:"))[:60]
    finally:
        stream.close()


check(38, "Event stream", first_event)

print(f"\n--- Results ({len(results)} checks, {failures} failed) ---")
for r in results:
    print(r)

client.close()
server.close()
print("\nDone!")
raise SystemExit(1 if failures else 0)
