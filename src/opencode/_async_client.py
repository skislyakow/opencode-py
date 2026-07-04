from __future__ import annotations

import asyncio
import random
from typing import Any, TypeVar, cast

import httpx

from opencode._errors import (
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    OpencodeError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from opencode._logs import logger
from opencode._response_models import (
    AgentResponse,
    CommandResponse,
    ConfigProviderResponse,
    ConfigResponse,
    FileContentResponse,
    FileNode,
    FileStatus,
    FindMatch,
    FormatterStatusResponse,
    HealthResponse,
    LSPStatusResponse,
    MCPStatusResponse,
    ModelV2Info,
    PathResponse,
    PermissionRequestResponse,
    ProjectResponse,
    ProviderAuthListResponse,
    ProviderResponse,
    ProviderV2Info,
    PtyResponse,
    PtyShell,
    QuestionRequestResponse,
    SessionResponse,
    SnapshotFileDiffResponse,
    Symbol,
    TodoResponse,
    ToolIDs,
    ToolList,
    V1SessionResponse,
    VcsFileDiff,
    VcsFileStatus,
    VcsInfo,
    WorkspaceResponse,
    WorktreeResponse,
)
from opencode._types import NOT_GIVEN, NotGiven, is_given

_T = TypeVar("_T")

DEFAULT_MAX_RETRIES = 2
INITIAL_RETRY_DELAY = 0.5
MAX_RETRY_DELAY = 8.0
RETRYABLE_STATUS_CODES = {408, 409, 429}


class AsyncOpendcodeClient:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:4096",
        directory: str | None = None,
        workspace: str | None = None,
        timeout: float = 300.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        httpx_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.directory = directory
        self.workspace = workspace
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx_client or httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _merge_params(
        self,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = dict(params or {})
        if self.directory and "directory" not in params:
            params["directory"] = self.directory
        if self.workspace and "workspace" not in params:
            params["workspace"] = self.workspace
        return params

    @staticmethod
    def _should_retry(response: httpx.Response | None = None, exc: Exception | None = None) -> bool:
        if response is not None:
            if response.status_code in RETRYABLE_STATUS_CODES or response.status_code >= 500:
                return True
        if isinstance(exc, httpx.TimeoutException):
            return True
        return False

    @staticmethod
    def _retry_interval(attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After") or response.headers.get(
                "retry-after-ms"
            )
            if retry_after:
                try:
                    return float(retry_after) / 1000 if "ms" in retry_after else float(retry_after)
                except ValueError:
                    pass
        delay = min(INITIAL_RETRY_DELAY * pow(2.0, attempt), MAX_RETRY_DELAY)
        return delay * (1 - 0.25 * random.random())

    @staticmethod
    def _make_status_error(
        message: str,
        *,
        body: object = None,
        response: httpx.Response,
    ) -> APIStatusError:
        status = response.status_code
        if status == 400:
            return BadRequestError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status == 401:
            return AuthenticationError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status == 403:
            return PermissionDeniedError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status == 404:
            return NotFoundError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status == 409:
            return ConflictError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status == 422:
            return UnprocessableEntityError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status == 429:
            return RateLimitError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        if status >= 500:
            return InternalServerError(
                message=message,
                body=body,
                response=response,
                status_code=status,
            )
        return APIStatusError(message=message, body=body, response=response, status_code=status)

    def _construct_type(self, model_class: type[_T] | None, data: Any) -> _T | Any:
        if model_class is None:
            return data
        if isinstance(data, list):
            return [self._construct_type(model_class, item) for item in data]
        if isinstance(data, dict):
            return cast(_T, cast(Any, model_class).model_validate(data))
        if data is None:
            return None
        return data

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    def _handle(
        self,
        response: httpx.Response,
        cast_to: type[_T] | None = None,
    ) -> Any:
        if response.is_success:
            if response.status_code == 204:
                return None
            ct = response.headers.get("content-type", "")
            if "text/event-stream" in ct:
                return response
            if "text/" in ct:
                return response.text
            json_data = response.json()
            if cast_to is not None:
                return self._construct_type(cast_to, json_data)
            return json_data

        body: Any = None
        try:
            body = response.json()
        except Exception:
            body = response.text
        message = None
        if isinstance(body, dict):
            message = body.get("message") or body.get("error") or str(body)
        elif isinstance(body, str):
            message = body
        raise self._make_status_error(
            message or f"HTTP {response.status_code}: {response.reason_phrase}",
            body=body,
            response=response,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        extra_query: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
        cast_to: type[_T] | None = None,
    ) -> Any:
        url = self._build_url(path)
        params = self._merge_params(params)
        if extra_query:
            params = {**params, **extra_query}

        hdrs = {"Content-Type": "application/json", **(headers or {})}
        if extra_headers:
            hdrs = {**hdrs, **extra_headers}

        body = json_body
        if extra_body:
            if isinstance(body, dict) and isinstance(extra_body, dict):
                body = {**body, **extra_body}
            else:
                body = extra_body

        logger.debug("HTTP Request: %s %s params=%s", method, url, params)

        last_exc: httpx.TimeoutException | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(
                    method, url, params=params, json=body, headers=hdrs
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_interval(attempt)
                    logger.debug(
                        "Retry %d after timeout, sleeping %.2fs",
                        attempt + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise APITimeoutError(request=exc.request) from exc

            if not response.is_success and attempt < self._max_retries:
                if self._should_retry(response=response):
                    delay = self._retry_interval(attempt, response)
                    logger.debug(
                        "Retry %d after HTTP %d, sleeping %.2fs",
                        attempt + 1,
                        response.status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

            return self._handle(response, cast_to=cast_to)

        if last_exc:
            raise APITimeoutError(request=last_exc.request) from last_exc
        raise OpencodeError("Unexpected retry exhaustion")

    async def _request_stream(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = self._build_url(path)
        params = self._merge_params(params)
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        request = self._client.build_request(
            method, url, params=params, json=json_body, headers=hdrs
        )
        return await self._client.send(request, stream=True)

    # ------------------------------------------------------------------
    # copy / with_options
    # ------------------------------------------------------------------

    def copy(
        self,
        *,
        base_url: str | NotGiven = NOT_GIVEN,
        timeout: float | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        directory: str | None | NotGiven = NOT_GIVEN,
        workspace: str | None | NotGiven = NOT_GIVEN,
        httpx_client: httpx.AsyncClient | None | NotGiven = NOT_GIVEN,
    ) -> AsyncOpendcodeClient:
        return AsyncOpendcodeClient(
            base_url=self.base_url if is_given(base_url) else cast(str, base_url),
            timeout=self._timeout if is_given(timeout) else cast(float, timeout),
            max_retries=self._max_retries if is_given(max_retries) else cast(int, max_retries),
            directory=self.directory if is_given(directory) else cast(str, directory),
            workspace=self.workspace if is_given(workspace) else cast(str, workspace),
            httpx_client=(
                self._client if is_given(httpx_client) else cast(httpx.AsyncClient, httpx_client)
            ),
        )

    def with_options(self, **kwargs: Any) -> AsyncOpendcodeClient:
        return self.copy(**kwargs)

    # ------------------------------------------------------------------
    # Global
    # ------------------------------------------------------------------

    async def health(self) -> HealthResponse:
        return cast(
            HealthResponse,
            await self._request("GET", "/global/health", cast_to=HealthResponse),
        )

    async def global_event(self) -> httpx.Response:
        return await self._request_stream("GET", "/global/event")

    async def global_dispose(self) -> Any:
        return await self._request("POST", "/global/dispose")

    async def global_upgrade(self, target: str | None = None) -> Any:
        return await self._request("POST", "/global/upgrade", json_body={"target": target})

    async def global_config_get(self) -> Any:
        return await self._request("GET", "/global/config", cast_to=ConfigResponse)

    async def global_config_update(self, config: Any) -> Any:
        return await self._request(
            "PATCH", "/global/config", json_body={"config": config}, cast_to=ConfigResponse
        )

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    async def config_get(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/config", params=kwargs, cast_to=ConfigResponse)

    async def config_update(self, config: Any, **kwargs: Any) -> Any:
        return await self._request(
            "PATCH", "/config", json_body={"config": config}, params=kwargs, cast_to=ConfigResponse
        )

    async def config_providers(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/config/providers", params=kwargs, cast_to=ConfigProviderResponse
        )

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def session_create(self, **kwargs: Any) -> SessionResponse:
        return cast(
            SessionResponse,
            await self._request(
                "POST",
                "/session",
                json_body=kwargs or None,
                cast_to=SessionResponse,
            ),
        )

    async def session_get(self, session_id: str) -> SessionResponse:
        return cast(
            SessionResponse,
            await self._request("GET", f"/session/{session_id}", cast_to=SessionResponse),
        )

    async def session_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/session", params=kwargs)

    async def session_delete(self, session_id: str) -> Any:
        return await self._request("DELETE", f"/session/{session_id}")

    async def session_update(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request("PUT", f"/session/{session_id}", json_body=kwargs or None)

    async def session_messages(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request("GET", f"/session/{session_id}/message", params=kwargs)

    async def session_message(self, session_id: str, message_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}/message/{message_id}")

    async def session_fork(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request(
            "POST", f"/session/{session_id}/fork", json_body=kwargs or None, cast_to=SessionResponse
        )

    async def session_abort(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/abort")

    async def session_init(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request("POST", f"/session/{session_id}/init", json_body=kwargs or None)

    async def session_summarize(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/summarize")

    async def session_todo(self, session_id: str) -> Any:
        return await self._request("GET", f"/session/{session_id}/todo", cast_to=list[TodoResponse])

    async def session_children(self, session_id: str) -> Any:
        return await self._request(
            "GET", f"/session/{session_id}/child", cast_to=list[SessionResponse]
        )

    async def session_diff(self, session_id: str) -> Any:
        return await self._request(
            "GET", f"/session/{session_id}/diff", cast_to=list[SnapshotFileDiffResponse]
        )

    async def session_share(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/share")

    async def session_unshare(self, session_id: str) -> Any:
        return await self._request("DELETE", f"/session/{session_id}/share")

    async def session_revert(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/revert")

    async def session_unrevert(self, session_id: str) -> Any:
        return await self._request("POST", f"/session/{session_id}/unrevert")

    async def session_command(self, session_id: str, command: str, **kwargs: Any) -> Any:
        return await self._request(
            "POST",
            f"/session/{session_id}/command",
            json_body={"command": command, **kwargs},
        )

    async def session_shell(self, session_id: str, command: str) -> Any:
        return await self._request(
            "POST",
            f"/session/{session_id}/shell",
            json_body={"command": command},
        )

    # ------------------------------------------------------------------
    # V2 Session
    # ------------------------------------------------------------------

    async def v2_session_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/api/session", params=kwargs)

    async def session_send(self, session_id: str, body: Any) -> V1SessionResponse:
        return cast(
            V1SessionResponse,
            await self._request(
                "POST",
                f"/session/{session_id}/message",
                json_body=body,
                cast_to=V1SessionResponse,
            ),
        )

    async def v2_session_prompt(
        self,
        session_id: str,
        prompt: Any,
        *,
        delivery: str = "queue",
        **kwargs: Any,
    ) -> Any:
        body: dict[str, Any] = {
            "prompt": prompt,
            "delivery": delivery,
            **kwargs,
        }
        return await self._request(
            "POST", f"/api/session/{session_id}/prompt", json_body=body, cast_to=V1SessionResponse
        )

    async def v2_session_wait(self, session_id: str) -> Any:
        return await self._request("POST", f"/api/session/{session_id}/wait")

    async def v2_session_context(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request("GET", f"/api/session/{session_id}/context", params=kwargs)

    async def v2_session_messages(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request("GET", f"/api/session/{session_id}/message", params=kwargs)

    async def v2_session_compact(self, session_id: str) -> Any:
        return await self._request("POST", f"/api/session/{session_id}/compact")

    async def v2_model_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/api/model", params=kwargs, cast_to=list[ModelV2Info])

    async def v2_provider_list(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/api/provider", params=kwargs, cast_to=list[ProviderV2Info]
        )

    async def v2_provider_get(self, provider_id: str) -> Any:
        return await self._request("GET", f"/api/provider/{provider_id}", cast_to=ProviderV2Info)

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

    async def app_log(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/log", json_body=kwargs or None)

    async def app_agents(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/agent", params=kwargs, cast_to=list[AgentResponse])

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    async def file_read(self, path: str, **kwargs: Any) -> FileContentResponse:
        return cast(
            FileContentResponse,
            await self._request(
                "GET",
                "/file/content",
                params={"path": path, **kwargs},
                cast_to=FileContentResponse,
            ),
        )

    async def file_list(self, path: str, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/file", params={"path": path, **kwargs}, cast_to=list[FileNode]
        )

    async def file_status(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/file/status", params=kwargs, cast_to=list[FileStatus])

    # ------------------------------------------------------------------
    # Find
    # ------------------------------------------------------------------

    async def find_text(self, pattern: str, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/find", params={"pattern": pattern, **kwargs}, cast_to=list[FindMatch]
        )

    async def find_files(self, query: str, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/find/file", params={"query": query, **kwargs}, cast_to=list[str]
        )

    async def find_symbols(self, query: str, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/find/symbol", params={"query": query, **kwargs}, cast_to=list[Symbol]
        )

    # ------------------------------------------------------------------
    # VCS
    # ------------------------------------------------------------------

    async def vcs_get(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/vcs", params=kwargs, cast_to=VcsInfo)

    async def vcs_status(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/vcs/status", params=kwargs, cast_to=list[VcsFileStatus])

    async def vcs_diff(self, mode: str = "git", **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/vcs/diff", params={"mode": mode, **kwargs}, cast_to=list[VcsFileDiff]
        )

    async def vcs_diff_raw(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/vcs/diff/raw", params=kwargs)

    async def vcs_apply(self, patch: str, **kwargs: Any) -> Any:
        return await self._request("POST", "/vcs/apply", json_body={"patch": patch, **kwargs})

    # ------------------------------------------------------------------
    # LSP / Formatter
    # ------------------------------------------------------------------

    async def lsp_status(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/lsp", params=kwargs, cast_to=list[LSPStatusResponse])

    async def formatter_status(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/formatter", params=kwargs, cast_to=list[FormatterStatusResponse]
        )

    # ------------------------------------------------------------------
    # Provider
    # ------------------------------------------------------------------

    async def provider_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/provider", params=kwargs, cast_to=ProviderResponse)

    async def provider_auth(self, provider_id: str, **kwargs: Any) -> Any:
        return await self._request(
            "GET", f"/provider/{provider_id}/auth", params=kwargs, cast_to=ProviderAuthListResponse
        )

    # ------------------------------------------------------------------
    # MCP
    # ------------------------------------------------------------------

    async def mcp_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/mcp", params=kwargs, cast_to=MCPStatusResponse)

    async def mcp_status(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/mcp/status", params=kwargs, cast_to=MCPStatusResponse)

    async def mcp_add(self, config: Any) -> Any:
        return await self._request(
            "PUT", "/mcp", json_body={"config": config}, cast_to=MCPStatusResponse
        )

    async def mcp_connect(self, name: str, **kwargs: Any) -> Any:
        return await self._request("POST", f"/mcp/{name}/connect", json_body=kwargs or None)

    async def mcp_disconnect(self, name: str) -> Any:
        return await self._request("DELETE", f"/mcp/{name}/connect")

    # ------------------------------------------------------------------
    # Tool
    # ------------------------------------------------------------------

    async def tool_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/experimental/tool", params=kwargs, cast_to=ToolList)

    async def tool_ids(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/experimental/tool/ids", params=kwargs, cast_to=ToolIDs)

    # ------------------------------------------------------------------
    # Permission
    # ------------------------------------------------------------------

    async def permission_list(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/permission", params=kwargs, cast_to=list[PermissionRequestResponse]
        )

    async def permission_reply(self, permission_id: str, **kwargs: Any) -> Any:
        return await self._request("POST", f"/permission/{permission_id}", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Question
    # ------------------------------------------------------------------

    async def question_list(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/question", params=kwargs, cast_to=list[QuestionRequestResponse]
        )

    async def question_reply(self, question_id: str, answer: Any) -> Any:
        return await self._request("POST", f"/question/{question_id}", json_body={"answer": answer})

    async def question_reject(self, question_id: str) -> Any:
        return await self._request("DELETE", f"/question/{question_id}")

    # ------------------------------------------------------------------
    # Event (SSE)
    # ------------------------------------------------------------------

    async def event_subscribe(self, **kwargs: Any) -> httpx.Response:
        return await self._request_stream("GET", "/event", params=kwargs)

    # ------------------------------------------------------------------
    # PTY
    # ------------------------------------------------------------------

    async def pty_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/pty", params=kwargs, cast_to=list[PtyResponse])

    async def pty_create(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/pty", json_body=kwargs or None, cast_to=PtyResponse)

    async def pty_get(self, pty_id: str) -> Any:
        return await self._request("GET", f"/pty/{pty_id}", cast_to=PtyResponse)

    async def pty_remove(self, pty_id: str) -> Any:
        return await self._request("DELETE", f"/pty/{pty_id}")

    async def pty_update(self, pty_id: str, **kwargs: Any) -> Any:
        return await self._request(
            "PATCH", f"/pty/{pty_id}", json_body=kwargs or None, cast_to=PtyResponse
        )

    async def pty_shells(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/pty/shells", params=kwargs, cast_to=list[PtyShell])

    # ------------------------------------------------------------------
    # Path
    # ------------------------------------------------------------------

    async def path_get(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/path", params=kwargs, cast_to=PathResponse)

    # ------------------------------------------------------------------
    # Instance
    # ------------------------------------------------------------------

    async def instance_dispose(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/instance/dispose", params=kwargs)

    # ------------------------------------------------------------------
    # Command
    # ------------------------------------------------------------------

    async def command_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/command", params=kwargs, cast_to=list[CommandResponse])

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    async def project_current(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/project/current", params=kwargs, cast_to=ProjectResponse
        )

    async def project_list(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/project", params=kwargs, cast_to=list[ProjectResponse])

    async def project_update(self, **kwargs: Any) -> Any:
        return await self._request(
            "PATCH", "/project", json_body=kwargs or None, cast_to=ProjectResponse
        )

    async def project_init_git(self, **kwargs: Any) -> Any:
        return await self._request(
            "POST", "/project/init-git", json_body=kwargs or None, cast_to=ProjectResponse
        )

    # ------------------------------------------------------------------
    # Worktree (experimental)
    # ------------------------------------------------------------------

    async def worktree_list(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/experimental/worktree", params=kwargs, cast_to=list[str]
        )

    async def worktree_create(self, **kwargs: Any) -> Any:
        return await self._request(
            "POST", "/experimental/worktree", json_body=kwargs or None, cast_to=WorktreeResponse
        )

    async def worktree_remove(self, **kwargs: Any) -> Any:
        return await self._request("DELETE", "/experimental/worktree", params=kwargs)

    async def worktree_reset(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/experimental/worktree/reset", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Workspace (experimental)
    # ------------------------------------------------------------------

    async def workspace_list(self, **kwargs: Any) -> Any:
        return await self._request(
            "GET", "/experimental/workspace", params=kwargs, cast_to=list[WorkspaceResponse]
        )

    async def workspace_create(self, **kwargs: Any) -> Any:
        return await self._request(
            "POST", "/experimental/workspace", json_body=kwargs or None, cast_to=WorkspaceResponse
        )

    async def workspace_status(self, **kwargs: Any) -> Any:
        return await self._request("GET", "/experimental/workspace/status", params=kwargs)

    async def workspace_remove(self, workspace_id: str) -> Any:
        return await self._request(
            "DELETE", f"/experimental/workspace/{workspace_id}", cast_to=WorkspaceResponse
        )

    async def workspace_warp(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/experimental/workspace/warp", json_body=kwargs or None)

    # ------------------------------------------------------------------
    # Sync (experimental)
    # ------------------------------------------------------------------

    async def sync_start(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/experimental/sync/start", json_body=kwargs or None)

    async def sync_steal(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/experimental/sync/steal", json_body=kwargs or None)

    async def sync_replay(self, session_id: str) -> Any:
        return await self._request("POST", f"/experimental/sync/replay/{session_id}")

    async def sync_history(self, session_id: str) -> Any:
        return await self._request("GET", f"/experimental/sync/history/{session_id}")

    # ------------------------------------------------------------------
    # TUI
    # ------------------------------------------------------------------

    async def tui_submit_prompt(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/tui/submit", json_body=kwargs or None)

    async def tui_append_prompt(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/tui/append", json_body=kwargs or None)

    async def tui_clear_prompt(self) -> Any:
        return await self._request("POST", "/tui/clear")

    async def tui_execute_command(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/tui/command", json_body=kwargs or None)

    async def tui_show_toast(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/tui/toast", json_body=kwargs or None)

    async def tui_open_sessions(self) -> Any:
        return await self._request("POST", "/tui/sessions")

    async def tui_open_models(self) -> Any:
        return await self._request("POST", "/tui/models")

    async def tui_open_themes(self) -> Any:
        return await self._request("POST", "/tui/themes")

    async def tui_open_help(self) -> Any:
        return await self._request("POST", "/tui/help")

    async def tui_publish(self, **kwargs: Any) -> Any:
        return await self._request("POST", "/tui/publish", json_body=kwargs or None)

    async def tui_control_response(self, **kwargs: Any) -> Any:
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
