from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any, cast

from opencode._client import OpencodeClient, model_ref
from opencode._models import SessionMessage
from opencode._response_models import OpencodeResponse, StreamResult
from opencode._server import OpencodeServer, create_opencode_server
from opencode._session import Session, _permission_reply, _PromptWatch

_opencode_state: dict[str, Any] = {}


def _resolve_model(
    model: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, str] | None:
    model_str = model
    if not model_str and config:
        model_str = config.get("model")
    return model_ref(model_str) if model_str else None


class Opencode:
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
        self._client: OpencodeClient | None = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Opencode:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

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
        client = OpencodeClient(
            base_url=server.url,
            directory=self._directory,
            password=server.password,
            username=server.username,
            timeout=self._client_timeout,
        )
        self._server = server
        self._client = client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        if self._server:
            self._server.close()
            self._server = None

    @property
    def client(self) -> OpencodeClient:
        self.start()
        assert self._client is not None
        return self._client

    @property
    def server(self) -> OpencodeServer:
        self.start()
        assert self._server is not None
        return self._server

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def create_session(self, agent: str | None = None, **kwargs: Any) -> Session:
        """Create a session using this instance's ``model`` unless ``model=`` is given."""
        kwargs.setdefault("model", self._resolve_model())
        raw = self.client.session_create(agent=agent, **kwargs)
        return Session(self.client, raw.id or "")

    def _resolve_model(self) -> dict[str, str] | None:
        return _resolve_model(model=self._model, config=self._config)

    def ask(
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
        session = self.create_session(agent=agent)
        if auto_tools:
            msg = session.ask(
                prompt, files=files, format=format, poll_timeout=poll_timeout, collect=collect
            )
        else:
            msg = session.prompt(
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
        session: Session | None = None,
        collect: bool = False,
    ) -> Iterator[str]:
        """Yield assistant text deltas (``session.text.delta``) as they arrive.

        Reasoning is not yielded. Permission requests are rejected. With
        ``collect=True`` a :class:`StreamResult` exposing ``.events`` and
        ``.text`` is returned.
        """
        if session is None:
            session = self.create_session()
        sid = session.id
        client = self.client
        # Subscribe before sending so no events are missed
        stream = client.event_subscribe()
        sent = client.session_prompt(sid, prompt, files=files)
        watch = _PromptWatch(sid, sent.id or "", collect=False, quiet=True)

        def gen() -> Iterator[Any]:
            try:
                for line in stream.iter_lines():
                    event = watch.feed(line)
                    if event is None:
                        continue
                    if collect:
                        yield ("event", event)
                    decision = _permission_reply(event, None)
                    if decision is not None:
                        client.session_permission_reply(sid, event.properties["id"], decision)
                    elif event.type == "session.text.delta" and watch.delivered:
                        delta = event.properties.get("delta", "")
                        if delta:
                            yield delta
                    if watch.done:
                        break
            finally:
                stream.close()

        raw = gen()
        if collect:
            return StreamResult(raw)
        return cast(Iterator[str], raw)


def _extract_text(msg: SessionMessage) -> str:
    if isinstance(msg, dict) and msg.get("type") == "assistant":
        parts: list[dict[str, Any]] = cast("list[dict[str, Any]]", msg.get("content", []))
        texts: list[str] = []
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
        return "\n".join(texts)
    if isinstance(msg, dict) and msg.get("type") == "user":
        return cast(str, msg.get("text", ""))
    return str(msg)


def opencode(
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
    global _opencode_state
    state = _opencode_state

    if not state:
        cfg = dict(config or {})
        resolved_agent = agent or ("build" if auto_tools else None)
        ai = Opencode(port=port, directory=directory, config=cfg or None, model=model)
        ai.start()
        session = ai.create_session(agent=resolved_agent)
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
        msg = session.ask(prompt, format=format, collect=collect)
    else:
        msg = session.prompt(prompt, format=format, collect=collect)
    if collect:
        assert isinstance(msg, OpencodeResponse)
        if not keep:
            ai.close()
            state.clear()
        return msg

    if not keep:
        ai.close()
        state.clear()
    return _extract_text(cast("SessionMessage", msg))
