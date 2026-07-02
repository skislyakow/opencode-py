from __future__ import annotations

from typing import Any, Dict, List, Literal, NotRequired, TypedDict


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


AssistantContent = AssistantMessageText | AssistantMessageReasoning | AssistantMessageTool


class AssistantMessage(TypedDict):
    id: str
    type: Literal["assistant"]
    agent: NotRequired[str | None]
    model: NotRequired[Dict[str, str] | None]
    content: List[AssistantContent]
    finish: NotRequired[str | None]
    cost: NotRequired[float | None]
    tokens: NotRequired[Dict[str, int] | None]
    time: Dict[str, float]


class UserMessage(TypedDict):
    id: str
    type: Literal["user"]
    text: str
    files: NotRequired[List[Any] | None]
    agents: NotRequired[List[Any] | None]
    references: NotRequired[List[Any] | None]
    time: Dict[str, float]


SessionMessage = AssistantMessage | UserMessage


class PromptFileAttachment(TypedDict):
    uri: str
    mime: NotRequired[str | None]
    name: NotRequired[str | None]
    description: NotRequired[str | None]
    source: NotRequired[Dict[str, Any] | None]


class PromptAgentAttachment(TypedDict):
    name: str
    source: NotRequired[Dict[str, Any] | None]


class PromptReferenceAttachment(TypedDict):
    name: str
    kind: NotRequired[str | None]
    uri: NotRequired[str | None]
    repository: NotRequired[str | None]
    branch: NotRequired[str | None]
    target: NotRequired[str | None]
    targetUri: NotRequired[str | None]
    source: NotRequired[Dict[str, Any] | None]
