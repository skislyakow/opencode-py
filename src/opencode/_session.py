from __future__ import annotations

from typing import Any, cast

from opencode._client import OpencodeClient
from opencode._models import SessionMessage
from opencode._response_models import OpencodeResponse, V1SessionResponse
from opencode._tools import ToolExecutor


class Session:
    def __init__(self, client: OpencodeClient, session_id: str):
        self._client = client
        self.id = session_id
        self._auto_confirmed: bool = False

    def _prompt_v2(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        references: list[dict[str, Any]] | None = None,
        timeout: float = 600.0,
    ) -> SessionMessage | None:
        """V2 prompt via SSE subscription. Returns None on failure (falls back to V1)."""
        import time as _time

        import httpx

        from opencode._stream_events import parse_stream_event

        try:
            response = self._client.event_subscribe()
            assert isinstance(response, httpx.Response)

            prompt_body: dict[str, Any] = {"text": text}
            if files:
                prompt_body["files"] = files
            if agents:
                prompt_body["agents"] = agents
            if references:
                prompt_body["references"] = references

            # Send V2 prompt (non-blocking)
            self._client.v2_session_prompt(self.id, prompt_body, delivery="queue")

            # Wait for step.ended for our session
            start = _time.time()
            our_prompt_seen = False

            for line in response.iter_lines():
                if _time.time() - start > timeout:
                    break

                if not line.startswith("data: "):
                    continue

                event = parse_stream_event(line[6:])
                props = event.properties

                sid = props.get("sessionID")
                if sid is not None and sid != self.id:
                    continue

                if event.type == "session.next.prompted":
                    our_prompt_seen = True

                if event.type == "session.next.step.ended" and our_prompt_seen:
                    _time.sleep(0.2)
                    break

            if not our_prompt_seen:
                return None

            # Read context to get the assistant message
            ctx = self._client.v2_session_context(self.id)
            messages: list[Any] = ctx.get("data", []) if isinstance(ctx, dict) else ctx

            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("type") == "assistant":
                    parts_list: list[dict[str, Any]] = []
                    for p in msg.get("content", []):
                        ptype = p.get("type", "")
                        if ptype in ("text", "reasoning", "tool"):
                            parts_list.append({"type": ptype, "text": p.get("text", "")})

                    return cast(SessionMessage, {
                        "id": msg.get("id", ""),
                        "type": "assistant",
                        "content": parts_list,
                        "model": msg.get("model"),
                        "time": msg.get("time", {}),
                    })

            return None

        except Exception:
            return None

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
        collect: bool = False,
    ) -> OpencodeResponse | SessionMessage:
        # Try V2 + SSE first (unless model/format specified — not supported by V2)
        if wait and model is None and format is None:
            v2_result = self._prompt_v2(
                text, files=files, agents=agents, references=references, timeout=poll_timeout,
            )
            if v2_result is not None:
                if collect:
                    from opencode._opencode import _extract_text
                    return OpencodeResponse(text=_extract_text(v2_result))
                return v2_result

        # Fall back to V1
        parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
        body: dict[str, Any] = {"parts": parts}
        if model:
            body["model"] = model
        if format:
            body["format"] = format

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
        result_msg = cast(SessionMessage, msg)
        if collect:
            from opencode._opencode import _extract_text

            return OpencodeResponse(text=_extract_text(result_msg))
        return result_msg

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
        collect: bool = False,
    ) -> OpencodeResponse | SessionMessage:
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
                early_msg = cast(SessionMessage, result)
                if collect:
                    from opencode._opencode import _extract_text
                    return OpencodeResponse(text=_extract_text(early_msg))
                return early_msg

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
            result_msg = cast(SessionMessage, msg)
            if collect:
                from opencode._opencode import _extract_text
                return OpencodeResponse(text=_extract_text(result_msg))
            return result_msg

        raise RuntimeError(f"Tool loop exceeded {max_tool_rounds} rounds")

    def messages(self, **kwargs: Any) -> Any:
        return self._client.v2_session_messages(self.id, **kwargs)

    def context(self, **kwargs: Any) -> list[SessionMessage]:
        ctx = self._client.v2_session_context(self.id, **kwargs)
        messages = ctx.get("data", []) if isinstance(ctx, dict) else ctx
        return cast("list[SessionMessage]", messages)

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
