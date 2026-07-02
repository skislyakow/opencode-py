from opencode._async_client import AsyncOpendcodeClient
from opencode._async_opencode import AsyncOpendcode, async_opencode
from opencode._async_session import AsyncSession
from opencode._client import OpencodeClient
from opencode._errors import ApiError, BinaryNotFound, OpencodeError, ServerStartupTimeout
from opencode._models import (
    AssistantMessage,
    AssistantMessageReasoning,
    AssistantMessageText,
    AssistantMessageTool,
    SessionMessage,
    SessionInfo,
    UserMessage,
)
from opencode._opencode import Opencode, opencode
from opencode._server import OpencodeServer, create_opencode_server
from opencode._session import Session
from opencode._tools import ToolExecutor

try:
    from importlib.metadata import version as _version
    __version__ = _version("opencode-py")
except:  # noqa: E722
    __version__ = "0.0.0"

__all__ = [
    "ApiError",
    "AssistantMessage",
    "AssistantMessageReasoning",
    "AssistantMessageText",
    "AssistantMessageTool",
    "AsyncOpendcode",
    "AsyncOpendcodeClient",
    "AsyncSession",
    "async_opencode",
    "BinaryNotFound",
    "Opencode",
    "OpendcodeClient",
    "OpendcodeError",
    "OpencodeServer",
    "ServerStartupTimeout",
    "Session",
    "ToolExecutor",
    "SessionInfo",
    "SessionMessage",
    "UserMessage",
    "create_opencode_server",
    "opencode",
]
