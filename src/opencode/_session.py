from __future__ import annotations

import time
from contextlib import closing
from typing import Any, cast

from opencode._client import OpencodeClient
from opencode._errors import APITimeoutError, OpencodeError
from opencode._logs import logger
from opencode._models import SessionMessage
from opencode._response_models import OpencodeResponse, PageResponse, SessionResponse
from opencode._stream_events import StreamEvent, parse_stream_event
from opencode._tools import ToolExecutor

_FINISHED_EVENTS = {"session.execution.succeeded", "session.execution.interrupted"}


def _check_format(format: dict[str, Any] | None) -> None:
    if format is not None:
        raise OpencodeError(
            "Structured output (format=...) is not supported by the opencode v2 API"
        )


class _PromptWatch:
    """Tracks SSE events for one prompt until its execution finishes.

    Shared by :class:`Session` and :class:`AsyncSession`.
    """

    def __init__(self, session_id: str, prompt_id: str, *, collect: bool, quiet: bool):
        self.session_id = session_id
        self.prompt_id = prompt_id
        self.collect = collect
        self.quiet = quiet
        self.delivered = False
        self.done = False
        self.events: list[StreamEvent] = []

    def feed(self, line: str) -> StreamEvent | None:
        """Process one SSE line; returns the event if it belongs to this session."""
        if not line.startswith("data:"):
            return None
        event = parse_stream_event(line[5:].strip())
        if event.session_id != self.session_id:
            return None
        if self.collect:
            self.events.append(event)
        props = event.properties
        if event.type == "session.inbox.delivered" and props.get("inboxID") == self.prompt_id:
            self.delivered = True
        elif event.type == "session.tool.input.started" and not self.quiet:
            print(f"\033[33m[Tool] {props.get('name', '')}\033[0m")
        elif self.delivered and event.type in _FINISHED_EVENTS:
            self.done = True
        elif self.delivered and event.type == "session.execution.failed":
            error = props.get("error") or {}
            detail = error.get("message") if isinstance(error, dict) else None
            raise OpencodeError(f"Session {self.session_id} failed: {detail or error}")
        return event


def _permission_reply(event: StreamEvent | None, tool_executor: ToolExecutor | None) -> str | None:
    """Decision for a ``permission.asked`` event (``None`` for any other event)."""
    if event is None or event.type != "permission.asked":
        return None
    request = event.properties
    if tool_executor is not None:
        return tool_executor.decide(request)
    logger.warning(
        "Rejecting permission request %s (%s): no tool_executor given",
        request.get("id"),
        request.get("action"),
    )
    return "reject"


def _build_reply(messages: list[dict[str, Any]], prompt_id: str) -> SessionMessage:
    """Merge every assistant message after the prompt into one reply message."""
    ids = [m.get("id") for m in messages]
    if prompt_id in ids:
        start = ids.index(prompt_id) + 1
    else:
        users = [i for i, m in enumerate(messages) if m.get("type") == "user"]
        start = users[-1] + 1 if users else 0
    replies = [m for m in messages[start:] if m.get("type") == "assistant"]
    if not replies:
        return cast(SessionMessage, {"id": "", "type": "assistant", "content": [], "time": {}})
    content = [part for m in replies for part in m.get("content", [])]
    return cast(SessionMessage, {**replies[-1], "content": content})


def _user_message(sent: Any, text: str) -> SessionMessage:
    return cast(
        SessionMessage,
        {"id": sent.id or "", "type": "user", "text": text, "time": sent.time or {}},
    )


class Session:
    def __init__(self, client: OpencodeClient, session_id: str):
        self._client = client
        self.id = session_id

    def prompt(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        model: str | dict[str, str] | None = None,
        format: dict[str, Any] | None = None,
        wait: bool = True,
        poll_timeout: float = 600.0,
        collect: bool = False,
        tool_executor: ToolExecutor | None = None,
        quiet: bool = True,
    ) -> OpencodeResponse | SessionMessage:
        """Send a prompt and (by default) wait for the assistant's reply.

        Uses ``POST /api/session/{id}/prompt`` and follows ``/api/event`` until
        the execution finishes. ``model`` switches the session model first.
        Permission requests are answered by ``tool_executor`` (rejected if
        ``None``). With ``wait=False`` the queued user message is returned.
        """
        _check_format(format)
        if model is not None:
            self._client.session_switch_model(self.id, model)
        if not wait:
            sent = self._client.session_prompt(
                self.id, text, files=files, agents=agents, skills=skills
            )
            return _user_message(sent, text)

        deadline = time.monotonic() + poll_timeout
        with closing(self._client.event_subscribe()) as stream:
            sent = self._client.session_prompt(
                self.id, text, files=files, agents=agents, skills=skills
            )
            watch = _PromptWatch(self.id, sent.id or "", collect=collect, quiet=quiet)
            for line in stream.iter_lines():
                event = watch.feed(line)
                decision = _permission_reply(event, tool_executor)
                if event is not None and decision is not None:
                    self._client.session_permission_reply(self.id, event.properties["id"], decision)
                if watch.done:
                    break
                if time.monotonic() > deadline:
                    raise APITimeoutError(
                        f"No reply from session {self.id} within {poll_timeout}s",
                        request=stream.request,
                    )
            else:
                raise OpencodeError(f"Event stream closed before session {self.id} finished")

        reply = _build_reply(self._client.session_context(self.id), sent.id or "")
        if collect:
            from opencode._opencode import _extract_text

            return OpencodeResponse(text=_extract_text(reply), events=list(watch.events))
        return reply

    def ask(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        model: str | dict[str, str] | None = None,
        format: dict[str, Any] | None = None,
        tool_executor: ToolExecutor | None = None,
        quiet: bool = False,
        poll_timeout: float = 600.0,
        collect: bool = False,
    ) -> OpencodeResponse | SessionMessage:
        """Like :meth:`prompt`, answering permission requests with ``tool_executor``
        (default :class:`ToolExecutor`, which asks on the console before shell commands)."""
        return self.prompt(
            text,
            files=files,
            model=model,
            format=format,
            poll_timeout=poll_timeout,
            collect=collect,
            tool_executor=tool_executor or ToolExecutor(),
            quiet=quiet,
        )

    def info(self) -> SessionResponse:
        return self._client.session_get(self.id)

    def messages(self, **params: Any) -> PageResponse:
        return self._client.session_messages(self.id, **params)

    def context(self) -> list[SessionMessage]:
        return cast("list[SessionMessage]", self._client.session_context(self.id))

    def compact(self) -> Any:
        return self._client.session_compact(self.id)

    def abort(self) -> Any:
        return self._client.session_interrupt(self.id)

    def fork(self, *, before: str | None = None) -> SessionResponse:
        return self._client.session_fork(self.id, before=before)

    def diff(self) -> Any:
        return self._client.session_diff(self.id)

    def delete(self) -> None:
        self._client.session_delete(self.id)
