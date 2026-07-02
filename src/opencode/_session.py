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
        model: Optional[Dict[str, str]] = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> SessionMessage:
        parts: List[Dict[str, Any]] = [{"type": "text", "text": text}]
        body: Dict[str, Any] = {"parts": parts}
        if model:
            body["model"] = model

        # Use V1 sync prompt (POST /session/:id/message)
        result = self._client.session_send(self.id, body)

        if isinstance(result, dict):
            parts_list = result.get("parts", [])
            info = result.get("info", {})
            # Convert parts to V2-like SessionMessage format
            text_parts: List[Dict[str, Any]] = []
            for p in parts_list:
                ptype = p.get("type", "")
                if ptype in ("text", "reasoning", "tool"):
                    text_parts.append({"type": ptype, "text": p.get("text", "")})
            return {
                "id": info.get("id", ""),
                "type": "assistant",
                "content": text_parts,
                "model": info.get("model"),
                "time": info.get("time", {}),
            }

        return result

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
