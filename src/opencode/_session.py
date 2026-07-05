from __future__ import annotations

from typing import Any, cast

from opencode._client import OpencodeClient
from opencode._models import SessionMessage
from opencode._response_models import V1SessionResponse
from opencode._tools import ToolExecutor


class Session:
    def __init__(self, client: OpencodeClient, session_id: str):
        self._client = client
        self.id = session_id
        self._auto_confirmed: bool = False

    def prompt(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        references: list[dict[str, Any]] | None = None,
        model: dict[str, str] | None = None,
        format: dict[str, Any] | None = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> SessionMessage:
        parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
        body: dict[str, Any] = {"parts": parts}
        if model:
            body["model"] = model
        if format:
            body["format"] = format

        # Use V1 sync prompt (POST /session/:id/message)
        result = self._client.session_send(self.id, body)

        parts_list = (
            result.parts if isinstance(result, V1SessionResponse) else result.get("parts", [])
        )
        info = result.info if isinstance(result, V1SessionResponse) else result.get("info", {})
        structured = getattr(result, "structured", None) or info.get("structured")
        text_parts: list[dict[str, Any]] = []
        for p in parts_list:
            ptype = p.get("type", "")
            if ptype in ("text", "reasoning", "tool"):
                text_parts.append({"type": ptype, "text": p.get("text", "")})
        msg: dict[str, Any] = {
            "id": info.get("id", ""),
            "type": "assistant",
            "content": text_parts,
            "model": info.get("model"),
            "time": info.get("time", {}),
        }
        if structured is not None:
            msg["structured"] = structured
        return cast(SessionMessage, msg)

    def ask(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        model: dict[str, str] | None = None,
        format: dict[str, Any] | None = None,
        max_tool_rounds: int = 25,
        tool_executor: ToolExecutor | None = None,
        quiet: bool = False,
    ) -> SessionMessage:
        if tool_executor is None:
            tool_executor = ToolExecutor()
        parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
        if files:
            parts.extend(files)

        for _round in range(max_tool_rounds):
            body: dict[str, Any] = {"parts": parts}
            if model:
                body["model"] = model
            if format:
                body["format"] = format

            result = self._client.session_send(self.id, body)
            if not isinstance(result, V1SessionResponse) and not isinstance(result, dict):
                return cast(SessionMessage, result)

            parts_list = (
                result.parts if isinstance(result, V1SessionResponse) else result.get("parts", [])
            )
            info = result.info if isinstance(result, V1SessionResponse) else result.get("info", {})

            tool_uses = [p for p in parts_list if p.get("type") == "tool-use"]
            if tool_uses:
                self._auto_confirmed = True
                results: list[dict[str, Any]] = []
                for tu in tool_uses:
                    tool_name = tu.get("tool", {}).get("name", "")
                    tool_input = tu.get("tool", {}).get("input", {})
                    tool_id = tu.get("toolUseID", "")
                    if not quiet:
                        print(f"\033[33m[Tool] {tool_name}\033[0m")
                    output = tool_executor.execute(tool_name, tool_input)
                    results.append(
                        {
                            "type": "tool-result",
                            "toolUseID": tool_id,
                            "tool": {"name": tool_name},
                            "output": output,
                        }
                    )

                parts = results
                continue

            # No tool-use parts — model may be planning or asking.
            if not self._auto_confirmed:
                self._auto_confirmed = True
                parts = [
                    {
                        "type": "text",
                        "text": "Exit plan mode and proceed. Use tools as needed.",
                    }
                ]
                continue

            # Final response (no tool calls, already confirmed)
            text_parts: list[dict[str, Any]] = []
            for p in parts_list:
                ptype = p.get("type", "")
                if ptype in ("text", "reasoning", "tool"):
                    text_parts.append({"type": ptype, "text": p.get("text", "")})
            msg: dict[str, Any] = {
                "id": info.get("id", ""),
                "type": "assistant",
                "content": text_parts,
                "model": info.get("model"),
                "time": info.get("time", {}),
            }
            structured = getattr(result, "structured", None) or info.get("structured")
            if structured is not None:
                msg["structured"] = structured
            return cast(SessionMessage, msg)

        raise RuntimeError(f"Tool loop exceeded {max_tool_rounds} rounds")

    def messages(self, **kwargs: Any) -> Any:
        return self._client.v2_session_messages(self.id, **kwargs)

    def context(self, **kwargs: Any) -> list[SessionMessage]:
        return cast("list[SessionMessage]", self._client.v2_session_context(self.id, **kwargs))

    def delete_message(self, message_id: str, **kwargs: Any) -> Any:
        return self._client.session_delete_message(self.id, message_id, **kwargs)

    def compact(self) -> Any:
        return self._client.v2_session_compact(self.id)

    def abort(self) -> Any:
        return self._client.session_abort(self.id)

    def fork(self, **kwargs: Any) -> Any:
        return self._client.session_fork(self.id, **kwargs)

    def diff(self) -> Any:
        return self._client.session_diff(self.id)

    def todo(self) -> Any:
        return self._client.session_todo(self.id)
