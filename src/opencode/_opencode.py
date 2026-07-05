from __future__ import annotations

import json
import warnings
from collections.abc import Iterator
from typing import Any, cast

from opencode._client import OpencodeClient
from opencode._models import SessionMessage
from opencode._server import OpencodeServer, create_opencode_server
from opencode._session import Session

_opencode_state: dict[str, Any] = {}


def _resolve_model(
    model: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, str] | None:
    model_str = model
    if not model_str and config:
        model_str = config.get("model")
    if not model_str:
        return None
    if "/" in model_str:
        provider, model_id = model_str.split("/", 1)
        return {"providerID": provider, "modelID": model_id}
    return {"providerID": "opencode", "modelID": model_str}


class Opencode:
    def __init__(
        self,
        *,
        model: str | None = None,
        hostname: str = "127.0.0.1",
        port: int = 4096,
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
            workspace=self._workspace,
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
        if agent:
            kwargs["agent"] = agent
        raw = self.client.session_create(**kwargs)
        sid = raw.id
        return Session(self.client, sid)

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
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> str:
        session = self.create_session(agent=agent)
        if auto_tools:
            from opencode._tools import ToolExecutor

            msg = session.ask(
                prompt,
                files=files,
                model=self._resolve_model(),
                format=format,
                tool_executor=ToolExecutor(),
            )
        else:
            msg = session.prompt(
                prompt,
                files=files,
                wait=wait,
                model=self._resolve_model(),
                format=format,
                poll_interval=poll_interval,
                poll_timeout=poll_timeout,
            )
        return _extract_text(msg)

    def ask_stream(
        self,
        prompt: str,
        *,
        files: list[dict[str, Any]] | None = None,
        session: Session | None = None,
    ) -> Iterator[str]:
        import httpx

        from opencode._stream_events import (
            MessagePartDeltaProps,
            MessagePartUpdatedProps,
            MessageUpdatedProps,
            SessionStatusProps,
            parse_stream_event,
        )

        if session is None:
            session = self.create_session()
        # Use V1 synchronous prompt — the response events arrive via /event
        body: dict[str, Any] = {"parts": [{"type": "text", "text": prompt}]}
        resolved = self._resolve_model()
        if resolved:
            body["model"] = resolved

        # Subscribe before sending to catch all events
        response = self.client.event_subscribe()
        assert isinstance(response, httpx.Response)

        # Send prompt (V1 sync)
        self.client.session_send(session.id, body)

        part_types: dict[str, str] = {}
        parts_with_deltas: set[str] = set()
        assistant_started = False

        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = parse_stream_event(line[6:])
            props = event.properties

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


def _extract_text(msg: SessionMessage) -> str:
    if isinstance(msg, dict) and msg.get("type") == "assistant":
        structured = msg.get("structured")
        if structured is not None:
            return json.dumps(structured, ensure_ascii=False, default=str)
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
    port: int = 4096,
    directory: str | None = None,
    config: dict[str, Any] | None = None,
) -> str:
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

    resolved = _resolve_model(model=state.get("model"), config=state.get("config", {}))
    if auto_tools:
        from opencode._tools import ToolExecutor

        msg = session.ask(prompt, model=resolved, format=format, tool_executor=ToolExecutor())
    else:
        msg = session.prompt(prompt, model=resolved, format=format)
    result = _extract_text(msg)

    if not keep:
        ai.close()
        state.clear()

    return result
