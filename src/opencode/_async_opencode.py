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
from opencode._session import _permission_reply, _PromptWatch

_async_opencode_state: dict[str, Any] = {}


class AsyncOpendcode:
    def __init__(
        self,
        *,
        model: str | None = None,
        hostname: str = "127.0.0.1",
        port: int | None = None,
        directory: str | None = None,
        server_timeout: float = 30.0,
        client_timeout: float = 300.0,
        config: dict[str, Any] | None = None,
        opencode_binary: str | None = None,
    ):
        self._model = model
        self._hostname = hostname
        self._port = port
        self._directory = directory
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
            password=server.password,
            username=server.username,
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
        """Create a session using this instance's ``model`` unless ``model=`` is given."""
        kwargs.setdefault("model", _resolve_model(model=self._model, config=self._config))
        raw = await self.client.session_create(agent=agent, **kwargs)
        return AsyncSession(self.client, raw.id or "")

    async def ask(
        self,
        prompt: str,
        *,
        files: list[dict[str, Any]] | None = None,
        auto_tools: bool = False,
        agent: str | None = None,
        format: dict[str, Any] | None = None,
        wait: bool = True,
        poll_timeout: float = 600.0,
        collect: bool = False,
    ) -> str | OpencodeResponse:
        session = await self.create_session(agent=agent)
        if auto_tools:
            msg = await session.ask(
                prompt, files=files, format=format, poll_timeout=poll_timeout, collect=collect
            )
        else:
            msg = await session.prompt(
                prompt,
                files=files,
                wait=wait,
                format=format,
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
        """Async version of :meth:`Opencode.ask_stream` (``session`` is required)."""
        if session is None:
            raise TypeError("session is required for async ask_stream")
        sid = session.id
        client = self.client

        async def gen() -> AsyncIterator[Any]:
            # Subscribe before sending so no events are missed
            stream = await client.event_subscribe()
            try:
                sent = await client.session_prompt(sid, prompt, files=files)
                watch = _PromptWatch(sid, sent.id or "", collect=False, quiet=True)
                async for line in stream.aiter_lines():
                    event = watch.feed(line)
                    if event is None:
                        continue
                    if collect:
                        yield ("event", event)
                    decision = _permission_reply(event, None)
                    if decision is not None:
                        await client.session_permission_reply(
                            sid, event.properties["id"], decision
                        )
                    elif event.type == "session.text.delta" and watch.delivered:
                        delta = event.properties.get("delta", "")
                        if delta:
                            yield delta
                    if watch.done:
                        break
            finally:
                await stream.aclose()

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

    if auto_tools:
        msg = await session.ask(prompt, format=format, collect=collect)
    else:
        msg = await session.prompt(prompt, format=format, collect=collect)
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
