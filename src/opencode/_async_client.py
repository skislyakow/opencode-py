# Generated from _client.py by scripts/gen-async-client.py — do not edit by hand.
from __future__ import annotations

import asyncio
import os
import random
from typing import Any, TypeVar, cast, get_args, get_origin

import httpx

from opencode._client import (
    _ENVELOPE_KEYS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_USERNAME,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
    PASSWORD_ENV,
    RETRYABLE_STATUS_CODES,
    _compact,
    model_ref,
)
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
    ConfigEntry,
    ConfigShellOption,
    CredentialResponse,
    FileDiffResponse,
    FileSystemEntry,
    FormResponse,
    IntegrationResponse,
    LocationResponse,
    MCPServerResponse,
    ModelV2Info,
    PageResponse,
    PermissionRequestResponse,
    ProjectResponse,
    PromptResponse,
    ProviderV2Info,
    PtyResponse,
    RawResponse,
    ServerInfoResponse,
    SessionResponse,
    ShellResponse,
    SkillResponse,
    VcsBranchList,
    VcsFileStatus,
    VcsInfo,
    WorktreeResponse,
)
from opencode._types import NOT_GIVEN, NotGiven, is_given

_T = TypeVar("_T")


class _AsyncRawResponseContextManager:
    """Context manager that enables raw response mode on the client.

    All methods will return :class:`RawResponse[T]` instead of the parsed model.
    """

    def __init__(self, client: AsyncOpendcodeClient) -> None:
        self._client = client

    def __enter__(self) -> AsyncOpendcodeClient:
        self._client._raw_mode = True
        return self._client

    def __exit__(self, *args: Any) -> None:
        self._client._raw_mode = False


class AsyncOpendcodeClient:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:4096",
        directory: str | None = None,
        password: str | None = None,
        username: str = DEFAULT_USERNAME,
        timeout: float = 300.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        httpx_client: httpx.AsyncClient | None = None,
    ):
        """``password`` defaults to ``$OPENCODE_SERVER_PASSWORD``; when set, requests
        use HTTP Basic auth as required by the opencode v2 server."""
        self.base_url = base_url.rstrip("/")
        self.directory = directory
        self.username = username
        self.password = password if password is not None else os.environ.get(PASSWORD_ENV)
        self._auth = httpx.BasicAuth(username, self.password) if self.password else None
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx_client or httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self._raw_mode = False

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
        if self.directory and "location[directory]" not in params:
            params["location[directory]"] = self.directory
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
        origin = get_origin(model_class)
        args = get_args(model_class)
        if origin is list and args:
            inner = args[0]
            if isinstance(data, list):
                return [self._construct_type(inner, item) for item in data]
            return cast(_T, data)
        if isinstance(data, dict):
            return cast(_T, cast(Any, model_class).model_construct(**data))
        if isinstance(data, list):
            return [self._construct_type(model_class, item) for item in data]
        if data is None:
            return None
        return data

    def _parse_json(self, json_data: Any, cast_to: type[_T] | None) -> Any:
        """Unwrap the v2 ``{"data": ...}`` envelope and build response models.

        Paginated responses (``{"data": [...], "cursor": {...}}``) become a
        :class:`PageResponse`.
        """
        if isinstance(json_data, dict) and "data" in json_data:
            if "cursor" in json_data:
                return PageResponse.model_construct(
                    data=self._construct_type(cast_to, json_data["data"]),
                    cursor=json_data["cursor"],
                )
            if set(json_data) <= _ENVELOPE_KEYS:
                json_data = json_data["data"]
        return self._construct_type(cast_to, json_data)

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
                parsed: Any = None
            else:
                ct = response.headers.get("content-type", "")
                if "text/event-stream" in ct:
                    parsed = response
                elif "json" in ct:
                    parsed = self._parse_json(response.json(), cast_to)
                elif "text/" in ct:
                    parsed = response.text
                else:
                    parsed = response.content
            if self._raw_mode:
                return RawResponse(parsed, response)
            return parsed

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
                    method, url, params=params, json=body, headers=hdrs, auth=self._auth
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
        response = await self._client.send(request, stream=True, auth=self._auth)
        if not response.is_success:
            await response.aread()
            await response.aclose()
            self._handle(response)
        if self._raw_mode:
            return cast(httpx.Response, RawResponse(response, response))
        return response

    # ------------------------------------------------------------------
    # copy / with_options / with_raw_response
    # ------------------------------------------------------------------

    @property
    def with_raw_response(self) -> _AsyncRawResponseContextManager:
        return _AsyncRawResponseContextManager(self)

    def copy(
        self,
        *,
        base_url: str | NotGiven = NOT_GIVEN,
        timeout: float | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        directory: str | None | NotGiven = NOT_GIVEN,
        password: str | None | NotGiven = NOT_GIVEN,
        username: str | NotGiven = NOT_GIVEN,
        httpx_client: httpx.AsyncClient | None | NotGiven = NOT_GIVEN,
    ) -> AsyncOpendcodeClient:
        return AsyncOpendcodeClient(
            base_url=cast(str, base_url) if is_given(base_url) else self.base_url,
            timeout=cast(float, timeout) if is_given(timeout) else self._timeout,
            max_retries=cast(int, max_retries) if is_given(max_retries) else self._max_retries,
            directory=cast("str | None", directory) if is_given(directory) else self.directory,
            password=cast("str | None", password) if is_given(password) else self.password,
            username=cast(str, username) if is_given(username) else self.username,
            httpx_client=(
                cast("httpx.AsyncClient | None", httpx_client)
                if is_given(httpx_client)
                else self._client
            ),
        )

    def with_options(self, **kwargs: Any) -> AsyncOpendcodeClient:
        return self.copy(**kwargs)

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------

    async def health(self) -> ServerInfoResponse:
        """``GET /api/info`` — server version, pid and URLs."""
        return cast(
            ServerInfoResponse,
            await self._request("GET", "/api/info", cast_to=ServerInfoResponse),
        )

    async def location_get(self, **params: Any) -> LocationResponse:
        return cast(
            LocationResponse,
            await self._request("GET", "/api/location", params=params, cast_to=LocationResponse),
        )

    async def location_reload(self) -> None:
        await self._request("POST", "/api/location/reload")

    async def event_subscribe(self, **params: Any) -> httpx.Response:
        """``GET /api/event`` — open the SSE event stream (caller must close it)."""
        return await self._request_stream("GET", "/api/event", params=params)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    async def config_get(self, **params: Any) -> list[ConfigEntry]:
        return cast(
            "list[ConfigEntry]",
            await self._request("GET", "/api/config", params=params, cast_to=list[ConfigEntry]),
        )

    async def config_shells(self) -> list[ConfigShellOption]:
        return cast(
            "list[ConfigShellOption]",
            await self._request("GET", "/api/config/shell", cast_to=list[ConfigShellOption]),
        )

    async def config_update(self, **kwargs: Any) -> Any:
        """``PATCH /api/experimental/config`` (currently only ``shell``)."""
        return await self._request("PATCH", "/api/experimental/config", json_body=kwargs)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def session_create(
        self,
        *,
        model: str | dict[str, str] | None = None,
        agent: str | None = None,
        title: str | None = None,
        parent_id: str | None = None,
        permissions: list[dict[str, str]] | None = None,
        metadata: dict[str, Any] | None = None,
        directory: str | None = None,
        **kwargs: Any,
    ) -> SessionResponse:
        """``POST /api/session``.

        ``model`` is ``"provider/model"`` or ``{"providerID": ..., "id": ...}``.
        ``directory`` defaults to the client's ``directory``.
        """
        directory = directory or self.directory
        body = _compact(
            model=model_ref(model),
            agent=agent,
            title=title,
            parentID=parent_id,
            permissions=permissions,
            metadata=metadata,
            location={"directory": directory} if directory else None,
            **kwargs,
        )
        return cast(
            SessionResponse,
            await self._request("POST", "/api/session", json_body=body, cast_to=SessionResponse),
        )

    async def session_get(self, session_id: str) -> SessionResponse:
        return cast(
            SessionResponse,
            await self._request("GET", f"/api/session/{session_id}", cast_to=SessionResponse),
        )

    async def session_list(self, **params: Any) -> PageResponse:
        """``GET /api/session`` — params: limit, order, search, parentID, archived, ..."""
        return cast(
            PageResponse,
            await self._request(
                "GET", "/api/session", params=params, cast_to=list[SessionResponse]
            ),
        )

    async def session_active(self) -> Any:
        return await self._request("GET", "/api/session/active")

    async def session_delete(self, session_id: str) -> None:
        await self._request("DELETE", f"/api/session/{session_id}")

    async def session_update(self, session_id: str, **kwargs: Any) -> None:
        """``PATCH /api/session/{id}`` — title, metadata, permissions, archived."""
        await self._request("PATCH", f"/api/session/{session_id}", json_body=kwargs)

    async def session_fork(self, session_id: str, *, before: str | None = None) -> SessionResponse:
        return cast(
            SessionResponse,
            await self._request(
                "POST",
                f"/api/session/{session_id}/fork",
                json_body=_compact(before=before),
                cast_to=SessionResponse,
            ),
        )

    async def session_switch_agent(self, session_id: str, agent: str) -> None:
        await self._request("POST", f"/api/session/{session_id}/agent", json_body={"agent": agent})

    async def session_switch_model(self, session_id: str, model: str | dict[str, str]) -> None:
        await self._request(
            "POST", f"/api/session/{session_id}/model", json_body={"model": model_ref(model)}
        )

    async def session_move(self, session_id: str, directory: str, **kwargs: Any) -> None:
        await self._request(
            "POST",
            f"/api/session/{session_id}/move",
            json_body={"directory": directory, **kwargs},
        )

    async def session_prompt(
        self,
        session_id: str,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        delivery: str | None = None,
        **kwargs: Any,
    ) -> PromptResponse:
        """``POST /api/session/{id}/prompt`` — enqueue a prompt (returns immediately).

        ``delivery`` is ``"steer"`` or ``"queue"``. Use :meth:`session_wait` or
        :meth:`event_subscribe` to wait for the assistant to finish.
        """
        body = _compact(
            text=text, files=files, agents=agents, skills=skills, delivery=delivery, **kwargs
        )
        return cast(
            PromptResponse,
            await self._request(
                "POST",
                f"/api/session/{session_id}/prompt",
                json_body=body,
                cast_to=PromptResponse,
            ),
        )

    async def session_wait(self, session_id: str) -> None:
        """``POST /api/experimental/session/{id}/wait`` — block until the session is idle."""
        await self._request("POST", f"/api/experimental/session/{session_id}/wait")

    async def session_command(
        self, session_id: str, name: str, text: str = "", **kwargs: Any
    ) -> None:
        await self._request(
            "POST",
            f"/api/session/{session_id}/command",
            json_body={"name": name, "text": text, **kwargs},
        )

    async def session_shell(self, session_id: str, command: str) -> None:
        await self._request(
            "POST", f"/api/session/{session_id}/shell", json_body={"command": command}
        )

    async def session_synthetic(self, session_id: str, text: str, **kwargs: Any) -> Any:
        return await self._request(
            "POST",
            f"/api/session/{session_id}/synthetic",
            json_body={"text": text, **kwargs},
        )

    async def session_compact(self, session_id: str, **kwargs: Any) -> Any:
        return await self._request("POST", f"/api/session/{session_id}/compact", json_body=kwargs)

    async def session_context(self, session_id: str) -> list[dict[str, Any]]:
        """``GET /api/session/{id}/context`` — messages in chronological order."""
        return cast(
            "list[dict[str, Any]]",
            await self._request("GET", f"/api/session/{session_id}/context"),
        )

    async def session_messages(self, session_id: str, **params: Any) -> PageResponse:
        """``GET /api/session/{id}/message`` — params: limit, order, cursor, type."""
        return cast(
            PageResponse,
            await self._request("GET", f"/api/session/{session_id}/message", params=params),
        )

    async def session_message(self, session_id: str, message_id: str) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            await self._request("GET", f"/api/session/{session_id}/message/{message_id}"),
        )

    async def session_diff(self, session_id: str) -> list[FileDiffResponse]:
        return cast(
            "list[FileDiffResponse]",
            await self._request(
                "GET", f"/api/session/{session_id}/diff", cast_to=list[FileDiffResponse]
            ),
        )

    async def session_interrupt(self, session_id: str, *, resume: bool | None = None) -> Any:
        return await self._request(
            "POST",
            f"/api/session/{session_id}/interrupt",
            params=_compact(resume=None if resume is None else str(resume).lower()),
        )

    async def session_background(self, session_id: str) -> None:
        await self._request("POST", f"/api/session/{session_id}/background")

    async def session_generate(self, session_id: str, prompt: str) -> Any:
        return await self._request(
            "POST", f"/api/session/{session_id}/generate", json_body={"prompt": prompt}
        )

    async def session_revert_stage(self, session_id: str, message_id: str, **kwargs: Any) -> Any:
        return await self._request(
            "POST",
            f"/api/session/{session_id}/revert/stage",
            json_body={"messageID": message_id, **kwargs},
        )

    async def session_revert_commit(self, session_id: str) -> None:
        await self._request("POST", f"/api/session/{session_id}/revert/commit")

    async def session_revert_clear(self, session_id: str) -> None:
        await self._request("DELETE", f"/api/session/{session_id}/revert")

    async def session_inbox(self, session_id: str) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            await self._request("GET", f"/api/session/{session_id}/inbox"),
        )

    async def session_permissions(self, session_id: str) -> list[PermissionRequestResponse]:
        """``GET /api/session/{id}/permission`` — pending permission requests."""
        return cast(
            "list[PermissionRequestResponse]",
            await self._request(
                "GET",
                f"/api/session/{session_id}/permission",
                cast_to=list[PermissionRequestResponse],
            ),
        )

    async def session_permission_reply(
        self,
        session_id: str,
        request_id: str,
        decision: str,
        *,
        message: str | None = None,
    ) -> None:
        """Reply to a permission request; ``decision`` is ``once``, ``always`` or ``reject``."""
        await self._request(
            "POST",
            f"/api/session/{session_id}/permission/{request_id}/reply",
            json_body=_compact(decision=decision, message=message),
        )

    async def session_forms(self, session_id: str) -> list[FormResponse]:
        return cast(
            "list[FormResponse]",
            await self._request(
                "GET", f"/api/session/{session_id}/form", cast_to=list[FormResponse]
            ),
        )

    async def session_form_reply(
        self, session_id: str, form_id: str, answer: dict[str, Any]
    ) -> None:
        await self._request(
            "POST",
            f"/api/session/{session_id}/form/{form_id}/reply",
            json_body={"answer": answer},
        )

    async def session_form_cancel(self, session_id: str, form_id: str) -> None:
        await self._request("DELETE", f"/api/session/{session_id}/form/{form_id}")

    # ------------------------------------------------------------------
    # Models, providers, agents
    # ------------------------------------------------------------------

    async def model_list(self, **params: Any) -> list[ModelV2Info]:
        return cast(
            "list[ModelV2Info]",
            await self._request("GET", "/api/model", params=params, cast_to=list[ModelV2Info]),
        )

    async def model_default(self) -> ModelV2Info | None:
        return cast(
            "ModelV2Info | None",
            await self._request("GET", "/api/model/default", cast_to=ModelV2Info),
        )

    async def provider_list(self, **params: Any) -> list[ProviderV2Info]:
        return cast(
            "list[ProviderV2Info]",
            await self._request(
                "GET", "/api/provider", params=params, cast_to=list[ProviderV2Info]
            ),
        )

    async def provider_get(self, provider_id: str) -> ProviderV2Info:
        return cast(
            ProviderV2Info,
            await self._request("GET", f"/api/provider/{provider_id}", cast_to=ProviderV2Info),
        )

    async def agent_list(self) -> list[AgentResponse]:
        return cast(
            "list[AgentResponse]",
            await self._request("GET", "/api/agent", cast_to=list[AgentResponse]),
        )

    async def agent_get(self, agent_id: str) -> AgentResponse:
        return cast(
            AgentResponse,
            await self._request("GET", f"/api/agent/{agent_id}", cast_to=AgentResponse),
        )

    async def command_list(self) -> list[CommandResponse]:
        return cast(
            "list[CommandResponse]",
            await self._request("GET", "/api/command", cast_to=list[CommandResponse]),
        )

    async def skill_list(self) -> list[SkillResponse]:
        return cast(
            "list[SkillResponse]",
            await self._request("GET", "/api/skill", cast_to=list[SkillResponse]),
        )

    # ------------------------------------------------------------------
    # Integrations & credentials
    # ------------------------------------------------------------------

    async def integration_list(self) -> list[IntegrationResponse]:
        return cast(
            "list[IntegrationResponse]",
            await self._request("GET", "/api/integration", cast_to=list[IntegrationResponse]),
        )

    async def integration_get(self, integration_id: str) -> IntegrationResponse:
        return cast(
            IntegrationResponse,
            await self._request(
                "GET", f"/api/integration/{integration_id}", cast_to=IntegrationResponse
            ),
        )

    async def integration_connect_key(self, integration_id: str, **kwargs: Any) -> None:
        await self._request(
            "POST", f"/api/integration/{integration_id}/connect/key", json_body=kwargs
        )

    async def credential_list(self) -> list[CredentialResponse]:
        return cast(
            "list[CredentialResponse]",
            await self._request("GET", "/api/credential", cast_to=list[CredentialResponse]),
        )

    async def credential_create(
        self, integration_id: str, value: Any, **kwargs: Any
    ) -> CredentialResponse:
        return cast(
            CredentialResponse,
            await self._request(
                "POST",
                "/api/credential",
                json_body={"integrationID": integration_id, "value": value, **kwargs},
                cast_to=CredentialResponse,
            ),
        )

    async def credential_update(self, credential_id: str, label: str) -> None:
        await self._request("PATCH", f"/api/credential/{credential_id}", json_body={"label": label})

    async def credential_remove(self, credential_id: str) -> None:
        await self._request("DELETE", f"/api/credential/{credential_id}")

    async def credential_activate(self, credential_id: str) -> None:
        await self._request("POST", f"/api/credential/{credential_id}/activate")

    # ------------------------------------------------------------------
    # MCP
    # ------------------------------------------------------------------

    async def mcp_list(self) -> list[MCPServerResponse]:
        return cast(
            "list[MCPServerResponse]",
            await self._request("GET", "/api/mcp", cast_to=list[MCPServerResponse]),
        )

    async def mcp_add(self, server: str, config: Any) -> Any:
        return await self._request(
            "PUT", f"/api/experimental/mcp/{server}", json_body={"config": config}
        )

    async def mcp_remove(self, server: str) -> Any:
        return await self._request("DELETE", f"/api/experimental/mcp/{server}")

    async def mcp_connect(self, server: str) -> Any:
        return await self._request("POST", f"/api/experimental/mcp/{server}/connect")

    async def mcp_disconnect(self, server: str) -> Any:
        return await self._request("POST", f"/api/experimental/mcp/{server}/disconnect")

    # ------------------------------------------------------------------
    # Permissions & forms (all sessions)
    # ------------------------------------------------------------------

    async def permission_list(self) -> list[PermissionRequestResponse]:
        return cast(
            "list[PermissionRequestResponse]",
            await self._request(
                "GET", "/api/permission/request", cast_to=list[PermissionRequestResponse]
            ),
        )

    async def permission_saved_list(self) -> list[dict[str, Any]]:
        return cast("list[dict[str, Any]]", await self._request("GET", "/api/permission/saved"))

    async def permission_saved_remove(self, permission_id: str) -> None:
        await self._request("DELETE", f"/api/permission/saved/{permission_id}")

    async def form_list(self) -> list[FormResponse]:
        return cast(
            "list[FormResponse]",
            await self._request("GET", "/api/form", cast_to=list[FormResponse]),
        )

    # ------------------------------------------------------------------
    # Filesystem
    # ------------------------------------------------------------------

    async def fs_read(self, path: str) -> str | bytes:
        """``GET /api/fs/read/{path}`` — text files return ``str``, others ``bytes``."""
        return cast("str | bytes", await self._request("GET", f"/api/fs/read/{path.lstrip('/')}"))

    async def fs_list(self, path: str | None = None) -> list[FileSystemEntry]:
        return cast(
            "list[FileSystemEntry]",
            await self._request(
                "GET", "/api/fs/list", params=_compact(path=path), cast_to=list[FileSystemEntry]
            ),
        )

    async def fs_find(
        self, query: str, *, type: str | None = None, limit: int | None = None
    ) -> list[FileSystemEntry]:
        return cast(
            "list[FileSystemEntry]",
            await self._request(
                "GET",
                "/api/fs/find",
                params=_compact(query=query, type=type, limit=limit),
                cast_to=list[FileSystemEntry],
            ),
        )

    # ------------------------------------------------------------------
    # VCS
    # ------------------------------------------------------------------

    async def vcs_get(self) -> VcsInfo:
        return cast(VcsInfo, await self._request("GET", "/api/vcs", cast_to=VcsInfo))

    async def vcs_base(self) -> Any:
        return await self._request("GET", "/api/vcs/base")

    async def vcs_status(self) -> list[VcsFileStatus]:
        return cast(
            "list[VcsFileStatus]",
            await self._request("GET", "/api/vcs/status", cast_to=list[VcsFileStatus]),
        )

    async def vcs_branches(self) -> VcsBranchList:
        return cast(
            VcsBranchList, await self._request("GET", "/api/vcs/branch", cast_to=VcsBranchList)
        )

    async def vcs_diff(self, **params: Any) -> list[FileDiffResponse]:
        return cast(
            "list[FileDiffResponse]",
            await self._request(
                "GET", "/api/vcs/diff", params=params, cast_to=list[FileDiffResponse]
            ),
        )

    async def vcs_init(self) -> None:
        await self._request("POST", "/api/vcs/init")

    # ------------------------------------------------------------------
    # Projects & worktrees
    # ------------------------------------------------------------------

    async def project_list(self) -> list[ProjectResponse]:
        return cast(
            "list[ProjectResponse]",
            await self._request("GET", "/api/project", cast_to=list[ProjectResponse]),
        )

    async def project_update(self, project_id: str, **kwargs: Any) -> Any:
        return await self._request("PATCH", f"/api/project/{project_id}", json_body=kwargs)

    async def worktree_list(self, project_id: str) -> list[WorktreeResponse]:
        return cast(
            "list[WorktreeResponse]",
            await self._request(
                "GET",
                "/api/worktree",
                params={"projectID": project_id},
                cast_to=list[WorktreeResponse],
            ),
        )

    async def worktree_create(self, project_id: str, **kwargs: Any) -> Any:
        return await self._request(
            "POST", "/api/worktree", json_body={"projectID": project_id, **kwargs}
        )

    async def worktree_remove(
        self, project_id: str, directory: str, *, force: bool = False
    ) -> None:
        await self._request(
            "DELETE",
            "/api/worktree",
            json_body={"projectID": project_id, "directory": directory, "force": force},
        )

    async def worktree_refresh(self) -> None:
        await self._request("POST", "/api/worktree/refresh")

    # ------------------------------------------------------------------
    # PTY & shell processes
    # ------------------------------------------------------------------

    async def pty_list(self) -> list[PtyResponse]:
        return cast(
            "list[PtyResponse]", await self._request("GET", "/api/pty", cast_to=list[PtyResponse])
        )

    async def pty_create(self, **kwargs: Any) -> PtyResponse:
        return cast(
            PtyResponse,
            await self._request("POST", "/api/pty", json_body=kwargs, cast_to=PtyResponse),
        )

    async def pty_get(self, pty_id: str) -> PtyResponse:
        return cast(
            PtyResponse, await self._request("GET", f"/api/pty/{pty_id}", cast_to=PtyResponse)
        )

    async def pty_update(self, pty_id: str, **kwargs: Any) -> PtyResponse:
        return cast(
            PtyResponse,
            await self._request("PUT", f"/api/pty/{pty_id}", json_body=kwargs, cast_to=PtyResponse),
        )

    async def pty_remove(self, pty_id: str) -> None:
        await self._request("DELETE", f"/api/pty/{pty_id}")

    async def shell_list(self) -> list[ShellResponse]:
        return cast(
            "list[ShellResponse]",
            await self._request("GET", "/api/shell", cast_to=list[ShellResponse]),
        )

    async def shell_create(self, command: str, **kwargs: Any) -> ShellResponse:
        return cast(
            ShellResponse,
            await self._request(
                "POST",
                "/api/shell",
                json_body={"command": command, **kwargs},
                cast_to=ShellResponse,
            ),
        )

    async def shell_get(self, shell_id: str) -> ShellResponse:
        return cast(
            ShellResponse,
            await self._request("GET", f"/api/shell/{shell_id}", cast_to=ShellResponse),
        )

    async def shell_output(self, shell_id: str) -> Any:
        return await self._request("GET", f"/api/shell/{shell_id}/output")

    async def shell_remove(self, shell_id: str) -> None:
        await self._request("DELETE", f"/api/shell/{shell_id}")

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpendcodeClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
