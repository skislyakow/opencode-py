from __future__ import annotations

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired  # Python <3.11

from typing import Any, Literal, TypedDict


class SessionInfo(TypedDict):
    id: str
    agent: NotRequired[str | None]
    model: NotRequired[str | None]
    title: NotRequired[str | None]
    created: NotRequired[float]


class AssistantMessageText(TypedDict):
    type: Literal["text"]
    text: str


class AssistantMessageReasoning(TypedDict):
    type: Literal["reasoning"]
    text: str


class AssistantMessageTool(TypedDict):
    type: Literal["tool"]
    tool: str
    input: Any
    output: NotRequired[str | None]


class ToolCall(TypedDict):
    name: str
    input: dict[str, Any]


class ToolUse(TypedDict):
    type: Literal["tool-use"]
    toolUseID: str
    tool: ToolCall


class ToolResult(TypedDict):
    type: Literal["tool-result"]
    toolUseID: str
    tool: ToolCall
    output: dict[str, Any]


AssistantContent = AssistantMessageText | AssistantMessageReasoning | AssistantMessageTool | ToolUse


class AssistantMessage(TypedDict):
    id: str
    type: Literal["assistant"]
    agent: NotRequired[str | None]
    model: NotRequired[dict[str, str] | None]
    content: list[AssistantContent]
    structured: NotRequired[Any]
    finish: NotRequired[str | None]
    cost: NotRequired[float | None]
    tokens: NotRequired[dict[str, int] | None]
    time: dict[str, float]


class UserMessage(TypedDict):
    id: str
    type: Literal["user"]
    text: str
    files: NotRequired[list[Any] | None]
    agents: NotRequired[list[Any] | None]
    references: NotRequired[list[Any] | None]
    time: dict[str, float]


SessionMessage = AssistantMessage | UserMessage


class PromptFileAttachment(TypedDict):
    uri: str
    mime: NotRequired[str | None]
    name: NotRequired[str | None]
    description: NotRequired[str | None]
    source: NotRequired[dict[str, Any] | None]


class PromptAgentAttachment(TypedDict):
    name: str
    source: NotRequired[dict[str, Any] | None]


class PromptReferenceAttachment(TypedDict):
    name: str
    kind: NotRequired[str | None]
    uri: NotRequired[str | None]
    repository: NotRequired[str | None]
    branch: NotRequired[str | None]
    target: NotRequired[str | None]
    targetUri: NotRequired[str | None]
    source: NotRequired[dict[str, Any] | None]


class OutputFormatJsonSchema(TypedDict):
    type: Literal["json_schema"]
    schema: dict[str, Any]
    retryCount: NotRequired[int | None]
