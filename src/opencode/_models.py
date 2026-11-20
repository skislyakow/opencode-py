from __future__ import annotations

from typing import Any, Literal, TypedDict

from typing_extensions import NotRequired


class SessionInfo(TypedDict):
    id: str
    agent: NotRequired[str | None]
    model: NotRequired[dict[str, str] | None]
    title: NotRequired[str | None]
    time: NotRequired[dict[str, float]]


class AssistantMessageText(TypedDict):
    type: Literal["text"]
    text: str


class AssistantMessageReasoning(TypedDict):
    type: Literal["reasoning"]
    text: str


class AssistantMessageTool(TypedDict):
    """Tool call executed by the server; ``state`` holds input, status and output."""

    type: Literal["tool"]
    id: str
    name: str
    executed: NotRequired[bool]
    state: NotRequired[dict[str, Any]]
    time: NotRequired[dict[str, float]]


AssistantContent = AssistantMessageText | AssistantMessageReasoning | AssistantMessageTool


class AssistantMessage(TypedDict):
    id: str
    type: Literal["assistant"]
    agent: NotRequired[str | None]
    model: NotRequired[dict[str, str] | None]
    content: list[AssistantContent]
    finish: NotRequired[str | None]
    cost: NotRequired[float | None]
    tokens: NotRequired[dict[str, Any] | None]
    time: dict[str, float]


class UserMessage(TypedDict):
    id: str
    type: Literal["user"]
    text: str
    files: NotRequired[list[Any] | None]
    agents: NotRequired[list[Any] | None]
    skills: NotRequired[list[Any] | None]
    time: dict[str, float]


SessionMessage = AssistantMessage | UserMessage


class PromptFileAttachment(TypedDict):
    """File attachment for ``Session.prompt(files=[...])``."""

    uri: str
    name: NotRequired[str]
    description: NotRequired[str]
    source: NotRequired[dict[str, Any]]


class PromptAgentAttachment(TypedDict):
    name: str
