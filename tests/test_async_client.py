from __future__ import annotations

import base64
import json
from collections.abc import Callable

import httpx
import pytest

from opencode import APIError, AsyncOpendcodeClient, AuthenticationError
from opencode._response_models import (
    FileSystemEntry,
    PageResponse,
    PromptResponse,
    RawResponse,
    ServerInfoResponse,
    SessionResponse,
)

Handler = Callable[[httpx.Request], httpx.Response]
_INFO = {"version": "2.3.2", "pid": 1, "urls": [], "paths": {}}


def _client(handler: Handler, **kwargs: object) -> AsyncOpendcodeClient:
    return AsyncOpendcodeClient(
        base_url="http://localhost:9999",
        httpx_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        **kwargs,  # type: ignore[arg-type]
    )


def _json(data: object, status: int = 200, **kwargs: object) -> Handler:
    return lambda _: httpx.Response(status, json=data, **kwargs)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_client_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    client = AsyncOpendcodeClient()
    assert client.base_url == "http://127.0.0.1:4096"
    assert client.directory is None
    assert client.password is None


@pytest.mark.asyncio
async def test_basic_auth_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_INFO)

    result = await _client(handler, password="pw").health()
    assert isinstance(result, ServerInfoResponse)
    expected = "Basic " + base64.b64encode(b"opencode:pw").decode()
    assert seen[0].headers["authorization"] == expected
    assert seen[0].url.path == "/api/info"


@pytest.mark.asyncio
async def test_health_error() -> None:
    client = _client(_json({"message": "internal error"}, 500))
    with pytest.raises(APIError) as exc:
        await client.health()
    assert exc.value.status == 500
    assert "internal error" in str(exc.value)


@pytest.mark.asyncio
async def test_merge_params_directory() -> None:
    client = AsyncOpendcodeClient(base_url="http://localhost:9999", directory="/proj")
    assert client._merge_params({}) == {"location[directory]": "/proj"}


@pytest.mark.asyncio
async def test_session_create_body_and_envelope() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {"id": "ses_1"}})

    result = await _client(handler, directory="/proj").session_create(model="p/m")
    assert isinstance(result, SessionResponse)
    assert result.id == "ses_1"
    assert seen[0].url.path == "/api/session"
    assert json.loads(seen[0].content) == {
        "model": {"providerID": "p", "id": "m"},
        "location": {"directory": "/proj"},
    }


@pytest.mark.asyncio
async def test_session_prompt() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {"id": "msg_1", "type": "user"}})

    result = await _client(handler).session_prompt("ses_1", "hello")
    assert isinstance(result, PromptResponse)
    assert result.id == "msg_1"
    assert seen[0].url.path == "/api/session/ses_1/prompt"
    assert json.loads(seen[0].content) == {"text": "hello"}


@pytest.mark.asyncio
async def test_session_wait_204() -> None:
    assert await _client(lambda _: httpx.Response(204)).session_wait("ses_1") is None


@pytest.mark.asyncio
async def test_session_list_paginated() -> None:
    client = _client(_json({"data": [{"id": "ses_1"}], "cursor": {"next": None}}))
    page = await client.session_list()
    assert isinstance(page, PageResponse)
    assert isinstance(page.data[0], SessionResponse)
    assert page.data[0].id == "ses_1"


@pytest.mark.asyncio
async def test_fs_list_with_location_envelope() -> None:
    client = _client(_json({"location": {"directory": "/p"}, "data": [{"path": "a.py"}]}))
    result = await client.fs_list()
    assert isinstance(result[0], FileSystemEntry)
    assert result[0].path == "a.py"


@pytest.mark.asyncio
async def test_event_subscribe_error_raises() -> None:
    client = _client(_json({"message": "Authentication required"}, 401))
    with pytest.raises(AuthenticationError):
        await client.event_subscribe()


@pytest.mark.asyncio
async def test_close() -> None:
    client = AsyncOpendcodeClient()
    await client.close()


@pytest.mark.asyncio
async def test_with_raw_response_parsed_model() -> None:
    client = _client(_json(_INFO, headers={"x-custom": "v"}))
    with client.with_raw_response:
        raw = await client.health()
    assert isinstance(raw, RawResponse)
    assert isinstance(raw.parsed, ServerInfoResponse)
    assert raw.headers["x-custom"] == "v"


@pytest.mark.asyncio
async def test_with_raw_response_204() -> None:
    client = _client(lambda _: httpx.Response(204))
    with client.with_raw_response:
        raw = await client.session_compact("ses_1")
    assert isinstance(raw, RawResponse)
    assert raw.status_code == 204
    assert raw.parsed is None


@pytest.mark.asyncio
async def test_with_raw_response_mode_resets() -> None:
    client = _client(_json(_INFO))
    with client.with_raw_response:
        raw = await client.health()
    assert isinstance(raw, RawResponse)
    assert isinstance(await client.health(), ServerInfoResponse)
