from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import httpx

from opencode._models import AssistantMessage
from opencode._opencode import (
    _extract_text,
    _opencode_state,
    _resolve_model,
    opencode,
)


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
