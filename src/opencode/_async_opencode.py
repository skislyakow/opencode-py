from __future__ import annotations

import warnings
from collections.abc import AsyncIterator
from typing import Any, cast

from opencode._async_client import AsyncOpendcodeClient
from opencode._async_session import AsyncSession
from opencode._models import SessionMessage
from opencode._opencode import _extract_text, _resolve_model
from opencode._response_models import AsyncStreamResult, OpencodeResponse
from opencode._server import OpencodeServer, create_opencode_server

_async_opencode_state: dict[str, Any] = {}


class AsyncOpendcode:
    def __init__(
        self,
        *,
        model: str | None = None,
        hostname: str = "127.0.0.1",
        port: int | None = None,
        directory: str | None = None,
        workspace: str | None = None,
        server_timeout: float = 30.0,
        client_timeout: float = 300.0,
        config: dict[str, Any] | None = None,
        opencode_binary: str | None = None,
    ):
        self._model = model
        self._hostname = hostname
        self._port = port
        self._directory = directory
        self._workspace = workspace
        self._server_timeout = server_timeout
        self._client_timeout = client_timeout
        self._config = config
        self._opencode_binary = opencode_binary

        self._server: OpencodeServer | None = None
        self._client: AsyncOpendcodeClient | None = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> AsyncOpendcode:
        self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Server / Client lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._client is not None:
            return
        server = create_opencode_server(
            hostname=self._hostname,
            port=self._port,
            timeout=self._server_timeout,
            config=self._config,
            opencode_binary=self._opencode_binary,
        )
        client = AsyncOpendcodeClient(
            base_url=server.url,
            directory=self._directory,
            workspace=self._workspace,
            timeout=self._client_timeout,
        )
        self._server = server
        self._client = client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        if self._server:
            self._server.close()
            self._server = None

    @property
    def client(self) -> AsyncOpendcodeClient:
        assert self._client is not None
        return self._client

    @property
    def server(self) -> OpencodeServer:
        assert self._server is not None
        return self._server

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    async def create_session(self, agent: str | None = None, **kwargs: Any) -> AsyncSession:
        if agent:
            kwargs["agent"] = agent
        raw = await self.client.session_create(**kwargs)
        sid = raw.id
        return AsyncSession(self.client, sid)

    async def ask(
        self,
        prompt: str,
        *,
        files: list[dict[str, Any]] | None = None,
        auto_tools: bool = False,
        agent: str | None = None,
        format: dict[str, Any] | None = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
        collect: bool = False,
    ) -> str | OpencodeResponse:
        session = await self.create_session(agent=agent)
        model = _resolve_model(model=self._model, config=self._config)
        if auto_tools:
            from opencode._tools import ToolExecutor

            msg = await session.ask(
                prompt,
                files=files,
                model=model,
                format=format,
                tool_executor=ToolExecutor(),
                collect=collect,
            )
        else:
            msg = await session.prompt(
                prompt,
                files=files,
                wait=wait,
                model=model,
                format=format,
                poll_interval=poll_interval,
                poll_timeout=poll_timeout,
                collect=collect,
            )
        if collect:
            assert isinstance(msg, OpencodeResponse)
            return msg
        return _extract_text(cast("SessionMessage", msg))

    def ask_stream(
        self,
        prompt: str,
        *,
        files: list[dict[str, Any]] | None = None,
        session: AsyncSession | None = None,
        collect: bool = False,
    ) -> AsyncIterator[str]:
        from opencode._stream_events import (
            MessagePartDeltaProps,
            MessagePartUpdatedProps,
            MessageUpdatedProps,
            SessionStatusProps,
            parse_stream_event,
        )

        if session is None:
            # Caller must create session before passing it, or we use a workaround
            raise TypeError("session is required for async ask_stream")

        async def gen() -> AsyncIterator[Any]:
            import httpx

            # Subscribe before sending to catch all events
            response = await self.client.event_subscribe()
            assert isinstance(response, httpx.Response)

            # Send prompt (V1 sync)
            body: dict[str, Any] = {"parts": [{"type": "text", "text": prompt}]}
            resolved = _resolve_model(model=self._model, config=self._config)
            if resolved:
                body["model"] = resolved
            await self.client.session_send(session.id, body)

            part_types: dict[str, str] = {}
            parts_with_deltas: set[str] = set()
            assistant_started = False

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = parse_stream_event(line[6:])
                props = event.properties

                if collect:
                    yield ("event", event)

                # Skip events for other sessions
                sid = props.get("sessionID")
                if sid is not None and sid != session.id:
                    continue

                if event.type == "message.updated":
                    p_msg = MessageUpdatedProps.model_construct(**props)
                    if p_msg.info.get("role") == "assistant":
                        assistant_started = True

                elif event.type == "message.part.updated":
                    p_part = MessagePartUpdatedProps.model_construct(**props)
                    part_id = p_part.part.get("id", "")
                    part_type = p_part.part.get("type", "")
                    if part_id and part_type:
                        part_types[part_id] = part_type
                    if assistant_started and part_type == "text":
                        text = p_part.part.get("text", "")
                        if text and part_id not in parts_with_deltas:
                            yield text

                elif event.type == "message.part.delta":
                    p_delta = MessagePartDeltaProps.model_construct(**props)
                    part_id = p_delta.partID
                    part_type = part_types.get(part_id)
                    if assistant_started and part_type == "text":
                        delta = p_delta.delta
                        if delta:
                            parts_with_deltas.add(part_id)
                            yield delta

                elif event.type in ("session.status",):
                    p_status = SessionStatusProps.model_construct(**props)
                    status = p_status.status
                    if isinstance(status, dict) and status.get("type") == "idle":
                        break

                elif event.type == "session.idle":
                    break

        raw = gen()
        if collect:
            return AsyncStreamResult(raw)
        return cast(AsyncIterator[str], raw)


async def async_opencode(
    prompt: str,
    *,
    keep: bool = False,
    auto_tools: bool = False,
    agent: str | None = None,
    model: str | None = None,
    format: dict[str, Any] | None = None,
    port: int | None = None,
    directory: str | None = None,
    config: dict[str, Any] | None = None,
    collect: bool = False,
) -> str | OpencodeResponse:
    global _async_opencode_state
    state = _async_opencode_state

    if not state:
        cfg = dict(config or {})
        resolved_agent = agent or ("build" if auto_tools else None)
        ai = AsyncOpendcode(port=port, directory=directory, config=cfg or None, model=model)
        ai.start()
        session = await ai.create_session(agent=resolved_agent)
        state["ai"] = ai
        state["session"] = session
        state["config"] = cfg
        state["model"] = model
    else:
        ai = state["ai"]
        session = state["session"]
        if model is not None or config is not None:
            new_cfg = dict(config or {})
            if model is not None and model != state.get("model"):
                warnings.warn("Ignoring new model — using existing session")
            elif new_cfg != state.get("config", {}):
                warnings.warn("Ignoring new config — using existing session")

    resolved = _resolve_model(model=state.get("model"), config=state.get("config", {}))
    if auto_tools:
        from opencode._tools import ToolExecutor

        msg = await session.ask(
                prompt, model=resolved, format=format, tool_executor=ToolExecutor(), collect=collect
            )
    else:
        msg = await session.prompt(prompt, model=resolved, format=format, collect=collect)
    if collect:
        assert isinstance(msg, OpencodeResponse)
        if not keep:
            await ai.close()
            state.clear()
        return msg

    if not keep:
        await ai.close()
        state.clear()
    return _extract_text(cast("SessionMessage", msg))
