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

        stream = await ai.ask_stream("hello", collect=True)
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
# Global / Health
# ---------------------------------------------------------------------------


class HealthResponse(OpencodeBaseModel):
    ok: bool = True
    version: str | None = None
    healthy: bool | None = None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ConfigResponse(OpencodeBaseModel):
    """Response from GET /config and PATCH /config."""


class ConfigProviderResponse(OpencodeBaseModel):
    """Response from GET /config/providers."""


# ---------------------------------------------------------------------------
# Session (V1 + V2)
# ---------------------------------------------------------------------------


class SessionResponse(OpencodeBaseModel):
    id: str = ""
    agent: str | None = None
    model: str | None = None
    title: str | None = None
    created: float | None = None


class V2SessionsResponse(OpencodeBaseModel):
    """Response from GET /api/session."""

    cursor: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []


class V2SessionMessagesResponse(OpencodeBaseModel):
    """Response from GET /api/session/:id/message."""

    cursor: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []


class V1SessionResponse(OpencodeBaseModel):
    """Response from POST /session/:id/message (V1)."""

    parts: list[dict[str, Any]] = []
    info: dict[str, Any] = {}
    structured: Any = None


class MessageInfo(OpencodeBaseModel):
    id: str = ""
    model: dict[str, str] | None = None
    time: dict[str, float] | None = None
    structured: Any = None


class MessagePart(OpencodeBaseModel):
    type: str = ""
    text: str | None = None


# ---------------------------------------------------------------------------
# V2 Model / Provider
# ---------------------------------------------------------------------------


class ModelV2Info(OpencodeBaseModel):
    """Response from GET /api/model."""

    id: str = ""
    providerID: str | None = None
    name: str | None = None
    description: str | None = None


class ProviderV2Info(OpencodeBaseModel):
    """Response from GET /api/provider."""

    id: str = ""
    name: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------


class FileContentResponse(OpencodeBaseModel):
    content: str = ""
    uri: str | None = None
    type: str | None = None
    encoding: str | None = None
    mimeType: str | None = None


class FileNode(OpencodeBaseModel):
    """Response item from GET /file."""

    absolute: str = ""
    ignored: bool = False
    name: str = ""
    path: str = ""
    type: str = ""


class FileStatus(OpencodeBaseModel):
    """Response item from GET /file/status."""

    path: str = ""
    status: str = ""
    added: int = 0
    removed: int = 0


# ---------------------------------------------------------------------------
# Find
# ---------------------------------------------------------------------------


class FindMatch(OpencodeBaseModel):
    """Response item from GET /find."""

    path: dict[str, Any] | None = None
    lines: dict[str, Any] | None = None
    line_number: int = 0
    absolute_offset: int = 0
    submatches: list[dict[str, Any]] = []


class Symbol(OpencodeBaseModel):
    """Response item from GET /find/symbol."""

    kind: int = 0
    location: dict[str, Any] | None = None
    name: str = ""


# ---------------------------------------------------------------------------
# VCS
# ---------------------------------------------------------------------------


class VcsInfo(OpencodeBaseModel):
    """Response from GET /vcs."""

    branch: str | None = None
    default_branch: str | None = None


class VcsFileStatus(OpencodeBaseModel):
    """Response item from GET /vcs/status."""

    file: str = ""
    status: str = ""
    additions: int = 0
    deletions: int = 0


class VcsFileDiff(OpencodeBaseModel):
    """Response item from GET /vcs/diff."""

    file: str = ""
    status: str | None = None
    additions: int = 0
    deletions: int = 0
    patch: str | None = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class AuthResponse(OpencodeBaseModel):
    """Response from auth endpoints."""


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class ProviderResponse(OpencodeBaseModel):
    """Response from GET /provider."""

    all: list[dict[str, Any]] = []
    default: dict[str, Any] = {}
    connected: list[str] = []


class ProviderAuthListResponse(OpencodeBaseModel):
    """Response from GET /provider/auth."""


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------


class MCPStatusResponse(OpencodeBaseModel):
    """Response from GET /mcp and GET /mcp/status."""


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


class ToolList(OpencodeBaseModel):
    """Response from GET /experimental/tool."""


class ToolIDs(OpencodeBaseModel):
    """Response from GET /experimental/tool/ids."""


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------


class PermissionRequestResponse(OpencodeBaseModel):
    """Response item from GET /permission."""

    id: str = ""
    sessionID: str = ""
    permission: str = ""
    tool: dict[str, Any] | None = None
    patterns: list[str] = []
    always: list[str] = []
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------


class QuestionRequestResponse(OpencodeBaseModel):
    """Response item from GET /question."""

    id: str = ""
    sessionID: str = ""
    questions: list[dict[str, Any]] = []
    tool: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# PTY
# ---------------------------------------------------------------------------


class PtyResponse(OpencodeBaseModel):
    """Response from PTY endpoints."""

    id: str = ""
    command: str = ""
    args: list[str] = []
    cwd: str = ""
    pid: int = 0
    status: str = ""
    title: str = ""


class PtyShell(OpencodeBaseModel):
    """Response item from GET /pty/shells."""

    path: str = ""
    name: str = ""
    acceptable: bool = False


# ---------------------------------------------------------------------------
# Path
# ---------------------------------------------------------------------------


class PathResponse(OpencodeBaseModel):
    """Response from GET /path."""

    config: str = ""
    directory: str = ""
    home: str = ""
    state: str = ""
    worktree: str = ""


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class CommandResponse(OpencodeBaseModel):
    """Response item from GET /command."""

    name: str = ""
    description: str = ""
    template: str = ""
    hints: list[str] = []
    agent: str | None = None
    model: str | None = None
    source: str | None = None
    subtask: bool | None = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class AgentResponse(OpencodeBaseModel):
    """Response item from GET /agent."""

    name: str = ""
    mode: str = ""
    options: dict[str, Any] = {}
    permission: Any = []
    description: str | None = None
    color: str | None = None
    hidden: bool | None = None
    model: dict[str, Any] | None = None
    prompt: str | None = None
    steps: float | None = None
    temperature: float | None = None
    topP: float | None = None
    native: bool | None = None
    variant: str | None = None


# ---------------------------------------------------------------------------
# LSP / Formatter
# ---------------------------------------------------------------------------


class LSPStatusResponse(OpencodeBaseModel):
    """Response item from GET /lsp."""

    id: str = ""
    name: str = ""
    root: str = ""
    status: str = ""


class FormatterStatusResponse(OpencodeBaseModel):
    """Response item from GET /formatter."""

    name: str = ""
    enabled: bool = False
    extensions: list[str] = []


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectResponse(OpencodeBaseModel):
    """Response from project endpoints."""

    id: str = ""
    name: str | None = None
    directory: str | None = None
    worktree: str = ""
    sandboxes: list[str] = []
    vcs: str | None = None
    time: dict[str, Any] | None = None
    commands: dict[str, Any] | None = None
    icon: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Worktree
# ---------------------------------------------------------------------------


class WorktreeResponse(OpencodeBaseModel):
    """Response from worktree endpoints."""

    directory: str = ""
    name: str = ""
    branch: str | None = None


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


class WorkspaceResponse(OpencodeBaseModel):
    """Response from workspace endpoints."""

    id: str = ""
    name: str = ""
    projectID: str = ""
    type: str = ""
    branch: dict[str, Any] | None = None
    directory: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None
    timeUsed: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


class SyncStartResponse(OpencodeBaseModel):
    """Response from POST /sync/start."""


class SyncStealResponse(OpencodeBaseModel):
    """Response from POST /sync/steal."""

    sessionID: str | None = None


class SyncReplayResponse(OpencodeBaseModel):
    """Response from POST /sync/replay."""

    sessionID: str | None = None


# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------


class TUINextResponse(OpencodeBaseModel):
    """Response from GET /tui/control/next."""

    path: str = ""
    body: Any = None


# ---------------------------------------------------------------------------
# Todo
# ---------------------------------------------------------------------------


class TodoResponse(OpencodeBaseModel):
    """Response item from GET /session/:id/todo."""

    content: str = ""
    status: str = ""
    priority: str = ""


# ---------------------------------------------------------------------------
# Snapshot file diff
# ---------------------------------------------------------------------------


class SnapshotFileDiffResponse(OpencodeBaseModel):
    """Response item from GET /session/:id/diff."""

    file: str | None = None
    status: str | None = None
    additions: int = 0
    deletions: int = 0
    patch: str | None = None


# ---------------------------------------------------------------------------
# Generic message response
# ---------------------------------------------------------------------------


class MessageResponse(OpencodeBaseModel):
    """Response from session message endpoints."""

    info: dict[str, Any] = {}
    parts: list[dict[str, Any]] = []
