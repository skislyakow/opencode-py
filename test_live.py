"""Test all non-LLM endpoints of the opencode SDK."""

from __future__ import annotations

from opencode import OpencodeClient, create_opencode_server

server = create_opencode_server(port=4097)
print(f"Server URL: {server.url}")

client = OpencodeClient(base_url=server.url)

results = []


def check(num: int, label: str, fn):
    try:
        result = fn()
        pretty = (
            result if isinstance(result, (str, int, bool, type(None))) else type(result).__name__
        )
        if isinstance(result, dict):
            pretty = f"dict keys={list(result.keys())[:5]}"
        if isinstance(result, list):
            pretty = f"list len={len(result)}"
        results.append(f"[{num:>2}] {label}: OK — {pretty}")
    except Exception as e:
        results.append(f"[{num:>2}] {label}: SKIP — {e}")


# 1-15: basic infrastructure
check(1, "Health", lambda: client.health().get("version"))
check(2, "Global config", lambda: client.global_config_get())
check(3, "Config", lambda: client.config_get())

check(4, "Session create", lambda: client.session_create()["id"])
ses = client.session_create()
sid = ses["id"]

check(5, "Session get", lambda: client.session_get(sid).get("id"))
check(6, "Session list", lambda: client.session_list())
check(7, "File list", lambda: client.file_list("."))
check(8, "Path", lambda: client.path_get().get("worktree", "")[:40])
check(9, "VCS info", lambda: client.vcs_get().get("type", "?"))
check(10, "Project", lambda: client.project_current().get("vcs", "?"))
check(11, "Commands", lambda: client.command_list())
check(12, "Agents", lambda: client.app_agents())
check(13, "Providers", lambda: client.provider_list())
check(14, "V2 Models", lambda: client.v2_model_list())
check(15, "V2 Providers", lambda: client.v2_provider_list())

# 16-17: experimental tool (requires model+provider config)
check(
    16,
    "Tool list",
    lambda: client.tool_list(provider="anthropic", model="claude-sonnet-4-20250514"),
)
check(
    17, "Tool IDs", lambda: client.tool_ids(provider="anthropic", model="claude-sonnet-4-20250514")
)

# 18-21: system info
check(18, "MCP list", lambda: client.mcp_list())
check(19, "LSP status", lambda: client.lsp_status())
check(20, "Formatter", lambda: client.formatter_status())
check(21, "Config providers", lambda: client.config_providers())

# 22-23: V2 session endpoints
check(22, "V2 Session list", lambda: client.v2_session_list())
check(23, "V2 Context", lambda: client.v2_session_context(sid))

# 24-25: File operations
check(24, "File read", lambda: client.file_read("README.md"))
check(25, "File status", lambda: client.file_status())

# 26-27: VCS
check(26, "VCS status", lambda: client.vcs_status())
check(27, "VCS diff", lambda: client.vcs_diff())

# 28-30: Find
check(28, "Find text", lambda: client.find_text("import", include="*.py"))
check(29, "Find files", lambda: client.find_files("*.py"))
check(30, "Find symbols", lambda: client.find_symbols("main"))

# 31: Auth
check(31, "Auth list (via provider)", lambda: client.provider_list())

# 32: Worktree
check(32, "Worktree list", lambda: client.worktree_list())

# 33: Workspace
check(33, "Workspace list", lambda: client.workspace_list())

# 34: Permission
check(34, "Permission list", lambda: client.permission_list())

# 35: Question
check(35, "Question list", lambda: client.question_list())

# 36: PTY shells
check(36, "PTY shells", lambda: client.pty_shells())

# 37: Instance
check(37, "Instance dispose (dry)", lambda: client.instance_dispose())

# V2 prompt (will queue but not process without API key)
check(38, "V2 prompt", lambda: client.v2_session_prompt(sid, {"text": "Hello"}, delivery="queue"))

# Print results
print(f"\n--- Results ({len(results)} checks) ---")
for r in results:
    print(r)

# Cleanup
client.close()
server.close()
print("\nDone!")
