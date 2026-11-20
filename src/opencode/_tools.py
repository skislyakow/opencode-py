from __future__ import annotations

from collections.abc import Callable
from typing import Any

Permission = str
PERMIT_ALLOW: Permission = "allow"
PERMIT_ASK: Permission = "ask"
PERMIT_DENY: Permission = "deny"

# Keyed by the permission ``action`` the server asks about (usually the tool name).
DEFAULT_PERMISSIONS: dict[str, Permission] = {
    "bash": PERMIT_ASK,
    "shell": PERMIT_ASK,
}


def _default_confirm(action: str, request: dict[str, Any]) -> bool:
    resources = ", ".join(request.get("resources", []))
    print(f"\n\033[33m[Permission] {action}: {resources}\033[0m")
    answer = input("  Allow? [Y/n] ").strip().lower()
    return answer not in ("n", "no")


class ToolExecutor:
    """Answers permission requests raised by the opencode server while it runs tools.

    In the opencode v2 API tools execute on the server. When the server's
    permission rules say ``ask``, it emits a ``permission.asked`` event; the
    session forwards it here. ``permissions`` maps an action (``shell``,
    ``edit``, ...) to ``allow``, ``ask`` or ``deny``; unlisted actions are
    allowed. ``confirm`` is called for ``ask`` and defaults to a console prompt.
    """

    def __init__(
        self,
        permissions: dict[str, Permission] | None = None,
        confirm: Callable[[str, dict[str, Any]], bool] | None = None,
    ):
        self._permissions = {**DEFAULT_PERMISSIONS, **(permissions or {})}
        self._confirm = confirm or _default_confirm

    def decide(self, request: dict[str, Any]) -> str:
        """Return the server reply (``once`` or ``reject``) for a permission request."""
        action = str(request.get("action", ""))
        permit = self._permissions.get(action, PERMIT_ALLOW)
        if permit == PERMIT_DENY:
            return "reject"
        if permit == PERMIT_ASK and not self._confirm(action, request):
            return "reject"
        return "once"
