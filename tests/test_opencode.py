from __future__ import annotations

from unittest.mock import MagicMock, patch

from opencode._opencode import _extract_text, _opencode_state, _resolve_model, opencode


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
    msg = {
        "id": "msg_1",
        "type": "assistant",
        "content": [],
        "structured": {"name": "Alice", "age": 30},
    }
    result = _extract_text(msg)
    assert result == '{"name": "Alice", "age": 30}'


def test_extract_text_structured_fallback() -> None:
    msg = {
        "id": "msg_2",
        "type": "assistant",
        "content": [{"type": "text", "text": "hello"}],
    }
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
        r = opencode("get name", format={"type": "json_schema", "schema": schema})

    assert r == '{"name": "Alice"}'
    mock_session.prompt.assert_called_once()
    _, kwargs = mock_session.prompt.call_args
    assert kwargs["format"] == {"type": "json_schema", "schema": schema}

    _opencode_state.clear()
