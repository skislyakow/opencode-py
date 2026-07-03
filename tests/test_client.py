from __future__ import annotations

import httpx
import pytest

from opencode import APIError, OpencodeClient
from opencode._response_models import FileContentResponse, HealthResponse, SessionResponse


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
    assert result == {"id": "msg_1", "type": "assistant"}


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
