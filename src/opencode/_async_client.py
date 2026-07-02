from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import httpx

from opencode._errors import ApiError


class AsyncOpendcodeClient:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:4096",
        directory: Optional[str] = None,
        workspace: Optional[str] = None,
        timeout: float = 300.0,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.directory = directory
        self.workspace = workspace
        self._client = httpx_client or httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _merge_params(
        self,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params = dict(params or {})
        if self.directory and "directory" not in params:
            params["directory"] = self.directory
        if self.workspace and "workspace" not in params:
            params["workspace"] = self.workspace
        return params

    def _handle(self, response: httpx.Response) -> Any:
        if response.is_success:
            if response.status_code == 204:
                return None
            ct = response.headers.get("content-type", "")
            if "text/event-stream" in ct:
                return response
            if "text/" in ct:
                return response.text
            return response.json()
        body = None
        try:
            body = response.json()
        except Exception:
            body = response.text
        message = None
        if isinstance(body, dict):
            message = body.get("message") or body.get("error") or str(body)
        elif isinstance(body, str):
            message = body
        raise ApiError(
            message or f"HTTP {response.status_code}: {response.reason_phrase}",
            status=response.status_code,
            body=body,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = self._build_url(path)
        params = self._merge_params(params)
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        response = await self._client.request(method, url, params=params, json=json_body, headers=hdrs)
        return self._handle(response)

    async def _request_stream(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        url = self._build_url(path)
        params = self._merge_params(params)
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        request = self._client.build_request(method, url, params=params, json=json_body, headers=hdrs)
        return await self._client.send(request, stream=True)

    # ------------------------------------------------------------------
    # Global
    # ------------------------------------------------------------------

    async def health(self) -> Any:
        return await self._request("GET", "/global/health")

    async def global_event(self) -> httpx.Response:
        return await self._request_stream("GET", "/global/event")

    async def global_dispose(self) -> Any:
        return await self._request("POST", "/global/dispose")

    async def global_upgrade(self, target: Optional[str] = None) -> Any:
        return await self._request("POST", "/global/upgrade", json_body={"target": target})

    async def global_config_get(self) -> Any:
        return await self._request("GET", "/global/config")

    async def global_config_update(self, config: Any) -> Any:
        return await self._request("PATCH", "/global/config", json_body={"config": config})

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    async def config_get(self, **kwargs) -> Any:
        return await self._request("GET", "/config", params=kwargs)

    async def config_update(self, config: Any, **kwargs) -> Any:
        return await self._request("PATCH", "/config", json_body={"config": config}, params=kwargs)

    async def config_providers(self, **kwargs) -> Any:
        return await self._request("GET", "/config/providers", params=kwargs)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def session_create(self, **kwargs) -> Any:
        return await self._request("POST", "/session", json_body=kwargs or None)

    async def session_get(self, session_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}")

    async def session_list(self, **kwargs) -> Any:
        return await self._request("GET", "/session", params=kwargs)

    async def session_delete(self, session_id: str) -> Any:
        return await self._request("DELETE", f"/session/{session_id}")

    async def session_update(self, session_id: str, **kwargs) -> Any:
        return await self._request("PUT", f"/session/{session_id}", json_body=kwargs or None)

    async def session_messages(self, session_id: str, **kwargs) -> Any:
        return await self._request("GET", f"/session/{session_id}/message", params=kwargs)

    async def session_message(self, session_id: str, message_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}/message/{message_id}")

    async def session_fork(self, session_id: str, **kwargs) -> Any:
        return await self._request("POST", f"/session/{session_id}/fork", json_body=kwargs or None)

    async def session_abort(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/abort")

    async def session_init(self, session_id: str, **kwargs) -> Any:
        return await self._request("POST", f"/session/{session_id}/init", json_body=kwargs or None)

    async def session_summarize(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/summarize")

    async def session_todo(self, session_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}/todo")

    async def session_children(self, session_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}/child")

    async def session_diff(self, session_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}/diff")

    async def session_share(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/share")

    async def session_unshare(self, session_id: str) -> Any:
        return await self._request("DELETE", f"/session/{session_id}/share")

    async def session_revert(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/revert")

    async def session_unrevert(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/unrevert")

    async def session_command(self, session_id: str, command: str, **kwargs) -> Any:
        return await self._request("POST", f"/session/{session_id}/command", json_body={"command": command, **kwargs})

    async def session_shell(self, session_id: str, command: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/shell", json_body={"command": command})

    # ------------------------------------------------------------------
    # V2 Session
    # ------------------------------------------------------------------

    async def v2_session_list(self, **kwargs) -> Any:
        return await self._request("GET", "/api/session", params=kwargs)

    async def session_send(self, session_id: str, body: Any) -> Any:
        return await self._request("POST", f"/session/{session_id}/message", json_body=body)

    async def v2_session_prompt(self, session_id: str, prompt: Any, *, delivery: str = "queue", **kwargs) -> Any:
        body: Dict[str, Any] = {"prompt": prompt, "delivery": delivery, **kwargs}
        return await self._request("POST", f"/api/session/{session_id}/prompt", json_body=body)

    async def v2_session_wait(self, session_id: str) -> Any:
        return await self._request("POST", f"/api/session/{session_id}/wait")

    async def v2_session_context(self, session_id: str, **kwargs) -> Any:
        return await self._request("GET", f"/api/session/{session_id}/context", params=kwargs)

    async def v2_session_messages(self, session_id: str, **kwargs) -> Any:
        return await self._request("GET", f"/api/session/{session_id}/message", params=kwargs)

    async def v2_session_compact(self, session_id: str) -> Any:
        return await self._request("POST", f"/api/session/{session_id}/compact")

    async def v2_model_list(self, **kwargs) -> Any:
        return await self._request("GET", "/api/model", params=kwargs)

    async def v2_provider_list(self, **kwargs) -> Any:
        return await self._request("GET", "/api/provider", params=kwargs)

    async def v2_provider_get(self, provider_id: str) -> Any:
        return await self._request("GET", f"/api/provider/{provider_id}")

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def auth_set(self, provider_id: str, auth: Any) -> Any:
        return await self._request("PUT", f"/auth/{provider_id}", json_body={"auth": auth})

    async def auth_remove(self, provider_id: str) -> Any:
        return await self._request("DELETE", f"/auth/{provider_id}")

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------

    async def app_log(self, **kwargs) -> Any:
        return await self._request("POST", "/log", json_body=kwargs or None)

    async def app_agents(self, **kwargs) -> Any:
        return await self._request("GET", "/agent", params=kwargs)

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    async def file_read(self, path: str, **kwargs) -> Any:
        return await self._request("GET", "/file/content", params={"path": path, **kwargs})

    async def file_list(self, path: str, **kwargs) -> Any:
        return await self._request("GET", "/file", params={"path": path, **kwargs})

    async def file_status(self, **kwargs) -> Any:
        return await self._request("GET", "/file/status", params=kwargs)

    # ------------------------------------------------------------------
    # Find
    # ------------------------------------------------------------------

    async def find_text(self, pattern: str, **kwargs) -> Any:
        return await self._request("GET", "/find", params={"pattern": pattern, **kwargs})

    async def find_files(self, query: str, **kwargs) -> Any:
        return await self._request("GET", "/find/file", params={"query": query, **kwargs})

    async def find_symbols(self, query: str, **kwargs) -> Any:
        return await self._request("GET", "/find/symbol", params={"query": query, **kwargs})

    # ------------------------------------------------------------------
    # VCS
    # ------------------------------------------------------------------

    async def vcs_get(self, **kwargs) -> Any:
        return await self._request("GET", "/vcs", params=kwargs)

    async def vcs_status(self, **kwargs) -> Any:
        return await self._request("GET", "/vcs/status", params=kwargs)

    async def vcs_diff(self, mode: str = "git", **kwargs) -> Any:
        return await self._request("GET", "/vcs/diff", params={"mode": mode, **kwargs})

    async def vcs_diff_raw(self, **kwargs) -> Any:
        return await self._request("GET", "/vcs/diff/raw", params=kwargs)

    async def vcs_apply(self, patch: str, **kwargs) -> Any:
        return await self._request("POST", "/vcs/apply", json_body={"patch": patch, **kwargs})

    # ------------------------------------------------------------------
    # LSP / Formatter
    # ------------------------------------------------------------------

    async def lsp_status(self, **kwargs) -> Any:
        return await self._request("GET", "/lsp", params=kwargs)

    async def formatter_status(self, **kwargs) -> Any:
        return await self._request("GET", "/formatter", params=kwargs)

    # ------------------------------------------------------------------
    # Provider
    # ------------------------------------------------------------------

    async def provider_list(self, **kwargs) -> Any:
        return await self._request("GET", "/provider", params=kwargs)

    async def provider_auth(self, provider_id: str, **kwargs) -> Any:
        return await self._request("GET", f"/provider/{provider_id}/auth", params=kwargs)

    # ------------------------------------------------------------------
    # MCP
    # ------------------------------------------------------------------

    async def mcp_list(self, **kwargs) -> Any:
        return await self._request("GET", "/mcp", params=kwargs)

    async def mcp_status(self, **kwargs) -> Any:
        return await self._request("GET", "/mcp/status", params=kwargs)

    async def mcp_add(self, config: Any) -> Any:
        return await self._request("PUT", "/mcp", json_body={"config": config})

    async def mcp_connect(self, name: str, **kwargs) -> Any:
        return await self._request("POST", f"/mcp/{name}/connect", json_body=kwargs or None)

    async def mcp_disconnect(self, name: str) -> Any:
        return await self._request("DELETE", f"/mcp/{name}/connect")

    # ------------------------------------------------------------------
    # Tool
    # ------------------------------------------------------------------

    async def tool_list(self, **kwargs) -> Any:
        return await self._request("GET", "/experimental/tool", params=kwargs)

    async def tool_ids(self, **kwargs) -> Any:
        return await self._request("GET", "/experimental/tool/ids", params=kwargs)

    # ------------------------------------------------------------------
    # Permission
    # ------------------------------------------------------------------

    async def permission_list(self, **kwargs) -> Any:
        return await self._request("GET", "/permission", params=kwargs)

    async def permission_reply(self, permission_id: str, **kwargs) -> Any:
        return await self._request("POST", f"/permission/{permission_id}", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Question
    # ------------------------------------------------------------------

    async def question_list(self, **kwargs) -> Any:
        return await self._request("GET", "/question", params=kwargs)

    async def question_reply(self, question_id: str, answer: Any) -> Any:
        return await self._request("POST", f"/question/{question_id}", json_body={"answer": answer})

    async def question_reject(self, question_id: str) -> Any:
        return await self._request("DELETE", f"/question/{question_id}")

    # ------------------------------------------------------------------
    # Event (SSE)
    # ------------------------------------------------------------------

    async def event_subscribe(self, **kwargs) -> httpx.Response:
        return await self._request_stream("GET", "/event", params=kwargs)

    # ------------------------------------------------------------------
    # PTY
    # ------------------------------------------------------------------

    async def pty_list(self, **kwargs) -> Any:
        return await self._request("GET", "/pty", params=kwargs)

    async def pty_create(self, **kwargs) -> Any:
        return await self._request("POST", "/pty", json_body=kwargs or None)

    async def pty_get(self, pty_id: str) -> Any:
        return await self._request("GET", f"/pty/{pty_id}")

    async def pty_remove(self, pty_id: str) -> Any:
        return await self._request("DELETE", f"/pty/{pty_id}")

    async def pty_update(self, pty_id: str, **kwargs) -> Any:
        return await self._request("PATCH", f"/pty/{pty_id}", json_body=kwargs or None)

    async def pty_shells(self, **kwargs) -> Any:
        return await self._request("GET", "/pty/shells", params=kwargs)

    # ------------------------------------------------------------------
    # Path
    # ------------------------------------------------------------------

    async def path_get(self, **kwargs) -> Any:
        return await self._request("GET", "/path", params=kwargs)

    # ------------------------------------------------------------------
    # Instance
    # ------------------------------------------------------------------

    async def instance_dispose(self, **kwargs) -> Any:
        return await self._request("POST", "/instance/dispose", params=kwargs)

    # ------------------------------------------------------------------
    # Command
    # ------------------------------------------------------------------

    async def command_list(self, **kwargs) -> Any:
        return await self._request("GET", "/command", params=kwargs)

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    async def project_current(self, **kwargs) -> Any:
        return await self._request("GET", "/project/current", params=kwargs)

    async def project_list(self, **kwargs) -> Any:
        return await self._request("GET", "/project", params=kwargs)

    async def project_update(self, **kwargs) -> Any:
        return await self._request("PATCH", "/project", json_body=kwargs or None)

    async def project_init_git(self, **kwargs) -> Any:
        return await self._request("POST", "/project/init-git", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Worktree (experimental)
    # ------------------------------------------------------------------

    async def worktree_list(self, **kwargs) -> Any:
        return await self._request("GET", "/experimental/worktree", params=kwargs)

    async def worktree_create(self, **kwargs) -> Any:
        return await self._request("POST", "/experimental/worktree", json_body=kwargs or None)

    async def worktree_remove(self, **kwargs) -> Any:
        return await self._request("DELETE", "/experimental/worktree", params=kwargs)

    async def worktree_reset(self, **kwargs) -> Any:
        return await self._request("POST", "/experimental/worktree/reset", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Workspace (experimental)
    # ------------------------------------------------------------------

    async def workspace_list(self, **kwargs) -> Any:
        return await self._request("GET", "/experimental/workspace", params=kwargs)

    async def workspace_create(self, **kwargs) -> Any:
        return await self._request("POST", "/experimental/workspace", json_body=kwargs or None)

    async def workspace_status(self, **kwargs) -> Any:
        return await self._request("GET", "/experimental/workspace/status", params=kwargs)

    async def workspace_remove(self, workspace_id: str) -> Any:
        return await self._request("DELETE", f"/experimental/workspace/{workspace_id}")

    async def workspace_warp(self, **kwargs) -> Any:
        return await self._request("POST", "/experimental/workspace/warp", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Sync (experimental)
    # ------------------------------------------------------------------

    async def sync_start(self, **kwargs) -> Any:
        return await self._request("POST", "/experimental/sync/start", json_body=kwargs or None)

    async def sync_steal(self, **kwargs) -> Any:
        return await self._request("POST", "/experimental/sync/steal", json_body=kwargs or None)

    async def sync_replay(self, session_id: str) -> Any:
        return await self._request("POST", f"/experimental/sync/replay/{session_id}")

    async def sync_history(self, session_id: str) -> Any:
        return await self._request("GET", f"/experimental/sync/history/{session_id}")

    # ------------------------------------------------------------------
    # TUI
    # ------------------------------------------------------------------

    async def tui_submit_prompt(self, **kwargs) -> Any:
        return await self._request("POST", "/tui/submit", json_body=kwargs or None)

    async def tui_append_prompt(self, **kwargs) -> Any:
        return await self._request("POST", "/tui/append", json_body=kwargs or None)

    async def tui_clear_prompt(self) -> Any:
        return await self._request("POST", "/tui/clear")

    async def tui_execute_command(self, **kwargs) -> Any:
        return await self._request("POST", "/tui/command", json_body=kwargs or None)

    async def tui_show_toast(self, **kwargs) -> Any:
        return await self._request("POST", "/tui/toast", json_body=kwargs or None)

    async def tui_open_sessions(self) -> Any:
        return await self._request("POST", "/tui/sessions")

    async def tui_open_models(self) -> Any:
        return await self._request("POST", "/tui/models")

    async def tui_open_themes(self) -> Any:
        return await self._request("POST", "/tui/themes")

    async def tui_open_help(self) -> Any:
        return await self._request("POST", "/tui/help")

    async def tui_publish(self, **kwargs) -> Any:
        return await self._request("POST", "/tui/publish", json_body=kwargs or None)

    async def tui_control_response(self, **kwargs) -> Any:
        return await self._request("POST", "/tui/control/response", json_body=kwargs or None)

    async def tui_control_next(self, session_id: str) -> Any:
        return await self._request("POST", f"/tui/control/next/{session_id}")

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpendcodeClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
