from __future__ import annotations

import json
from typing import Any, cast
from unittest.mock import MagicMock, patch

import httpx
import pytest

from opencode import (
    AsyncOpendcode,
    AsyncOpendcodeClient,
    AsyncSession,
    Opencode,
    OpencodeClient,
    OpencodeError,
    ToolExecutor,
    parse_stream_event,
    parse_typed_event,
)
from opencode._models import AssistantMessage, SessionMessage
from opencode._opencode import _extract_text, _opencode_state, _resolve_model, opencode
from opencode._response_models import AsyncStreamResult, OpencodeResponse, StreamResult
from opencode._session import Session, _build_reply

SID = "ses_1"
PROMPT_ID = "msg_u"


def _event(type_: str, sid: str = SID, **data: Any) -> str:
    return "data: " + json.dumps({"id": "evt", "type": type_, "data": {"sessionID": sid, **data}})


def _sse(*lines: str) -> str:
    return "".join(f"{line}\n\n" for line in [": heartbeat", *lines])


TURN = [
    _event("session.inbox.enqueued", inboxID=PROMPT_ID),
    _event("session.execution.started"),
    _event("session.text.delta", sid="ses_other", delta="not mine"),
    _event("session.inbox.delivered", inboxID=PROMPT_ID),
    _event("session.reasoning.delta", delta="thinking"),
    _event("session.text.delta", delta="Hello"),
    _event("session.text.delta", delta=" world"),
    _event("session.execution.succeeded"),
]

CONTEXT = [
    {"id": "msg_old", "type": "user", "text": "earlier"},
    {"id": "msg_a0", "type": "assistant", "content": [{"type": "text", "text": "old reply"}]},
    {"id": PROMPT_ID, "type": "user", "text": "hi"},
    {
        "id": "msg_a1",
        "type": "assistant",
        "content": [
            {"type": "reasoning", "text": "thinking"},
            {"type": "text", "text": "Working on it"},
            {"type": "tool", "id": "t1", "name": "shell", "state": {"status": "completed"}},
        ],
    },
    {
        "id": "msg_a2",
        "type": "assistant",
        "content": [{"type": "text", "text": "Done"}],
        "finish": "stop",
    },
    {"id": "msg_idle", "type": "idle", "outcome": "succeeded"},
]


class FakeServer:
    """Routes requests the way the opencode v2 server would for one prompt."""

    def __init__(self, events: list[str], context: list[dict[str, Any]] | None = None):
        self.events = events
        self.context = CONTEXT if context is None else context
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/api/event":
            return httpx.Response(
                200, text=_sse(*self.events), headers={"content-type": "text/event-stream"}
            )
        if path.endswith("/prompt"):
            return httpx.Response(200, json={"data": {"id": PROMPT_ID, "type": "user"}})
        if path.endswith("/context"):
            return httpx.Response(200, json={"data": self.context})
        return httpx.Response(204)

    def paths(self) -> list[str]:
        return [f"{r.method} {r.url.path}" for r in self.requests]

    def body(self, path_suffix: str) -> Any:
        request = next(r for r in self.requests if r.url.path.endswith(path_suffix))
        return json.loads(request.content)


def _session(server: FakeServer) -> Session:
    client = OpencodeClient(
        base_url="http://test", httpx_client=httpx.Client(transport=httpx.MockTransport(server))
    )
    return Session(client, SID)


def _async_session(server: FakeServer) -> AsyncSession:
    client = AsyncOpendcodeClient(
        base_url="http://test",
        httpx_client=httpx.AsyncClient(transport=httpx.MockTransport(server)),
    )
    return AsyncSession(client, SID)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def test_resolve_model_default() -> None:
    assert _resolve_model() is None


def test_resolve_model_provider_model() -> None:
    assert _resolve_model(model="opencode/big-pickle") == {
        "providerID": "opencode",
        "id": "big-pickle",
    }


def test_resolve_model_model_overrides_config() -> None:
    assert _resolve_model(model="x/y", config={"model": "a/b"}) == {"providerID": "x", "id": "y"}
    assert _resolve_model(config={"model": "a/b"}) == {"providerID": "a", "id": "b"}


def test_extract_text_joins_text_parts_only() -> None:
    msg = cast(
        AssistantMessage,
        {
            "id": "m",
            "type": "assistant",
            "content": [
                {"type": "reasoning", "text": "hmm"},
                {"type": "text", "text": "a"},
                {"type": "tool", "id": "t", "name": "shell"},
                {"type": "text", "text": "b"},
            ],
            "time": {},
        },
    )
    assert _extract_text(msg) == "a\nb"


def test_build_reply_merges_assistant_messages_after_prompt() -> None:
    reply = _build_reply(CONTEXT, PROMPT_ID)
    assert reply["id"] == "msg_a2"
    assert reply["type"] == "assistant"
    assert _extract_text(reply) == "Working on it\nDone"
    assert [p["type"] for p in reply["content"]] == ["reasoning", "text", "tool", "text"]


def test_build_reply_without_assistant() -> None:
    reply = _build_reply([{"id": PROMPT_ID, "type": "user", "text": "hi"}], PROMPT_ID)
    assert reply["type"] == "assistant"
    assert reply["content"] == []


def test_parse_stream_event_v2_payload() -> None:
    event = parse_stream_event(
        json.dumps(
            {
                "id": "evt_1",
                "type": "session.text.delta",
                "location": {"directory": "/p"},
                "data": {"sessionID": SID, "delta": "x"},
            }
        )
    )
    assert event.type == "session.text.delta"
    assert event.properties == {"sessionID": SID, "delta": "x"}
    assert event.session_id == SID
    assert event.location == {"directory": "/p"}


def test_parse_typed_event_fills_defaults() -> None:
    event = parse_typed_event(json.dumps({"type": "session.text.delta", "data": {"sessionID": SID}}))
    assert event.properties["delta"] == ""


def test_tool_executor_decide() -> None:
    executor = ToolExecutor(
        permissions={"edit": "deny", "shell": "ask"}, confirm=lambda action, req: False
    )
    assert executor.decide({"action": "edit"}) == "reject"
    assert executor.decide({"action": "shell", "resources": ["ls"]}) == "reject"
    assert executor.decide({"action": "read"}) == "once"
    assert ToolExecutor(confirm=lambda a, r: True).decide({"action": "shell"}) == "once"


# ---------------------------------------------------------------------------
# Session.prompt (sync)
# ---------------------------------------------------------------------------


def test_session_prompt_returns_reply() -> None:
    server = FakeServer(TURN)
    result = _session(server).prompt("hi")
    assert isinstance(result, dict)
    assert result["type"] == "assistant"
    assert _extract_text(result) == "Working on it\nDone"
    assert server.paths() == [
        "GET /api/event",
        f"POST /api/session/{SID}/prompt",
        f"GET /api/session/{SID}/context",
    ]
    assert server.body("/prompt") == {"text": "hi"}


def test_session_prompt_collect() -> None:
    result = _session(FakeServer(TURN)).prompt("hi", collect=True)
    assert isinstance(result, OpencodeResponse)
    assert result.text == "Working on it\nDone"
    types = [e.type for e in result.events]
    assert types[0] == "session.inbox.enqueued"
    assert types[-1] == "session.execution.succeeded"
    assert all(e.session_id == SID for e in result.events)


def test_session_prompt_switches_model() -> None:
    server = FakeServer(TURN)
    _session(server).prompt("hi", model="anthropic/claude-x")
    assert server.paths()[0] == f"POST /api/session/{SID}/model"
    assert server.body("/model") == {"model": {"providerID": "anthropic", "id": "claude-x"}}


def test_session_prompt_ignores_finish_before_delivery() -> None:
    """A run that finishes before our prompt is delivered must not end the wait."""
    events = [
        _event("session.execution.succeeded"),
        _event("session.inbox.delivered", inboxID=PROMPT_ID),
        _event("session.execution.succeeded"),
    ]
    result = _session(FakeServer(events)).prompt("hi", collect=True)
    assert isinstance(result, OpencodeResponse)
    assert len(result.events) == 3


def test_session_prompt_execution_failed_raises() -> None:
    events = [
        _event("session.inbox.delivered", inboxID=PROMPT_ID),
        _event("session.execution.failed", error={"message": "provider exploded"}),
    ]
    with pytest.raises(OpencodeError, match="provider exploded"):
        _session(FakeServer(events)).prompt("hi")


def test_session_prompt_stream_closed_raises() -> None:
    events = [_event("session.inbox.delivered", inboxID=PROMPT_ID)]
    with pytest.raises(OpencodeError, match="closed"):
        _session(FakeServer(events)).prompt("hi")


def _permission_turn() -> list[str]:
    return [
        _event("session.inbox.delivered", inboxID=PROMPT_ID),
        _event("permission.asked", id="per_1", action="shell", resources=["rm -rf /"]),
        _event("session.execution.succeeded"),
    ]


def test_session_prompt_rejects_permission_without_executor() -> None:
    server = FakeServer(_permission_turn())
    _session(server).prompt("hi")
    assert f"POST /api/session/{SID}/permission/per_1/reply" in server.paths()
    assert server.body("/reply") == {"decision": "reject"}


def test_session_ask_answers_permission_with_executor() -> None:
    server = FakeServer(_permission_turn())
    _session(server).ask("hi", tool_executor=ToolExecutor(confirm=lambda a, r: True), quiet=True)
    assert server.body("/reply") == {"decision": "once"}


def test_session_prompt_no_wait_returns_user_message() -> None:
    server = FakeServer([])
    result = _session(server).prompt("hi", wait=False)
    assert result["type"] == "user"
    assert result["id"] == PROMPT_ID
    assert server.paths() == [f"POST /api/session/{SID}/prompt"]


def test_session_prompt_format_not_supported() -> None:
    with pytest.raises(OpencodeError, match="Structured output"):
        _session(FakeServer(TURN)).prompt("hi", format={"type": "json_schema", "schema": {}})


# ---------------------------------------------------------------------------
# AsyncSession.prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_session_prompt_returns_reply() -> None:
    server = FakeServer(TURN)
    result = await _async_session(server).prompt("hi")
    assert isinstance(result, dict)
    assert _extract_text(result) == "Working on it\nDone"
    assert server.paths()[1] == f"POST /api/session/{SID}/prompt"


@pytest.mark.asyncio
async def test_async_session_prompt_collect_and_permission() -> None:
    server = FakeServer(_permission_turn())
    result = await _async_session(server).prompt("hi", collect=True)
    assert isinstance(result, OpencodeResponse)
    assert server.body("/reply") == {"decision": "reject"}
    assert [e.type for e in result.events][-1] == "session.execution.succeeded"


# ---------------------------------------------------------------------------
# ask_stream
# ---------------------------------------------------------------------------


def _opencode_with(server: FakeServer) -> Opencode:
    ai = Opencode(model="opencode/big-pickle")
    ai._client = OpencodeClient(
        base_url="http://test", httpx_client=httpx.Client(transport=httpx.MockTransport(server))
    )
    ai._server = MagicMock()
    return ai


def test_ask_stream_yields_text_deltas_only() -> None:
    ai = _opencode_with(FakeServer(TURN))
    session = Session(ai.client, SID)
    assert list(ai.ask_stream("hi", session=session)) == ["Hello", " world"]


def test_ask_stream_collect_returns_stream_result() -> None:
    ai = _opencode_with(FakeServer(TURN))
    stream = ai.ask_stream("hi", session=Session(ai.client, SID), collect=True)
    assert isinstance(stream, StreamResult)
    assert list(stream) == ["Hello", " world"]
    assert stream.text == "Hello world"
    assert len(stream.events) == len(TURN) - 1  # other-session event excluded


@pytest.mark.asyncio
async def test_async_ask_stream_collect() -> None:
    server = FakeServer(TURN)
    ai = AsyncOpendcode(model="opencode/big-pickle")
    ai._client = AsyncOpendcodeClient(
        base_url="http://test",
        httpx_client=httpx.AsyncClient(transport=httpx.MockTransport(server)),
    )
    ai._server = MagicMock()
    stream = ai.ask_stream("hi", session=AsyncSession(ai.client, SID), collect=True)
    assert isinstance(stream, AsyncStreamResult)
    chunks = [chunk async for chunk in stream]
    assert chunks == ["Hello", " world"]
    assert stream.text == "Hello world"


@pytest.mark.asyncio
async def test_async_ask_stream_plain() -> None:
    ai = AsyncOpendcode()
    ai._client = AsyncOpendcodeClient(
        base_url="http://test",
        httpx_client=httpx.AsyncClient(transport=httpx.MockTransport(FakeServer(TURN))),
    )
    ai._server = MagicMock()
    result = ai.ask_stream("hi", session=AsyncSession(ai.client, SID))
    assert not isinstance(result, AsyncStreamResult)
    assert [chunk async for chunk in result] == ["Hello", " world"]


# ---------------------------------------------------------------------------
# Opencode.create_session / opencode()
# ---------------------------------------------------------------------------


def test_create_session_uses_instance_model() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {"id": "ses_9"}})

    ai = Opencode(model="anthropic/claude-x")
    ai._client = OpencodeClient(
        base_url="http://test", httpx_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    ai._server = MagicMock()
    session = ai.create_session(agent="build")
    assert session.id == "ses_9"
    assert json.loads(seen[0].content) == {
        "model": {"providerID": "anthropic", "id": "claude-x"},
        "agent": "build",
    }


def _mock_ai(reply: SessionMessage | OpencodeResponse) -> tuple[MagicMock, MagicMock]:
    mock_ai = MagicMock()
    mock_session = MagicMock()
    mock_session.prompt.return_value = reply
    mock_ai.create_session.return_value = mock_session
    return mock_ai, mock_session


_REPLY = cast(
    SessionMessage,
    {"id": "m", "type": "assistant", "content": [{"type": "text", "text": "answer"}], "time": {}},
)


def test_opencode_keep_reuses_session() -> None:
    _opencode_state.clear()
    mock_ai, mock_session = _mock_ai(_REPLY)
    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        assert opencode("hello", keep=True) == "answer"
        assert opencode("world", keep=True) == "answer"
    assert mock_ai.create_session.call_count == 1
    assert mock_session.prompt.call_count == 2
    assert mock_ai.close.call_count == 0
    _opencode_state.clear()


def test_opencode_keep_false_closes() -> None:
    _opencode_state.clear()
    mock_ai, mock_session = _mock_ai(_REPLY)
    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        assert opencode("question") == "answer"
    mock_ai.close.assert_called_once()
    assert not _opencode_state


def test_opencode_collect_true() -> None:
    _opencode_state.clear()
    mock_ai, _ = _mock_ai(OpencodeResponse(text="answer from mock"))
    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        result = opencode("test", collect=True)
    assert isinstance(result, OpencodeResponse)
    assert result.text == "answer from mock"
    mock_ai.close.assert_called_once()
    assert not _opencode_state
