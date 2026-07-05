from __future__ import annotations

import httpx
import pytest

from opencode import APIError, OpencodeClient
from opencode._response_models import (
    FileContentResponse,
    HealthResponse,
    RawResponse,
    SessionResponse,
    V1SessionResponse,
)


def test_create_client_defaults() -> None:
    client = OpencodeClient()
    assert client.base_url == "http://127.0.0.1:4096"
    assert client.directory is None
    assert client.workspace is None


def test_create_client_with_options() -> None:
    client = OpencodeClient(
        base_url="http://localhost:8080",
        directory="/home/user/project",
        workspace="ws-1",
        timeout=10.0,
    )
    assert client.base_url == "http://localhost:8080"
    assert client.directory == "/home/user/project"
    assert client.workspace == "ws-1"


def test_health_success() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True}))
        ),
    )
    result = client.health()
    assert isinstance(result, HealthResponse)
    assert result.ok is True


def test_health_error() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(500, json={"message": "internal error"})
            )
        ),
    )
    with pytest.raises(APIError) as exc:
        client.health()
    assert exc.value.status == 500
    assert "internal error" in str(exc.value)


def test_merge_params_directory() -> None:
    client = OpencodeClient(base_url="http://localhost:9999", directory="/proj")
    result = client._merge_params({"foo": "bar"})
    assert result == {"foo": "bar", "directory": "/proj"}


def test_merge_params_workspace() -> None:
    client = OpencodeClient(base_url="http://localhost:9999", workspace="ws-1")
    result = client._merge_params({})
    assert result == {"workspace": "ws-1"}


def test_v2_session_prompt() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"id": "msg_1", "type": "assistant"})
            )
        ),
    )
    result = client.v2_session_prompt("ses_1", {"text": "hello"})
    assert isinstance(result, V1SessionResponse)
    assert result.id == "msg_1"
    assert result.type == "assistant"


def test_v2_session_wait_204() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(204))),
    )
    result = client.v2_session_wait("ses_1")
    assert result is None


def test_close() -> None:
    client = OpencodeClient()
    client.close()


def test_session_create() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"id": "ses_1"}))
        ),
    )
    result = client.session_create()
    assert isinstance(result, SessionResponse)
    assert result.id == "ses_1"


def test_file_read() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"content": "print('hello')"})
            )
        ),
    )
    result = client.file_read("/path/to/file.py")
    assert isinstance(result, FileContentResponse)
    assert result.content == "print('hello')"


# ---------------------------------------------------------------------------
# with_raw_response
# ---------------------------------------------------------------------------


def test_with_raw_response_parsed_model() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True}))
        ),
    )
    with client.with_raw_response:
        raw = client.health()
    assert isinstance(raw, RawResponse)
    assert isinstance(raw.parsed, HealthResponse)
    assert raw.parsed.ok is True


def test_with_raw_response_status_code() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(201, json={"ok": True}))
        ),
    )
    with client.with_raw_response:
        raw = client.health()
    assert raw.status_code == 201


def test_with_raw_response_headers() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={"ok": True},
                    headers={"x-custom": "test-val"},
                )
            )
        ),
    )
    with client.with_raw_response:
        raw = client.health()
    assert raw.headers["x-custom"] == "test-val"


def test_with_raw_response_content() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"ok": True})
            )
        ),
    )
    with client.with_raw_response:
        raw = client.health()
    assert raw.content is not None
    assert b"ok" in raw.content


def test_with_raw_response_204() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(204))
        ),
    )
    with client.with_raw_response:
        raw = client.v2_session_wait("ses_1")
    assert isinstance(raw, RawResponse)
    assert raw.status_code == 204
    assert raw.parsed is None


def test_with_raw_response_mode_resets() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True}))
        ),
    )
    # Inside context — returns RawResponse
    with client.with_raw_response:
        raw = client.health()
    assert isinstance(raw, RawResponse)
    # After context — returns normal model
    normal = client.health()
    assert isinstance(normal, HealthResponse)
    assert not isinstance(normal, RawResponse)


def test_with_raw_response_still_raises_error() -> None:
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(500, json={"message": "boom"})
            )
        ),
    )
    with client.with_raw_response:
        with pytest.raises(APIError) as exc:
            client.health()
    assert exc.value.status == 500


def test_with_raw_response_cast_to_none() -> None:
    """Methods without cast_to should still return RawResponse with raw parsed data."""
    client = OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"foo": "bar"}))
        ),
    )
    with client.with_raw_response:
        raw = client.global_dispose()
    assert isinstance(raw, RawResponse)
    assert raw.parsed == {"foo": "bar"}
