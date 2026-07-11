from opencode._async_client import AsyncOpendcodeClient
from opencode._async_opencode import AsyncOpendcode, async_opencode
from opencode._async_session import AsyncSession
from opencode._client import OpencodeClient
from opencode._errors import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    BinaryNotFoundError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    OpencodeError,
    PermissionDeniedError,
    RateLimitError,
    ServerStartupTimeoutError,
    UnprocessableEntityError,
)
from opencode._logs import setup_logging
from opencode._models import (
    AssistantMessage,
    AssistantMessageReasoning,
    AssistantMessageText,
    AssistantMessageTool,
    SessionInfo,
    SessionMessage,
    UserMessage,
)
from opencode._opencode import Opencode, opencode
from opencode._response_models import OpencodeResponse, RawResponse
from opencode._server import OpencodeServer, create_opencode_server
from opencode._session import Session
from opencode._stream_events import (
    MessagePartDeltaProps,
    MessagePartUpdatedProps,
    MessageUpdatedProps,
    SessionStatusProps,
    StreamEvent,
    parse_stream_event,
)
from opencode._tools import ToolExecutor

setup_logging()

try:
    from importlib.metadata import version as _version

    __version__ = _version("opencode-py")
except:  # noqa: E722
    __version__ = "0.0.0"

__all__ = [
    "APIError",
    "APIConnectionError",
    "APIResponseValidationError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "AssistantMessage",
    "AssistantMessageReasoning",
    "AssistantMessageText",
    "AssistantMessageTool",
    "AsyncOpendcode",
    "AsyncOpendcodeClient",
    "AsyncSession",
    "async_opencode",
    "BadRequestError",
    "BinaryNotFoundError",
    "ConflictError",
    "InternalServerError",
    "NotFoundError",
    "Opencode",
    "OpencodeClient",
    "OpencodeError",
    "OpencodeResponse",
    "OpencodeServer",
    "PermissionDeniedError",
    "RawResponse",
    "RateLimitError",
    "ServerStartupTimeoutError",
    "Session",
    "MessagePartDeltaProps",
    "MessagePartUpdatedProps",
    "MessageUpdatedProps",
    "SessionStatusProps",
    "StreamEvent",
    "ToolExecutor",
    "SessionInfo",
    "SessionMessage",
    "UnprocessableEntityError",
    "UserMessage",
    "create_opencode_server",
    "opencode",
    "parse_stream_event",
]
