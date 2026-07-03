from __future__ import annotations

from typing import Any


class OpencodeError(Exception):
    """Base exception for all opencode SDK errors."""

    def __init__(
        self,
        message: str = "",
        *,
        status: int | None = None,
        body: object = None,
    ):
        self.status = status
        self.body = body
        super().__init__(message)


class APIError(OpencodeError):
    """Base class for all API-related errors."""

    def __init__(
        self,
        message: str = "",
        *,
        request: Any = None,
        response: Any = None,
        body: object = None,
        status_code: int | None = None,
    ):
        self.request = request
        self.response = response
        super().__init__(message, status=status_code, body=body)


class APIResponseValidationError(APIError):
    """Response data did not match the expected schema."""

    def __init__(self, message: str = "", *, response: Any = None, body: object = None):
        super().__init__(message, response=response, body=body)


class APIStatusError(APIError):
    """Base class for errors with an HTTP status code."""


class BadRequestError(APIStatusError):
    """HTTP 400"""


class AuthenticationError(APIStatusError):
    """HTTP 401"""


class PermissionDeniedError(APIStatusError):
    """HTTP 403"""


class NotFoundError(APIStatusError):
    """HTTP 404"""


class ConflictError(APIStatusError):
    """HTTP 409"""


class UnprocessableEntityError(APIStatusError):
    """HTTP 422"""


class RateLimitError(APIStatusError):
    """HTTP 429"""


class InternalServerError(APIStatusError):
    """HTTP 5xx"""


class APIConnectionError(APIError):
    """Connection or transport error."""


class APITimeoutError(APIConnectionError):
    """Request timed out."""


class BinaryNotFoundError(OpencodeError):
    """Opencode binary not found on the system."""


class ServerStartupTimeoutError(OpencodeError):
    """Server did not start within the expected timeout."""
