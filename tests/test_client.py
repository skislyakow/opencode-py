from __future__ import annotations

import base64
import json
from collections.abc import Callable

import httpx
import pytest

from opencode import APIError, AuthenticationError, OpencodeClient
from opencode._client import model_ref
from opencode._response_models import (
    FileSystemEntry,
    PageResponse,
    PromptResponse,
    RawResponse,
    ServerInfoResponse,
    SessionResponse,
)

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler, **kwargs: object) -> OpencodeClient:
    return OpencodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
        **kwargs,  # type: ignore[arg-type]
    )


def _json(data: object, status: int = 200, **kwargs: object) -> Handler:
    return lambda _: httpx.Response(status, json=data, **kwargs)  # type: ignore[arg-type]


def test_create_client_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    client = OpencodeClient()
    assert client.base_url == "http://127.0.0.1:4096"
    assert client.directory is None
    assert client.password is None


def test_create_client_with_options() -> None:
    client = OpencodeClient(
        base_url="http://localhost:8080/",
        directory="/home/user/project",
        password="secret",
        timeout=10.0,
    )
    assert client.base_url == "http://localhost:8080"
    assert client.directory == "/home/user/project"
    assert client.username == "opencode"
    assert client.password == "secret"


def test_password_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_SERVER_PASSWORD", "from-env")
    assert OpencodeClient().password == "from-env"


def test_basic_auth_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"version": "2.3.2", "pid": 1, "urls": [], "paths": {}})

    _client(handler, password="pw").health()
    expected = "Basic " + base64.b64encode(b"opencode:pw").decode()
    assert seen[0].headers["authorization"] == expected
    assert seen[0].url.path == "/api/info"


def test_health_success() -> None:
    client = _client(_json({"version": "2.3.2", "pid": 42, "urls": [], "paths": {"tmp": "/t"}}))
    result = client.health()
    assert isinstance(result, ServerInfoResponse)
    assert result.version == "2.3.2"
    assert result.pid == 42


def test_health_error() -> None:
    client = _client(_json({"message": "internal error"}, 500))
    with pytest.raises(APIError) as exc:
        client.health()
    assert exc.value.status == 500
    assert "internal error" in str(exc.value)


def test_unauthorized_raises_authentication_error() -> None:
    client = _client(_json({"_tag": "UnauthorizedError", "message": "Authentication required"}, 401))
    with pytest.raises(AuthenticationError):
        client.health()


def test_merge_params_directory() -> None:
    client = OpencodeClient(base_url="http://localhost:9999", directory="/proj")
    result = client._merge_params({"foo": "bar"})
    assert result == {"foo": "bar", "location[directory]": "/proj"}


def test_model_ref() -> None:
    assert model_ref(None) is None
    assert model_ref("anthropic/claude-x") == {"providerID": "anthropic", "id": "claude-x"}
    assert model_ref("big-pickle") == {"providerID": "opencode", "id": "big-pickle"}
    assert model_ref({"providerID": "p", "modelID": "m"}) == {"providerID": "p", "id": "m"}
    assert model_ref({"providerID": "p", "id": "m"}) == {"providerID": "p", "id": "m"}


def test_session_create_body_and_envelope() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {"id": "ses_1", "title": "t"}})

    client = _client(handler, directory="/proj")
    result = client.session_create(model="anthropic/claude-x", agent="build")
    assert isinstance(result, SessionResponse)
    assert result.id == "ses_1"
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/api/session"
    assert json.loads(seen[0].content) == {
        "model": {"providerID": "anthropic", "id": "claude-x"},
        "agent": "build",
        "location": {"directory": "/proj"},
    }


def test_session_prompt() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, json={"data": {"id": "msg_1", "type": "user", "payload": {"text": "hello"}}}
        )

    result = _client(handler).session_prompt("ses_1", "hello")
    assert isinstance(result, PromptResponse)
    assert result.id == "msg_1"
    assert seen[0].url.path == "/api/session/ses_1/prompt"
    assert json.loads(seen[0].content) == {"text": "hello"}


def test_session_wait_204() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    assert _client(handler).session_wait("ses_1") is None
    assert seen[0].url.path == "/api/experimental/session/ses_1/wait"


def test_session_list_paginated() -> None:
    client = _client(_json({"data": [{"id": "ses_1"}, {"id": "ses_2"}], "cursor": {"next": "c"}}))
    page = client.session_list(limit=2)
    assert isinstance(page, PageResponse)
    assert [s.id for s in page.data] == ["ses_1", "ses_2"]
    assert isinstance(page.data[0], SessionResponse)
    assert page.cursor == {"next": "c"}


def test_session_context_unwraps_list() -> None:
    client = _client(_json({"data": [{"id": "msg_1", "type": "user", "text": "hi"}]}))
    assert client.session_context("ses_1") == [{"id": "msg_1", "type": "user", "text": "hi"}]


def test_fs_list_with_location_envelope() -> None:
    client = _client(
        _json({"location": {"directory": "/proj"}, "data": [{"path": "a.py", "type": "file"}]})
    )
    result = client.fs_list()
    assert isinstance(result[0], FileSystemEntry)
    assert result[0].path == "a.py"


def test_fs_read_text() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="print('hello')", headers={"content-type": "text/plain"})

    assert _client(handler).fs_read("/src/file.py") == "print('hello')"
    assert seen[0].url.path == "/api/fs/read/src/file.py"


def test_event_subscribe_error_raises() -> None:
    client = _client(_json({"message": "Authentication required"}, 401))
    with pytest.raises(AuthenticationError):
        client.event_subscribe()


def test_copy_overrides() -> None:
    client = OpencodeClient(base_url="http://a", directory="/a", password="pw", timeout=5.0)
    copy = client.copy(directory="/b")
    assert copy.base_url == "http://a"
    assert copy.directory == "/b"
    assert copy.password == "pw"
    assert copy._timeout == 5.0


def test_close() -> None:
    client = OpencodeClient()
    client.close()


# ---------------------------------------------------------------------------
# with_raw_response
# ---------------------------------------------------------------------------

_INFO = {"version": "2.3.2", "pid": 1, "urls": [], "paths": {}}


def test_with_raw_response_parsed_model() -> None:
    client = _client(_json(_INFO))
    with client.with_raw_response:
        raw = client.health()
    assert isinstance(raw, RawResponse)
    assert isinstance(raw.parsed, ServerInfoResponse)
    assert raw.parsed.version == "2.3.2"


def test_with_raw_response_status_code() -> None:
    client = _client(_json(_INFO, 201))
    with client.with_raw_response:
        raw = client.health()
    assert raw.status_code == 201


def test_with_raw_response_headers() -> None:
    client = _client(_json(_INFO, headers={"x-custom": "test-val"}))
    with client.with_raw_response:
        raw = client.health()
    assert raw.headers["x-custom"] == "test-val"


def test_with_raw_response_content() -> None:
    client = _client(_json(_INFO))
    with client.with_raw_response:
        raw = client.health()
    assert b"version" in raw.content


def test_with_raw_response_204() -> None:
    client = _client(lambda _: httpx.Response(204))
    with client.with_raw_response:
        raw = client.session_compact("ses_1")
    assert isinstance(raw, RawResponse)
    assert raw.status_code == 204
    assert raw.parsed is None


def test_with_raw_response_mode_resets() -> None:
    client = _client(_json(_INFO))
    with client.with_raw_response:
        raw = client.health()
    assert isinstance(raw, RawResponse)
    normal = client.health()
    assert isinstance(normal, ServerInfoResponse)
    assert not isinstance(normal, RawResponse)


def test_with_raw_response_still_raises_error() -> None:
    client = _client(_json({"message": "boom"}, 500))
    with client.with_raw_response:
        with pytest.raises(APIError) as exc:
            client.health()
    assert exc.value.status == 500


def test_with_raw_response_cast_to_none() -> None:
    """Methods without cast_to still return RawResponse with the unwrapped data."""
    client = _client(_json({"data": {"foo": "bar"}}))
    with client.with_raw_response:
        raw = client.session_active()
    assert isinstance(raw, RawResponse)
    assert raw.parsed == {"foo": "bar"}
