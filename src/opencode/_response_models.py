from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class OpencodeBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(OpencodeBaseModel):
    ok: bool = True
    version: str | None = None
    healthy: bool | None = None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class SessionResponse(OpencodeBaseModel):
    id: str
    agent: str | None = None
    model: str | None = None
    title: str | None = None
    created: float | None = None


class SessionListResponse(OpencodeBaseModel):
    """Wrapper for session list endpoint."""


# ---------------------------------------------------------------------------
# V2 Session / Message parts
# ---------------------------------------------------------------------------


class MessageInfo(OpencodeBaseModel):
    id: str = ""
    model: dict[str, str] | None = None
    time: dict[str, float] | None = None
    structured: Any = None


class MessagePart(OpencodeBaseModel):
    type: str
    text: str | None = None


class V1SessionResponse(OpencodeBaseModel):
    """Response from POST /session/:id/message (V1)."""
    parts: list[dict[str, Any]] = []
    info: dict[str, Any] = {}
    structured: Any = None


# ---------------------------------------------------------------------------
# V2 Model / Provider
# ---------------------------------------------------------------------------


class ModelResponse(OpencodeBaseModel):
    id: str
    provider: str | None = None
    name: str | None = None
    description: str | None = None


class ProviderResponse(OpencodeBaseModel):
    id: str
    name: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------


class FileContentResponse(OpencodeBaseModel):
    content: str = ""
    uri: str | None = None


# ---------------------------------------------------------------------------
# VCS
# ---------------------------------------------------------------------------


class VCSGetResponse(OpencodeBaseModel):
    """Response from GET /vcs."""


class VCSStatusResponse(OpencodeBaseModel):
    """Response from GET /vcs/status."""


class VCSDiffResponse(OpencodeBaseModel):
    """Response from GET /vcs/diff."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ConfigResponse(OpencodeBaseModel):
    """Response from GET /config."""


class ConfigProviderResponse(OpencodeBaseModel):
    """Response from GET /config/providers."""


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


class WorkspaceResponse(OpencodeBaseModel):
    id: str | None = None
    name: str | None = None


# ---------------------------------------------------------------------------
# PTY
# ---------------------------------------------------------------------------


class PTYResponse(OpencodeBaseModel):
    id: str | None = None
    program: str | None = None


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------


class PermissionResponse(OpencodeBaseModel):
    id: str | None = None
    tool: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------


class QuestionResponse(OpencodeBaseModel):
    id: str | None = None
    question: str | None = None


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------


class MCPStatusResponse(OpencodeBaseModel):
    """Response from GET /mcp/status."""


# ---------------------------------------------------------------------------
# LSP / Formatter
# ---------------------------------------------------------------------------


class LSPStatusResponse(OpencodeBaseModel):
    """Response from GET /lsp."""


class FormatterStatusResponse(OpencodeBaseModel):
    """Response from GET /formatter."""


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectResponse(OpencodeBaseModel):
    id: str | None = None
    name: str | None = None
    directory: str | None = None


# ---------------------------------------------------------------------------
# Worktree
# ---------------------------------------------------------------------------


class WorktreeResponse(OpencodeBaseModel):
    id: str | None = None
    path: str | None = None


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


class ToolResponse(OpencodeBaseModel):
    id: str | None = None
    name: str | None = None


# ---------------------------------------------------------------------------
# App / Agent
# ---------------------------------------------------------------------------


class AgentResponse(OpencodeBaseModel):
    id: str | None = None
    name: str | None = None


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


class SyncHistoryResponse(OpencodeBaseModel):
    """Response from GET /experimental/sync/history/:id."""


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class CommandResponse(OpencodeBaseModel):
    id: str | None = None
    command: str | None = None
