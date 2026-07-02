from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from opencode._client import OpencodeClient
from opencode._models import SessionMessage


class Session:
    def __init__(self, client: OpencodeClient, session_id: str):
        self._client = client
        self.id = session_id

    def prompt(
        self,
        text: str,
        *,
        files: Optional[List[Dict[str, Any]]] = None,
        agents: Optional[List[Dict[str, Any]]] = None,
        references: Optional[List[Dict[str, Any]]] = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> SessionMessage:
        prompt: Dict[str, Any] = {"text": text}
        if files:
            prompt["files"] = files
        if agents:
            prompt["agents"] = agents
        if references:
            prompt["references"] = references

        delivery = "deferred" if wait else "immediate"
        msg = self._client.v2_session_prompt(self.id, prompt, delivery=delivery)

        if wait:
            self._wait_until_idle(poll_interval, poll_timeout)
            messages = self._client.v2_session_context(self.id)
            if messages:
                return messages[-1]

        return msg

    def _wait_until_idle(self, interval: float = 0.5, timeout: float = 600.0) -> None:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                self._client.v2_session_wait(self.id)
                return
            except Exception:
                time.sleep(interval)
        raise TimeoutError(f"Session {self.id} did not become idle within {timeout}s")

    def messages(self, **kwargs) -> Any:
        return self._client.v2_session_messages(self.id, **kwargs)

    def context(self, **kwargs) -> List[SessionMessage]:
        return self._client.v2_session_context(self.id, **kwargs)

    def compact(self) -> Any:
        return self._client.v2_session_compact(self.id)

    def abort(self) -> Any:
        return self._client.session_abort(self.id)

    def fork(self, **kwargs) -> Any:
        return self._client.session_fork(self.id, **kwargs)

    def diff(self) -> Any:
        return self._client.session_diff(self.id)

    def todo(self) -> Any:
        return self._client.session_todo(self.id)
