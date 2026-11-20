from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, cast

import httpx
from pydantic import BaseModel, ConfigDict

_T = TypeVar("_T")


class StreamResult:
    """Wraps ``ask_stream(collect=True)`` iteration.

    Iterate for text chunks, then access ``.events`` for all raw SSE events
    and ``.text`` for the full response.

    Example::

        stream = ai.ask_stream("hello", collect=True)
        for chunk in stream:
            print(chunk, end="")
        # After consumption:
        print(stream.events)   # list[StreamEvent]
        print(stream.text)     # full text
    """

    def __init__(self, gen: Iterator[Any]) -> None:
        self._gen = gen
        self.events: list[Any] = []
        self._text: str | None = None
        self._chunks: list[str] = []

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        if self._text is not None:
            raise StopIteration
        while True:
            try:
                item = next(self._gen)
            except StopIteration:
                self._text = "".join(self._chunks)
                raise
            if isinstance(item, tuple) and len(item) == 2 and item[0] == "event":
                self.events.append(item[1])
            else:
                chunk = cast(str, item)
                self._chunks.append(chunk)
                return chunk

    @property
    def text(self) -> str:
        if self._text is None:
            for _ in self:
                pass
        return self._text or ""


class AsyncStreamResult:
    """Async version of ``StreamResult`` for ``ask_stream(collect=True)``.

    Example::

        stream = ai.ask_stream("hello", collect=True)
        async for chunk in stream:
            print(chunk, end="")
        # After consumption:
        print(stream.events)   # list[StreamEvent]
        print(stream.text)     # full text (sync access after iteration)
    """

    def __init__(self, gen: AsyncIterator[Any]) -> None:
        self._gen = gen
        self.events: list[Any] = []
        self._text: str | None = None
        self._chunks: list[str] = []

    def __aiter__(self) -> AsyncStreamResult:
        return self

    async def __anext__(self) -> str:
        if self._text is not None:
            raise StopAsyncIteration
        while True:
            try:
                item = await self._gen.__anext__()
            except StopAsyncIteration:
                self._text = "".join(self._chunks)
                raise
            if isinstance(item, tuple) and len(item) == 2 and item[0] == "event":
                self.events.append(item[1])
            else:
                chunk = cast(str, item)
                self._chunks.append(chunk)
                return chunk

    @property
    def text(self) -> str:
        if self._text is None:
            raise RuntimeError(
                "Consume the async stream first (e.g. ``async for chunk in stream``) "
                "before accessing .text"
            )
        return self._text


class RawResponse(Generic[_T]):
    """Wraps a parsed response with the raw httpx.Response for direct access.

    Used with the ``with_raw_response`` context manager on the client::

        with client.with_raw_response:
            raw = client.health()
        raw.status_code  # 200
        raw.headers      # httpx.Headers
        raw.parsed       # HealthResponse
    """

    def __init__(self, parsed: _T, response: httpx.Response) -> None:
        self.parsed = parsed
        self._response: httpx.Response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> httpx.Headers:
        return self._response.headers

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def response(self) -> httpx.Response:
        return self._response


@dataclass
class OpencodeResponse:
    """Dataclass wrapping the assistant's text response and all raw SSE events.

    Returned by ``Session.prompt(collect=True)`` or ``Session.ask(collect=True)``.
    """

    text: str = ""
    events: list[Any] = field(default_factory=list)


class OpencodeBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ---------------------------------------------------------------------------
# opencode v2 API models — generated from the server's /openapi.json.
# All fields are optional; unknown fields are kept (extra="allow").
# ---------------------------------------------------------------------------


class PageResponse(OpencodeBaseModel):
    """Paginated list: ``data`` items plus ``cursor`` (``previous``/``next``)."""

    data: list[Any] = []
    cursor: dict[str, Any] | None = None


class ServerInfoResponse(OpencodeBaseModel):
    """GET /api/info"""

    version: str | None = None
    pid: int | None = None
    hostname: str | None = None
    urls: list[Any] | None = None
    paths: dict[str, Any] | None = None
    capabilities: dict[str, Any] | None = None


class LocationResponse(OpencodeBaseModel):
    """GET /api/location"""

    directory: str | None = None
    project: dict[str, Any] | None = None


class SessionResponse(OpencodeBaseModel):
    """Session.Info"""

    id: str | None = None
    parentID: str | None = None
    fork: dict[str, Any] | None = None
    projectID: str | None = None
    agent: str | None = None
    model: dict[str, Any] | None = None
    cost: float | None = None
    tokens: dict[str, Any] | None = None
    outcome: str | None = None
    time: dict[str, Any] | None = None
    title: str | None = None
    subpath: str | None = None
    metadata: dict[str, Any] | None = None
    permissions: list[Any] | None = None
    revert: dict[str, Any] | None = None
    location: dict[str, Any] | None = None


class PromptResponse(OpencodeBaseModel):
    """Session.Inbox.User — returned by POST /api/session/{id}/prompt"""

    id: str | None = None
    sessionID: str | None = None
    time: dict[str, Any] | None = None
    type: str | None = None
    payload: dict[str, Any] | None = None
    delivery: str | None = None


class AgentResponse(OpencodeBaseModel):
    """Agent.Info"""

    id: str | None = None
    name: str | None = None
    model: dict[str, Any] | None = None
    request: dict[str, Any] | None = None
    system: str | None = None
    description: str | None = None
    mode: str | None = None
    hidden: bool | None = None
    color: str | None = None
    steps: int | None = None
    permissions: list[Any] | None = None


class ModelV2Info(OpencodeBaseModel):
    """Model.Info"""

    id: str | None = None
    modelID: str | None = None
    providerID: str | None = None
    canonical: str | None = None
    type: str | None = None
    family: str | None = None
    name: str | None = None
    compatibility: dict[str, Any] | None = None
    package: str | None = None
    settings: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    capabilities: dict[str, Any] | None = None
    variants: list[Any] | None = None
    time: dict[str, Any] | None = None
    cost: list[Any] | None = None
    status: str | None = None
    enabled: bool | None = None
    limit: dict[str, Any] | None = None


class ProviderV2Info(OpencodeBaseModel):
    """Provider.Info"""

    id: str | None = None
    canonical: str | None = None
    integrationID: str | None = None
    name: str | None = None
    activation: str | None = None
    package: str | None = None
    compatibility: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    body: dict[str, Any] | None = None


class IntegrationResponse(OpencodeBaseModel):
    """Integration.Info"""

    id: str | None = None
    name: str | None = None
    metadata: dict[str, Any] | None = None
    methods: list[Any] | None = None
    connections: list[Any] | None = None


class MCPServerResponse(OpencodeBaseModel):
    """Mcp.Server"""

    name: str | None = None
    status: dict[str, Any] | None = None
    title: str | None = None
    integrationID: str | None = None


class CredentialResponse(OpencodeBaseModel):
    """Credential.Entry"""

    id: str | None = None
    integrationID: str | None = None
    label: str | None = None
    active: bool | None = None
    value: dict[str, Any] | None = None


class ProjectResponse(OpencodeBaseModel):
    """Project"""

    id: str | None = None
    canonical: str | None = None
    vcs: str | None = None
    name: str | None = None
    icon: dict[str, Any] | None = None
    commands: dict[str, Any] | None = None
    time: dict[str, Any] | None = None
    sandboxes: list[Any] | None = None


class PermissionRequestResponse(OpencodeBaseModel):
    """Permission.Request"""

    id: str | None = None
    sessionID: str | None = None
    action: str | None = None
    resources: list[Any] | None = None
    save: list[Any] | None = None
    metadata: dict[str, Any] | None = None
    source: dict[str, Any] | None = None
    message: str | None = None


class FormResponse(OpencodeBaseModel):
    """Form.Info"""

    id: str | None = None
    sessionID: str | None = None
    title: str | None = None
    metadata: dict[str, Any] | None = None
    fields: list[Any] | None = None


class FileSystemEntry(OpencodeBaseModel):
    """FileSystem.Entry"""

    path: str | None = None
    type: str | None = None


class CommandResponse(OpencodeBaseModel):
    """Command.Info"""

    name: str | None = None
    description: str | None = None


class SkillResponse(OpencodeBaseModel):
    """Skill.Info"""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    autoinvoke: bool | None = None
    path: str | None = None
    content: str | None = None


class PtyResponse(OpencodeBaseModel):
    """Pty"""

    id: str | None = None
    title: str | None = None
    command: str | None = None
    args: list[Any] | None = None
    cwd: str | None = None
    status: str | None = None
    pid: int | None = None
    exitCode: int | None = None


class ShellResponse(OpencodeBaseModel):
    """Shell.Info"""

    id: str | None = None
    status: str | None = None
    command: str | None = None
    cwd: str | None = None
    shell: str | None = None
    file: str | None = None
    pid: int | None = None
    exit: float | None = None
    signal: str | None = None
    metadata: dict[str, Any] | None = None
    time: dict[str, Any] | None = None


class VcsInfo(OpencodeBaseModel):
    """Vcs.Info"""

    provider: str | None = None
    branch: dict[str, Any] | None = None


class VcsFileStatus(OpencodeBaseModel):
    """Vcs.FileStatus"""

    file: str | None = None
    additions: int | None = None
    deletions: int | None = None
    status: str | None = None


class VcsBranchList(OpencodeBaseModel):
    """Vcs.BranchList"""

    pass


class FileDiffResponse(OpencodeBaseModel):
    """FileDiff.Info"""

    file: str | None = None
    patch: str | None = None
    additions: int | None = None
    deletions: int | None = None
    status: str | None = None
    more: bool | None = None


class WorktreeResponse(OpencodeBaseModel):
    """Worktree.Directory"""

    directory: str | None = None
    strategy: str | None = None


class ConfigEntry(OpencodeBaseModel):
    """Config.Entry"""

    type: str | None = None
    path: str | None = None
    info: dict[str, Any] | None = None


class ConfigShellOption(OpencodeBaseModel):
    """ConfigShell.Option"""

    path: str | None = None
    name: str | None = None
    acceptable: bool | None = None
