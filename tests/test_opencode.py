from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from opencode import OpencodeClient
from opencode._models import AssistantMessage, SessionMessage
from opencode._opencode import (
    _extract_text,
    _opencode_state,
    _resolve_model,
    opencode,
)
from opencode._response_models import OpencodeResponse
from opencode._session import Session


def test_resolve_model_default() -> None:
    assert _resolve_model() is None


def test_resolve_model_provider_model() -> None:
    assert _resolve_model(model="opencode/big-pickle") == {
        "providerID": "opencode",
        "modelID": "big-pickle",
    }


def test_resolve_model_from_config() -> None:
    assert _resolve_model(config={"model": "foo/bar"}) == {
        "providerID": "foo",
        "modelID": "bar",
    }


def test_resolve_model_model_overrides_config() -> None:
    assert _resolve_model(model="x/y", config={"model": "a/b"}) == {
        "providerID": "x",
        "modelID": "y",
    }


def test_opencode_keep_reuses_session() -> None:
    _opencode_state.clear()

    mock_ai = MagicMock()
    mock_ai.start = MagicMock()
    mock_ai.close = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "ses_keep"
    mock_session.prompt.return_value = {
        "type": "assistant",
        "content": [{"type": "text", "text": "answer1"}],
    }
    mock_ai.create_session.return_value = mock_session

    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        r1 = opencode("hello", keep=True)
        r2 = opencode("world", keep=True)

    assert r1 == "answer1"
    assert r2 == "answer1"
    assert mock_ai.create_session.call_count == 1
    assert mock_session.prompt.call_count == 2
    assert mock_ai.close.call_count == 0

    _opencode_state.clear()


def test_opencode_keep_false_closes() -> None:
    _opencode_state.clear()

    mock_ai = MagicMock()
    mock_ai.start = MagicMock()
    mock_ai.close = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "ses_close"
    mock_session.prompt.return_value = {
        "type": "assistant",
        "content": [{"type": "text", "text": "answer"}],
    }
    mock_ai.create_session.return_value = mock_session

    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        r = opencode("question")

    assert r == "answer"
    assert mock_ai.create_session.call_count == 1
    assert mock_session.prompt.call_count == 1
    mock_ai.close.assert_called_once()
    assert not _opencode_state

    _opencode_state.clear()


def test_extract_text_structured() -> None:
    msg = cast(
        AssistantMessage,
        {
            "id": "msg_1",
            "type": "assistant",
            "content": [],
            "structured": {"name": "Alice", "age": 30},
        },
    )
    result = _extract_text(msg)
    assert result == '{"name": "Alice", "age": 30}'


def test_extract_text_structured_fallback() -> None:
    msg = cast(
        AssistantMessage,
        {
            "id": "msg_2",
            "type": "assistant",
            "content": [{"type": "text", "text": "hello"}],
        },
    )
    result = _extract_text(msg)
    assert result == "hello"


def test_opencode_with_format() -> None:
    _opencode_state.clear()

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    mock_ai = MagicMock()
    mock_ai.start = MagicMock()
    mock_ai.close = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "ses_fmt"
    mock_session.prompt.return_value = {
        "id": "msg_1",
        "type": "assistant",
        "content": [],
        "structured": {"name": "Alice"},
    }
    mock_ai.create_session.return_value = mock_session

    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        r = opencode(
            "get name", format={"type": "json_schema", "schema": schema}
        )

    assert r == '{"name": "Alice"}'
    mock_session.prompt.assert_called_once()
    _, kwargs = mock_session.prompt.call_args
    assert kwargs["format"] == {"type": "json_schema", "schema": schema}

    _opencode_state.clear()


# ---------------------------------------------------------------------------
# ask_stream
# ---------------------------------------------------------------------------


def _make_sse_response(events: list[str]) -> httpx.Response:
    """Build an httpx.Response with SSE-formatted body for testing."""
    return httpx.Response(200, text="".join(events))


def test_ask_stream_filters_reasoning() -> None:
    from opencode import Opencode

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_user","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_reason","type":"reasoning"}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_reason","delta":"thinking step 1"}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_reason","delta":"thinking step 2"}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_reason","type":"reasoning","text":"thinking step 1thinking step 2"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_text","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_text","delta":"Hello"}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_text","delta":" world"}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_text","type":"text","text":"Hello world"}}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    chunks = list(ai.ask_stream("hello", session=session))

    assert chunks == ["Hello", " world"]


def test_ask_stream_no_reasoning() -> None:
    from opencode import Opencode

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_user","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_text","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_text","delta":"Hi"}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_text","delta":" there"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    chunks = list(ai.ask_stream("hello", session=session))

    assert chunks == ["Hi", " there"]


def test_ask_stream_only_reasoning_yields_nothing() -> None:
    from opencode import Opencode

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_user","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_r","type":"reasoning"}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_r","delta":"thinking"}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_r","type":"reasoning","text":"thinking"}}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    chunks = list(ai.ask_stream("hello", session=session))

    assert chunks == []


def test_ask_stream_no_user_echo() -> None:
    """User's text part should never be yielded."""
    from opencode import Opencode

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_user","type":"text","text":"hello there"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_t","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_t","delta":"Response"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    chunks = list(ai.ask_stream("hello", session=session))

    assert chunks == ["Response"]


def test_ask_stream_other_session_skipped() -> None:
    from opencode import Opencode

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_other","part":{"id":"p_t","type":"text","text":"other"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_t","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_t","delta":"Mine"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    chunks = list(ai.ask_stream("hello", session=session))

    assert chunks == ["Mine"]


def test_ask_stream_no_deltas_falls_back_to_part_text() -> None:
    """If no deltas arrive, yield from message.part.updated full text."""
    from opencode import Opencode

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_u","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_t","type":"text","text":"Full response"}}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    chunks = list(ai.ask_stream("hello", session=session))

    assert chunks == ["Full response"]


def test_ask_stream_collect_true_returns_stream_result() -> None:
    """ask_stream(collect=True) returns StreamResult with events + text."""
    from opencode import Opencode
    from opencode._response_models import StreamResult

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_u","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_t","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_t","delta":"Hello"}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_t","delta":" world"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    stream = ai.ask_stream("hello", session=session, collect=True)

    assert isinstance(stream, StreamResult)
    chunks = list(stream)
    assert chunks == ["Hello", " world"]
    assert stream.text == "Hello world"
    # 7 SSE lines = 7 events collected
    assert len(stream.events) == 7
    # First event should be message.updated
    assert stream.events[0].type == "message.updated"


def test_ask_stream_collect_no_events_when_no_events_yielded() -> None:
    """collect=True with no events still works."""
    from opencode import Opencode
    from opencode._response_models import StreamResult

    session = MagicMock()
    session.id = "ses_1"

    # Only non-data lines (should be ignored)
    response = httpx.Response(200, text="not data\nnothing here\n")
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = response
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    stream = ai.ask_stream("hello", session=session, collect=True)

    assert isinstance(stream, StreamResult)
    chunks = list(stream)
    assert chunks == []
    assert stream.text == ""
    assert stream.events == []


def test_ask_stream_collect_false_backward_compat() -> None:
    """ask_stream(collect=False) behaves like old ask_stream (no events)."""
    from opencode import Opencode
    from opencode._response_models import StreamResult

    session = MagicMock()
    session.id = "ses_1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_u","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_1","part":{"id":"p_t","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_t","delta":"Hi"}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_1","partID":"p_t","delta":" there"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe.return_value = _make_sse_response(events)
    mock_client.session_send.return_value = MagicMock()

    ai = Opencode(model="opencode/big-pickle")
    ai._client = mock_client
    result = ai.ask_stream("hello", session=session, collect=False)

    # Should be a raw generator/iterator, not StreamResult
    assert not isinstance(result, StreamResult)
    chunks = list(result)
    assert chunks == ["Hi", " there"]


# ---------------------------------------------------------------------------
# collect parameter
# ---------------------------------------------------------------------------


def test_session_prompt_v2_collect_true() -> None:
    """V2 path: collect=True returns OpencodeResponse with text."""
    session = Session(MagicMock(), "ses_1")
    v2_msg = cast(
        SessionMessage,
        {
            "id": "msg_1",
            "type": "assistant",
            "content": [{"type": "text", "text": "Hello from V2"}],
            "time": {},
        },
    )
    with patch.object(session, "_prompt_v2", return_value=v2_msg):
        result = session.prompt("hi", collect=True)
    assert isinstance(result, OpencodeResponse)
    assert result.text == "Hello from V2"
    assert result.events == []


def test_session_prompt_v2_collect_false() -> None:
    """V2 path: collect=False returns SessionMessage."""
    session = Session(MagicMock(), "ses_1")
    v2_msg = cast(
        SessionMessage,
        {
            "id": "msg_1",
            "type": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
            "time": {},
        },
    )
    with patch.object(session, "_prompt_v2", return_value=v2_msg):
        result = session.prompt("hi", collect=False)
    assert isinstance(result, dict)
    assert result["type"] == "assistant"


def test_session_prompt_v1_collect_true() -> None:
    """V1 path (with model): collect=True returns OpencodeResponse."""
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "parts": [{"type": "text", "text": "Hello V1"}],
                        "info": {"id": "msg_1", "time": {}},
                    },
                )
            )
        ),
    )
    session = Session(client, "ses_1")
    result = session.prompt(
        "hi", model={"providerID": "opencode", "modelID": "big-pickle"}, collect=True
    )
    assert isinstance(result, OpencodeResponse)
    assert result.text == "Hello V1"
    assert result.events == []


def test_session_prompt_v1_collect_false() -> None:
    """V1 path (with model): collect=False returns SessionMessage."""
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "parts": [{"type": "text", "text": "Hello V1"}],
                        "info": {"id": "msg_1", "time": {}},
                    },
                )
            )
        ),
    )
    session = Session(client, "ses_1")
    result = session.prompt(
        "hi", model={"providerID": "opencode", "modelID": "big-pickle"}, collect=False
    )
    assert isinstance(result, dict)
    assert result["type"] == "assistant"


def test_opencode_collect_true() -> None:
    """opencode(collect=True) returns OpencodeResponse."""
    _opencode_state.clear()

    mock_ai = MagicMock()
    mock_ai.start = MagicMock()
    mock_ai.close = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "ses_collect"
    mock_session.prompt.return_value = OpencodeResponse(text="answer from mock")
    mock_ai.create_session.return_value = mock_session

    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        result = opencode("test", collect=True)

    assert isinstance(result, OpencodeResponse)
    assert result.text == "answer from mock"
    mock_ai.close.assert_called_once()
    assert not _opencode_state
    _opencode_state.clear()


def test_opencode_collect_false_default() -> None:
    """opencode() without collect returns bare string (default)."""
    _opencode_state.clear()

    mock_ai = MagicMock()
    mock_ai.start = MagicMock()
    mock_ai.close = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "ses_no_collect"
    mock_session.prompt.return_value = {
        "id": "msg_1",
        "type": "assistant",
        "content": [{"type": "text", "text": "bare string"}],
        "time": {},
    }
    mock_ai.create_session.return_value = mock_session

    with patch("opencode._opencode.Opencode", return_value=mock_ai):
        result = opencode("test")

    assert isinstance(result, str)
    assert result == "bare string"
    mock_ai.close.assert_called_once()
    assert not _opencode_state
    _opencode_state.clear()


# ---------------------------------------------------------------------------
# ask_stream collect — async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_stream_async_collect_true() -> None:
    """Async ask_stream(collect=True) returns AsyncStreamResult with events."""
    from opencode import AsyncOpendcode
    from opencode._response_models import AsyncStreamResult

    session = MagicMock()
    session.id = "ses_a1"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_a1","part":{"id":"p_u","type":"text","text":"hi"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_a1","part":{"id":"p_t","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_a1","partID":"p_t","delta":"Hello"}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_a1","partID":"p_t","delta":" async"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe = AsyncMock(return_value=_make_sse_response(events))
    mock_client.session_send = AsyncMock()
    mock_client.session_create = AsyncMock()

    ai = AsyncOpendcode(model="opencode/big-pickle")
    ai._client = mock_client
    ai._server = MagicMock()

    stream = ai.ask_stream("hello", session=session, collect=True)
    assert isinstance(stream, AsyncStreamResult)

    chunks: list[str] = []
    async for chunk in stream:
        chunks.append(chunk)
    assert chunks == ["Hello", " async"]
    assert stream.text == "Hello async"
    assert len(stream.events) == 7


@pytest.mark.asyncio
async def test_ask_stream_async_collect_false() -> None:
    """Async ask_stream(collect=False) is not AsyncStreamResult."""
    from opencode import AsyncOpendcode
    from opencode._response_models import AsyncStreamResult

    session = MagicMock()
    session.id = "ses_a2"

    events = [
        'data: {"type":"message.updated","properties":{"info":{"role":"user"}}}\n\n',
        'data: {"type":"message.updated","properties":{"info":{"role":"assistant"}}}\n\n',
        'data: {"type":"message.part.updated","properties":{"sessionID":"ses_a2","part":{"id":"p_t","type":"text","text":""}}}\n\n',
        'data: {"type":"message.part.delta","properties":{"sessionID":"ses_a2","partID":"p_t","delta":"Hi"}}\n\n',
        'data: {"type":"session.status","properties":{"status":{"type":"idle"}}}\n\n',
    ]
    mock_client = MagicMock()
    mock_client.event_subscribe = AsyncMock(return_value=_make_sse_response(events))
    mock_client.session_send = AsyncMock()
    mock_client.session_create = AsyncMock()

    ai = AsyncOpendcode(model="opencode/big-pickle")
    ai._client = mock_client
    ai._server = MagicMock()

    result = ai.ask_stream("hello", session=session, collect=False)
    assert not isinstance(result, AsyncStreamResult)
    chunks: list[str] = []
    async for chunk in result:
        chunks.append(chunk)
    assert chunks == ["Hi"]
