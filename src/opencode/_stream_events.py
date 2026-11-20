"""Typed models for opencode v2 SSE events (``GET /api/event``).

Generated from the server's ``/openapi.json`` (``V2Event`` union). Each SSE
``data:`` payload is ``{"id", "type", "created", "location", "data": {...}}``;
the ``data`` object is exposed as :attr:`StreamEvent.properties`.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str = ""
    type: str
    properties: dict[str, Any] = {}
    location: dict[str, Any] | None = None
    created: float | None = None

    @property
    def session_id(self) -> str | None:
        sid = self.properties.get("sessionID")
        return sid if isinstance(sid, str) else None


def parse_stream_event(data: str) -> StreamEvent:
    """Parse the JSON payload of an SSE ``data:`` line into a :class:`StreamEvent`."""
    raw = json.loads(data)
    if not isinstance(raw, dict):
        raw = {}
    props = raw.get("data", raw.get("properties", {}))
    return StreamEvent(
        id=raw.get("id") or "",
        type=raw.get("type", ""),
        properties=props if isinstance(props, dict) else {},
        location=raw.get("location"),
        created=raw.get("created"),
    )


class _EventProps(BaseModel):
    model_config = ConfigDict(extra="allow")


class LocationShutdownProps(_EventProps):
    """``location.shutdown``"""


class ModelsDevRefreshedProps(_EventProps):
    """``models-dev.refreshed``"""


class CredentialUpdatedProps(_EventProps):
    """``credential.updated``"""

    integrationID: str = ""
    credentialID: str = ""


class CredentialSwitchedProps(_EventProps):
    """``credential.switched``"""

    integrationID: str = ""
    credentialID: str = ""


class IntegrationUpdatedProps(_EventProps):
    """``integration.updated``"""


class ProviderUpdatedProps(_EventProps):
    """``provider.updated``"""


class ModelUpdatedProps(_EventProps):
    """``model.updated``"""


class AgentUpdatedProps(_EventProps):
    """``agent.updated``"""


class SessionCreatedProps(_EventProps):
    """``session.created``"""

    sessionID: str = ""
    projectID: str = ""
    location: dict[str, Any] = {}
    subpath: str | None = None
    parentID: str | None = None
    slug: str = ""
    title: str | None = None
    agent: str | None = None
    model: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    permissions: list[Any] | None = None
    version: str = ""


class SessionAgentSelectedProps(_EventProps):
    """``session.agent.selected``"""

    sessionID: str = ""
    agent: str = ""
    previous: str | None = None


class SessionModelSelectedProps(_EventProps):
    """``session.model.selected``"""

    sessionID: str = ""
    model: dict[str, Any] = {}
    previous: dict[str, Any] | None = None


class SessionMovedProps(_EventProps):
    """``session.moved``"""

    sessionID: str = ""
    location: dict[str, Any] = {}
    projectID: str = ""
    subpath: str | None = None


class SessionRenamedProps(_EventProps):
    """``session.renamed``"""

    sessionID: str = ""
    title: str = ""


class SessionMetadataUpdatedProps(_EventProps):
    """``session.metadata.updated``"""

    sessionID: str = ""
    metadata: dict[str, Any] = {}


class SessionPermissionsProps(_EventProps):
    """``session.permissions``"""

    sessionID: str = ""
    permissions: list[Any] = []


class SessionViewedProps(_EventProps):
    """``session.viewed``"""

    sessionID: str = ""
    idle: float = 0.0


class SessionArchivedProps(_EventProps):
    """``session.archived``"""

    sessionID: str = ""


class SessionUnarchivedProps(_EventProps):
    """``session.unarchived``"""

    sessionID: str = ""


class SessionUsageUpdatedProps(_EventProps):
    """``session.usage.updated``"""

    sessionID: str = ""
    cost: float = 0.0
    tokens: dict[str, Any] = {}


class SessionDeletedProps(_EventProps):
    """``session.deleted``"""

    sessionID: str = ""


class SessionForkedProps(_EventProps):
    """``session.forked``"""

    sessionID: str = ""
    parentID: str = ""
    boundary: dict[str, Any] = {}
    instructions: dict[str, Any] | None = None
    instructionEntries: list[Any] | None = None


class SessionInboxDeliveredProps(_EventProps):
    """``session.inbox.delivered``"""

    sessionID: str = ""
    inboxID: str = ""


class SessionInboxEnqueuedProps(_EventProps):
    """``session.inbox.enqueued``"""

    sessionID: str = ""
    inboxID: str = ""
    item: dict[str, Any] = {}


class SessionInboxCancelledProps(_EventProps):
    """``session.inbox.cancelled``"""

    sessionID: str = ""
    inboxID: str = ""


class SessionInboxDeliveryChangedProps(_EventProps):
    """``session.inbox.delivery.changed``"""

    sessionID: str = ""
    inboxID: str = ""
    delivery: str = ""


class SessionExecutionStartedProps(_EventProps):
    """``session.execution.started``"""

    sessionID: str = ""


class SessionExecutionSucceededProps(_EventProps):
    """``session.execution.succeeded``"""

    sessionID: str = ""


class SessionExecutionFailedProps(_EventProps):
    """``session.execution.failed``"""

    sessionID: str = ""
    error: dict[str, Any] = {}


class SessionExecutionInterruptedProps(_EventProps):
    """``session.execution.interrupted``"""

    sessionID: str = ""
    reason: str = ""


class SessionInstructionsUpdatedProps(_EventProps):
    """``session.instructions.updated``"""

    sessionID: str = ""
    delta: dict[str, Any] = {}
    text: str | None = None


class SessionSyntheticProps(_EventProps):
    """``session.synthetic``"""

    sessionID: str = ""
    text: str = ""
    description: str | None = None
    metadata: dict[str, Any] | None = None


class SessionSkillActivatedProps(_EventProps):
    """``session.skill.activated``"""

    sessionID: str = ""
    id: str = ""
    name: str = ""
    text: str = ""


class SessionShellStartedProps(_EventProps):
    """``session.shell.started``"""

    sessionID: str = ""
    shell: dict[str, Any] = {}


class SessionShellEndedProps(_EventProps):
    """``session.shell.ended``"""

    sessionID: str = ""
    shell: dict[str, Any] = {}
    output: dict[str, Any] = {}


class SessionStepStartedProps(_EventProps):
    """``session.step.started``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    agent: str = ""
    model: dict[str, Any] = {}
    snapshot: str | None = None
    started: int = 0


class SessionStepFirstTokenProps(_EventProps):
    """``session.step.first-token``"""

    sessionID: str = ""
    assistantMessageID: str = ""


class SessionStepStreamedProps(_EventProps):
    """``session.step.streamed``"""

    sessionID: str = ""
    assistantMessageID: str = ""


class SessionStepEndedProps(_EventProps):
    """``session.step.ended``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    finish: str = ""
    rawFinish: str | None = None
    native: dict[str, Any] | None = None
    cost: float = 0.0
    tokens: dict[str, Any] = {}
    snapshot: str | None = None
    files: list[Any] | None = None


class SessionStepFailedProps(_EventProps):
    """``session.step.failed``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    error: dict[str, Any] = {}
    finish: str | None = None
    rawFinish: str | None = None
    native: dict[str, Any] | None = None
    cost: float | None = None
    tokens: dict[str, Any] | None = None
    snapshot: str | None = None
    files: list[Any] | None = None


class SessionTextStartedProps(_EventProps):
    """``session.text.started``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    ordinal: int = 0


class SessionTextDeltaProps(_EventProps):
    """``session.text.delta``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    ordinal: int = 0
    delta: str = ""


class SessionTextEndedProps(_EventProps):
    """``session.text.ended``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    ordinal: int = 0
    text: str = ""
    native: dict[str, Any] | None = None


class SessionReasoningStartedProps(_EventProps):
    """``session.reasoning.started``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    ordinal: int = 0
    native: dict[str, Any] | None = None


class SessionReasoningDeltaProps(_EventProps):
    """``session.reasoning.delta``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    ordinal: int = 0
    delta: str = ""


class SessionReasoningEndedProps(_EventProps):
    """``session.reasoning.ended``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    ordinal: int = 0
    text: str = ""
    native: dict[str, Any] | None = None


class SessionToolInputStartedProps(_EventProps):
    """``session.tool.input.started``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    name: str = ""


class SessionToolInputDeltaProps(_EventProps):
    """``session.tool.input.delta``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    delta: str = ""


class SessionToolInputEndedProps(_EventProps):
    """``session.tool.input.ended``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    text: str = ""


class SessionToolCalledProps(_EventProps):
    """``session.tool.called``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    input: dict[str, Any] = {}
    executed: bool = False
    native: dict[str, Any] | None = None


class SessionToolProgressProps(_EventProps):
    """``session.tool.progress``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    metadata: dict[str, Any] = {}


class SessionToolSuccessProps(_EventProps):
    """``session.tool.success``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    content: list[Any] = []
    metadata: dict[str, Any] | None = None
    executed: bool = False
    native: dict[str, Any] | None = None


class SessionToolFailedProps(_EventProps):
    """``session.tool.failed``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    id: str = ""
    error: dict[str, Any] = {}
    content: list[Any] | None = None
    metadata: dict[str, Any] | None = None
    executed: bool = False
    native: dict[str, Any] | None = None


class SessionRetryScheduledProps(_EventProps):
    """``session.retry.scheduled``"""

    sessionID: str = ""
    assistantMessageID: str = ""
    attempt: int = 0
    at: int = 0
    error: dict[str, Any] = {}


class SessionCompactionStartedProps(_EventProps):
    """``session.compaction.started``"""

    sessionID: str = ""
    reason: str = ""
    inputID: str | None = None


class SessionCompactionDeltaProps(_EventProps):
    """``session.compaction.delta``"""

    sessionID: str = ""
    text: str = ""


class SessionCompactionEndedProps(_EventProps):
    """``session.compaction.ended``"""

    sessionID: str = ""
    reason: str = ""
    model: dict[str, Any] | None = None
    native: dict[str, Any] | None = None
    text: str = ""
    cost: float | None = None
    tokens: dict[str, Any] | None = None


class SessionCompactionFailedProps(_EventProps):
    """``session.compaction.failed``"""

    sessionID: str = ""
    reason: str = ""
    error: dict[str, Any] = {}
    inputID: str | None = None
    cost: float | None = None
    tokens: dict[str, Any] | None = None


class SessionRevertStagedProps(_EventProps):
    """``session.revert.staged``"""

    sessionID: str = ""
    revert: dict[str, Any] = {}


class SessionRevertClearedProps(_EventProps):
    """``session.revert.cleared``"""

    sessionID: str = ""


class SessionRevertCommittedProps(_EventProps):
    """``session.revert.committed``"""

    sessionID: str = ""
    to: str = ""


class FilesystemChangedProps(_EventProps):
    """``filesystem.changed``"""

    file: str = ""
    event: str = ""


class ReferenceUpdatedProps(_EventProps):
    """``reference.updated``"""


class PermissionAskedProps(_EventProps):
    """``permission.asked``"""

    id: str = ""
    sessionID: str = ""
    action: str = ""
    resources: list[Any] = []
    save: list[Any] | None = None
    metadata: dict[str, Any] | None = None
    source: dict[str, Any] | None = None
    message: str | None = None


class PermissionRepliedProps(_EventProps):
    """``permission.replied``"""

    sessionID: str = ""
    requestID: str = ""
    reply: str = ""


class PluginUpdatedProps(_EventProps):
    """``plugin.updated``"""


class ProjectUpdatedProps(_EventProps):
    """``project.updated``"""

    id: str = ""
    canonical: str = ""
    vcs: str | None = None
    name: str | None = None
    icon: dict[str, Any] | None = None
    commands: dict[str, Any] | None = None
    time: dict[str, Any] = {}
    sandboxes: list[Any] = []


class WorktreeUpdatedProps(_EventProps):
    """``worktree.updated``"""

    projectID: str = ""


class WorktreeResolvedProps(_EventProps):
    """``worktree.resolved``"""

    projectID: str = ""
    directory: str = ""
    previous: str = ""
    adopted: list[Any] | None = None


class CommandUpdatedProps(_EventProps):
    """``command.updated``"""


class ConfigUpdatedProps(_EventProps):
    """``config.updated``"""


class SkillUpdatedProps(_EventProps):
    """``skill.updated``"""


class PtyCreatedProps(_EventProps):
    """``pty.created``"""

    info: dict[str, Any] = {}


class PtyUpdatedProps(_EventProps):
    """``pty.updated``"""

    info: dict[str, Any] = {}


class PtyExitedProps(_EventProps):
    """``pty.exited``"""

    id: str = ""
    exitCode: int = 0


class PtyDeletedProps(_EventProps):
    """``pty.deleted``"""

    id: str = ""


class PersistentPtyAddedProps(_EventProps):
    """``persistent-pty.added``"""

    sessionID: str = ""
    terminal: dict[str, Any] = {}


class PersistentPtyRemovedProps(_EventProps):
    """``persistent-pty.removed``"""

    sessionID: str = ""
    ptyID: str = ""


class PersistentPtyUpdatedProps(_EventProps):
    """``persistent-pty.updated``"""

    sessionID: str = ""
    terminal: dict[str, Any] = {}


class ShellCreatedProps(_EventProps):
    """``shell.created``"""

    info: dict[str, Any] = {}


class ShellExitedProps(_EventProps):
    """``shell.exited``"""

    id: str = ""
    exit: float | None = None
    status: str = ""


class ShellDeletedProps(_EventProps):
    """``shell.deleted``"""

    id: str = ""


class FormCreatedProps(_EventProps):
    """``form.created``"""

    form: dict[str, Any] = {}


class FormRepliedProps(_EventProps):
    """``form.replied``"""

    id: str = ""
    sessionID: str = ""
    answer: dict[str, Any] = {}


class FormCancelledProps(_EventProps):
    """``form.cancelled``"""

    id: str = ""
    sessionID: str = ""


class WebsearchUpdatedProps(_EventProps):
    """``websearch.updated``"""


class ArtifactUpdatedProps(_EventProps):
    """``artifact.updated``"""


class SessionStatusProps(_EventProps):
    """``session.status``"""

    sessionID: str = ""
    status: dict[str, Any] = {}


class SessionIdleProps(_EventProps):
    """``session.idle``"""

    sessionID: str = ""


class TuiPromptAppendProps(_EventProps):
    """``tui.prompt.append``"""

    text: str = ""


class TuiCommandExecuteProps(_EventProps):
    """``tui.command.execute``"""

    command: str = ""


class TuiToastShowProps(_EventProps):
    """``tui.toast.show``"""

    title: str | None = None
    message: str = ""
    variant: str = ""
    duration: int | None = None


class TuiSessionSelectProps(_EventProps):
    """``tui.session.select``"""

    sessionID: Any = None


class InstallationUpdatedProps(_EventProps):
    """``installation.updated``"""

    version: str = ""


class InstallationUpdateAvailableProps(_EventProps):
    """``installation.update-available``"""

    version: str = ""


class VcsBranchUpdatedProps(_EventProps):
    """``vcs.branch.updated``"""

    branch: str | None = None


class McpStatusChangedProps(_EventProps):
    """``mcp.status.changed``"""

    server: str = ""


class McpResourcesChangedProps(_EventProps):
    """``mcp.resources.changed``"""

    server: str = ""


class ExperimentalMcpEventProps(_EventProps):
    """``experimental.mcp.event``"""

    id: str = ""
    server: str = ""
    name: str = ""
    eventId: str = ""
    timestamp: str = ""
    data: Any = None
    cursor: str = ""
    truncated: bool | None = None


class ServerConnectedProps(_EventProps):
    """``server.connected``"""


# Mapping from event type string to its ``data`` model
EVENT_PROPS_REGISTRY: dict[str, type[BaseModel]] = {
    "location.shutdown": LocationShutdownProps,
    "models-dev.refreshed": ModelsDevRefreshedProps,
    "credential.updated": CredentialUpdatedProps,
    "credential.switched": CredentialSwitchedProps,
    "integration.updated": IntegrationUpdatedProps,
    "provider.updated": ProviderUpdatedProps,
    "model.updated": ModelUpdatedProps,
    "agent.updated": AgentUpdatedProps,
    "session.created": SessionCreatedProps,
    "session.agent.selected": SessionAgentSelectedProps,
    "session.model.selected": SessionModelSelectedProps,
    "session.moved": SessionMovedProps,
    "session.renamed": SessionRenamedProps,
    "session.metadata.updated": SessionMetadataUpdatedProps,
    "session.permissions": SessionPermissionsProps,
    "session.viewed": SessionViewedProps,
    "session.archived": SessionArchivedProps,
    "session.unarchived": SessionUnarchivedProps,
    "session.usage.updated": SessionUsageUpdatedProps,
    "session.deleted": SessionDeletedProps,
    "session.forked": SessionForkedProps,
    "session.inbox.delivered": SessionInboxDeliveredProps,
    "session.inbox.enqueued": SessionInboxEnqueuedProps,
    "session.inbox.cancelled": SessionInboxCancelledProps,
    "session.inbox.delivery.changed": SessionInboxDeliveryChangedProps,
    "session.execution.started": SessionExecutionStartedProps,
    "session.execution.succeeded": SessionExecutionSucceededProps,
    "session.execution.failed": SessionExecutionFailedProps,
    "session.execution.interrupted": SessionExecutionInterruptedProps,
    "session.instructions.updated": SessionInstructionsUpdatedProps,
    "session.synthetic": SessionSyntheticProps,
    "session.skill.activated": SessionSkillActivatedProps,
    "session.shell.started": SessionShellStartedProps,
    "session.shell.ended": SessionShellEndedProps,
    "session.step.started": SessionStepStartedProps,
    "session.step.first-token": SessionStepFirstTokenProps,
    "session.step.streamed": SessionStepStreamedProps,
    "session.step.ended": SessionStepEndedProps,
    "session.step.failed": SessionStepFailedProps,
    "session.text.started": SessionTextStartedProps,
    "session.text.delta": SessionTextDeltaProps,
    "session.text.ended": SessionTextEndedProps,
    "session.reasoning.started": SessionReasoningStartedProps,
    "session.reasoning.delta": SessionReasoningDeltaProps,
    "session.reasoning.ended": SessionReasoningEndedProps,
    "session.tool.input.started": SessionToolInputStartedProps,
    "session.tool.input.delta": SessionToolInputDeltaProps,
    "session.tool.input.ended": SessionToolInputEndedProps,
    "session.tool.called": SessionToolCalledProps,
    "session.tool.progress": SessionToolProgressProps,
    "session.tool.success": SessionToolSuccessProps,
    "session.tool.failed": SessionToolFailedProps,
    "session.retry.scheduled": SessionRetryScheduledProps,
    "session.compaction.started": SessionCompactionStartedProps,
    "session.compaction.delta": SessionCompactionDeltaProps,
    "session.compaction.ended": SessionCompactionEndedProps,
    "session.compaction.failed": SessionCompactionFailedProps,
    "session.revert.staged": SessionRevertStagedProps,
    "session.revert.cleared": SessionRevertClearedProps,
    "session.revert.committed": SessionRevertCommittedProps,
    "filesystem.changed": FilesystemChangedProps,
    "reference.updated": ReferenceUpdatedProps,
    "permission.asked": PermissionAskedProps,
    "permission.replied": PermissionRepliedProps,
    "plugin.updated": PluginUpdatedProps,
    "project.updated": ProjectUpdatedProps,
    "worktree.updated": WorktreeUpdatedProps,
    "worktree.resolved": WorktreeResolvedProps,
    "command.updated": CommandUpdatedProps,
    "config.updated": ConfigUpdatedProps,
    "skill.updated": SkillUpdatedProps,
    "pty.created": PtyCreatedProps,
    "pty.updated": PtyUpdatedProps,
    "pty.exited": PtyExitedProps,
    "pty.deleted": PtyDeletedProps,
    "persistent-pty.added": PersistentPtyAddedProps,
    "persistent-pty.removed": PersistentPtyRemovedProps,
    "persistent-pty.updated": PersistentPtyUpdatedProps,
    "shell.created": ShellCreatedProps,
    "shell.exited": ShellExitedProps,
    "shell.deleted": ShellDeletedProps,
    "form.created": FormCreatedProps,
    "form.replied": FormRepliedProps,
    "form.cancelled": FormCancelledProps,
    "websearch.updated": WebsearchUpdatedProps,
    "artifact.updated": ArtifactUpdatedProps,
    "session.status": SessionStatusProps,
    "session.idle": SessionIdleProps,
    "tui.prompt.append": TuiPromptAppendProps,
    "tui.command.execute": TuiCommandExecuteProps,
    "tui.toast.show": TuiToastShowProps,
    "tui.session.select": TuiSessionSelectProps,
    "installation.updated": InstallationUpdatedProps,
    "installation.update-available": InstallationUpdateAvailableProps,
    "vcs.branch.updated": VcsBranchUpdatedProps,
    "mcp.status.changed": McpStatusChangedProps,
    "mcp.resources.changed": McpResourcesChangedProps,
    "experimental.mcp.event": ExperimentalMcpEventProps,
    "server.connected": ServerConnectedProps,
}


def parse_typed_event(data: str) -> StreamEvent:
    """Like :func:`parse_stream_event`, but fills defaults from the typed model
    registered for the event type (unknown types are returned as-is)."""
    event = parse_stream_event(data)
    props_cls = EVENT_PROPS_REGISTRY.get(event.type)
    if props_cls is None:
        return event
    props = props_cls.model_construct(**event.properties).model_dump()
    return event.model_copy(update={"properties": props})
