import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str = ""
    type: str
    properties: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def parse_stream_event(data: str) -> StreamEvent:
    raw = json.loads(data)
    return StreamEvent(
        id=raw.get("id", ""),
        type=raw.get("type", ""),
        properties=raw.get("properties", {}),
    )


# ---------------------------------------------------------------------------
# 1. Server lifecycle
# ---------------------------------------------------------------------------


class ServerConnectedProps(BaseModel):
    pass


class ServerHeartbeatProps(BaseModel):
    pass


class ServerInstanceDisposedProps(BaseModel):
    directory: str = ""


class GlobalDisposedProps(BaseModel):
    pass


# ---------------------------------------------------------------------------
# 2. Session lifecycle
# ---------------------------------------------------------------------------


class SessionCreatedProps(BaseModel):
    sessionID: str = ""
    info: dict[str, Any] = {}


class SessionUpdatedProps(BaseModel):
    sessionID: str = ""
    info: dict[str, Any] = {}


class SessionDeletedProps(BaseModel):
    sessionID: str = ""
    info: dict[str, Any] = {}


class SessionStatusProps(BaseModel):
    sessionID: str = ""
    status: dict[str, Any] = {}


class SessionIdleProps(BaseModel):
    sessionID: str = ""


class SessionDiffEntry(BaseModel):
    file: str = ""
    patch: str = ""
    additions: int = 0
    deletions: int = 0
    status: str | None = None


class SessionDiffProps(BaseModel):
    sessionID: str = ""
    diff: list[dict[str, Any]] = []


class SessionErrorProps(BaseModel):
    sessionID: str | None = None
    error: dict[str, Any] | None = None


class SessionCompactedProps(BaseModel):
    sessionID: str = ""


# ---------------------------------------------------------------------------
# 3. Message & Part events (used by ask_stream)
# ---------------------------------------------------------------------------


class MessageUpdatedProps(BaseModel):
    sessionID: str = ""
    info: dict[str, Any] = {}


class MessageRemovedProps(BaseModel):
    sessionID: str = ""
    messageID: str = ""


class MessagePartUpdatedProps(BaseModel):
    sessionID: str = ""
    part: dict[str, Any] = {}
    time: float = 0.0


class MessagePartRemovedProps(BaseModel):
    sessionID: str = ""
    messageID: str = ""
    partID: str = ""


class MessagePartDeltaProps(BaseModel):
    sessionID: str = ""
    messageID: str = ""
    partID: str = ""
    field: str = ""
    delta: str = ""


# ---------------------------------------------------------------------------
# 4. Session.Next (granular streaming, core EventV2 system)
# ---------------------------------------------------------------------------


class SessionNextAgentSwitchedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    agent: str = ""


class SessionNextModelSwitchedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    model: dict[str, Any] = {}


class SessionNextPromptedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    prompt: dict[str, Any] = {}


class SessionNextSyntheticProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    text: str = ""


class SessionNextShellStartedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    command: str = ""


class SessionNextShellEndedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    output: str = ""


class SessionNextStepStartedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    agent: str = ""
    model: dict[str, Any] = {}
    snapshot: str | None = None


class SessionNextStepEndedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    finish: str = ""
    cost: float = 0.0
    tokens: dict[str, Any] = {}
    snapshot: str | None = None


class SessionNextStepFailedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    error: dict[str, Any] = {}


class SessionNextTextStartedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""


class SessionNextTextDeltaProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    delta: str = ""


class SessionNextTextEndedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    text: str = ""


class SessionNextReasoningStartedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    reasoningID: str = ""


class SessionNextReasoningDeltaProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    reasoningID: str = ""
    delta: str = ""


class SessionNextReasoningEndedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    reasoningID: str = ""
    text: str = ""


class SessionNextToolInputStartedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    name: str = ""


class SessionNextToolInputDeltaProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    delta: str = ""


class SessionNextToolInputEndedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    text: str = ""


class SessionNextToolCalledProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    tool: str = ""
    input: dict[str, Any] = {}
    provider: dict[str, Any] = {}


class SessionNextToolProgressProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    structured: Any = None
    content: list[dict[str, Any]] = []


class SessionNextToolSuccessProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    structured: Any = None
    content: list[dict[str, Any]] = []
    provider: dict[str, Any] = {}


class SessionNextToolFailedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    callID: str = ""
    error: dict[str, Any] = {}
    provider: dict[str, Any] = {}


class SessionNextRetriedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    attempt: int = 0
    error: dict[str, Any] = {}


class SessionNextCompactionStartedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    reason: str = ""


class SessionNextCompactionDeltaProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    text: str = ""


class SessionNextCompactionEndedProps(BaseModel):
    timestamp: float = 0.0
    sessionID: str = ""
    text: str = ""
    include: str | None = None


# ---------------------------------------------------------------------------
# 5. Account events
# ---------------------------------------------------------------------------


class AccountAddedProps(BaseModel):
    account: dict[str, Any] = {}


class AccountRemovedProps(BaseModel):
    account: dict[str, Any] = {}


class AccountSwitchedProps(BaseModel):
    serviceID: str = ""
    from_: str | None = None
    to: str | None = None


# ---------------------------------------------------------------------------
# 6. Catalog / Model events
# ---------------------------------------------------------------------------


class CatalogModelUpdatedProps(BaseModel):
    model: dict[str, Any] = {}


class ModelsDevRefreshedProps(BaseModel):
    pass


# ---------------------------------------------------------------------------
# 7. Permission events
# ---------------------------------------------------------------------------


class PermissionAskedProps(BaseModel):
    id: str = ""
    sessionID: str = ""
    permission: str = ""
    patterns: list[str] = []
    metadata: dict[str, Any] = {}
    always: bool = False
    tool: dict[str, Any] | None = None


class PermissionRepliedProps(BaseModel):
    sessionID: str = ""
    requestID: str = ""
    reply: str = ""


# ---------------------------------------------------------------------------
# 8. Question events
# ---------------------------------------------------------------------------


class QuestionAskedProps(BaseModel):
    id: str = ""
    sessionID: str = ""
    questions: list[dict[str, Any]] = []
    tool: dict[str, Any] | None = None


class QuestionRepliedProps(BaseModel):
    sessionID: str = ""
    requestID: str = ""
    answers: list[dict[str, Any]] = []


class QuestionRejectedProps(BaseModel):
    sessionID: str = ""
    requestID: str = ""


# ---------------------------------------------------------------------------
# 9. PTY events
# ---------------------------------------------------------------------------


class PtyCreatedProps(BaseModel):
    info: dict[str, Any] = {}


class PtyUpdatedProps(BaseModel):
    info: dict[str, Any] = {}


class PtyExitedProps(BaseModel):
    id: str = ""
    exitCode: int = 0


class PtyDeletedProps(BaseModel):
    id: str = ""


# ---------------------------------------------------------------------------
# 10. File events
# ---------------------------------------------------------------------------


class FileEditedProps(BaseModel):
    file: str = ""


class FileWatcherUpdatedProps(BaseModel):
    file: str = ""
    event: str = ""


# ---------------------------------------------------------------------------
# 11. VCS events
# ---------------------------------------------------------------------------


class VcsBranchUpdatedProps(BaseModel):
    branch: str | None = None


# ---------------------------------------------------------------------------
# 12. LSP events
# ---------------------------------------------------------------------------


class LspUpdatedProps(BaseModel):
    pass


class LspClientDiagnosticsProps(BaseModel):
    serverID: str = ""
    path: str = ""


# ---------------------------------------------------------------------------
# 13. MCP events
# ---------------------------------------------------------------------------


class McpToolsChangedProps(BaseModel):
    server: str = ""


class McpBrowserOpenFailedProps(BaseModel):
    mcpName: str = ""
    url: str = ""


# ---------------------------------------------------------------------------
# 14. Installation events
# ---------------------------------------------------------------------------


class InstallationUpdatedProps(BaseModel):
    version: str = ""


class InstallationUpdateAvailableProps(BaseModel):
    version: str = ""


# ---------------------------------------------------------------------------
# 15. Project / Command / Todo / Workspace / Worktree / IDE
# ---------------------------------------------------------------------------


class ProjectUpdatedProps(BaseModel):
    pass


class CommandExecutedProps(BaseModel):
    name: str = ""
    sessionID: str = ""
    arguments: str = ""
    messageID: str = ""


class TodoUpdatedProps(BaseModel):
    sessionID: str = ""
    todos: list[dict[str, Any]] = []


class WorkspaceReadyProps(BaseModel):
    name: str = ""


class WorkspaceFailedProps(BaseModel):
    message: str = ""


class WorkspaceStatusProps(BaseModel):
    workspaceID: str = ""
    status: str = ""


class WorktreeReadyProps(BaseModel):
    name: str = ""
    branch: str | None = None


class WorktreeFailedProps(BaseModel):
    message: str = ""


class IdeInstalledProps(BaseModel):
    ide: str = ""


# ---------------------------------------------------------------------------
# Union of all property models — for discriminated parsing
# ---------------------------------------------------------------------------

# Mapping from event type string to property model class
EVENT_PROPS_REGISTRY: dict[str, type[BaseModel]] = {
    # Server lifecycle
    "server.connected": ServerConnectedProps,
    "server.heartbeat": ServerHeartbeatProps,
    "server.instance.disposed": ServerInstanceDisposedProps,
    "global.disposed": GlobalDisposedProps,
    # Session lifecycle
    "session.created": SessionCreatedProps,
    "session.updated": SessionUpdatedProps,
    "session.deleted": SessionDeletedProps,
    "session.status": SessionStatusProps,
    "session.idle": SessionIdleProps,
    "session.diff": SessionDiffProps,
    "session.error": SessionErrorProps,
    "session.compacted": SessionCompactedProps,
    # Message & Part
    "message.updated": MessageUpdatedProps,
    "message.removed": MessageRemovedProps,
    "message.part.updated": MessagePartUpdatedProps,
    "message.part.removed": MessagePartRemovedProps,
    "message.part.delta": MessagePartDeltaProps,
    # Session.Next
    "session.next.agent.switched": SessionNextAgentSwitchedProps,
    "session.next.model.switched": SessionNextModelSwitchedProps,
    "session.next.prompted": SessionNextPromptedProps,
    "session.next.synthetic": SessionNextSyntheticProps,
    "session.next.shell.started": SessionNextShellStartedProps,
    "session.next.shell.ended": SessionNextShellEndedProps,
    "session.next.step.started": SessionNextStepStartedProps,
    "session.next.step.ended": SessionNextStepEndedProps,
    "session.next.step.failed": SessionNextStepFailedProps,
    "session.next.text.started": SessionNextTextStartedProps,
    "session.next.text.delta": SessionNextTextDeltaProps,
    "session.next.text.ended": SessionNextTextEndedProps,
    "session.next.reasoning.started": SessionNextReasoningStartedProps,
    "session.next.reasoning.delta": SessionNextReasoningDeltaProps,
    "session.next.reasoning.ended": SessionNextReasoningEndedProps,
    "session.next.tool.input.started": SessionNextToolInputStartedProps,
    "session.next.tool.input.delta": SessionNextToolInputDeltaProps,
    "session.next.tool.input.ended": SessionNextToolInputEndedProps,
    "session.next.tool.called": SessionNextToolCalledProps,
    "session.next.tool.progress": SessionNextToolProgressProps,
    "session.next.tool.success": SessionNextToolSuccessProps,
    "session.next.tool.failed": SessionNextToolFailedProps,
    "session.next.retried": SessionNextRetriedProps,
    "session.next.compaction.started": SessionNextCompactionStartedProps,
    "session.next.compaction.delta": SessionNextCompactionDeltaProps,
    "session.next.compaction.ended": SessionNextCompactionEndedProps,
    # Account
    "account.added": AccountAddedProps,
    "account.removed": AccountRemovedProps,
    "account.switched": AccountSwitchedProps,
    # Catalog
    "catalog.model.updated": CatalogModelUpdatedProps,
    "models-dev.refreshed": ModelsDevRefreshedProps,
    # Permission
    "permission.asked": PermissionAskedProps,
    "permission.replied": PermissionRepliedProps,
    # Question
    "question.asked": QuestionAskedProps,
    "question.replied": QuestionRepliedProps,
    "question.rejected": QuestionRejectedProps,
    # PTY
    "pty.created": PtyCreatedProps,
    "pty.updated": PtyUpdatedProps,
    "pty.exited": PtyExitedProps,
    "pty.deleted": PtyDeletedProps,
    # File
    "file.edited": FileEditedProps,
    "file.watcher.updated": FileWatcherUpdatedProps,
    # VCS
    "vcs.branch.updated": VcsBranchUpdatedProps,
    # LSP
    "lsp.updated": LspUpdatedProps,
    "lsp.client.diagnostics": LspClientDiagnosticsProps,
    # MCP
    "mcp.tools.changed": McpToolsChangedProps,
    "mcp.browser.open.failed": McpBrowserOpenFailedProps,
    # Installation
    "installation.updated": InstallationUpdatedProps,
    "installation.update-available": InstallationUpdateAvailableProps,
    # Project
    "project.updated": ProjectUpdatedProps,
    # Command
    "command.executed": CommandExecutedProps,
    # Todo
    "todo.updated": TodoUpdatedProps,
    # Workspace
    "workspace.ready": WorkspaceReadyProps,
    "workspace.failed": WorkspaceFailedProps,
    "workspace.status": WorkspaceStatusProps,
    # Worktree
    "worktree.ready": WorktreeReadyProps,
    "worktree.failed": WorktreeFailedProps,
    # IDE
    "ide.installed": IdeInstalledProps,
}


def parse_typed_event(data: str) -> StreamEvent:
    """Parse an SSE event line into a typed ``StreamEvent``.

    If the event type is known, the ``properties`` dict is validated
    against the corresponding ``*Props`` model and stored as a dict.
    Unknown event types are returned as-is.
    """
    raw = json.loads(data)
    event_type = raw.get("type", "")
    props_raw = raw.get("properties", {})

    props_cls = EVENT_PROPS_REGISTRY.get(event_type)
    if props_cls is not None:
        props = props_cls.model_construct(**props_raw)
        props_dict: dict[str, Any] = props.model_dump()
    else:
        props_dict = dict(props_raw) if isinstance(props_raw, dict) else {}

    return StreamEvent(
        id=raw.get("id", ""),
        type=event_type,
        properties=props_dict,
    )
