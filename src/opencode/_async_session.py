from __future__ import annotations

from typing import Any, Dict, List, Optional

from opencode._async_client import AsyncOpendcodeClient
from opencode._models import SessionMessage
from opencode._tools import ToolExecutor


class AsyncSession:
    def __init__(self, client: AsyncOpendcodeClient, session_id: str):
        self._client = client
        self.id = session_id
        self._auto_confirmed: bool = False

    async def prompt(
        self,
        text: str,
        *,
        files: Optional[List[Dict[str, Any]]] = None,
        agents: Optional[List[Dict[str, Any]]] = None,
        references: Optional[List[Dict[str, Any]]] = None,
        model: Optional[Dict[str, str]] = None,
        format: Optional[Dict[str, Any]] = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> SessionMessage:
        parts: List[Dict[str, Any]] = [{"type": "text", "text": text}]
        body: Dict[str, Any] = {"parts": parts}
        if model:
            body["model"] = model
        if format:
            body["format"] = format

        result = await self._client.session_send(self.id, body)

        if isinstance(result, dict):
            parts_list = result.get("parts", [])
            info = result.get("info", {})
            structured = result.get("structured") or info.get("structured")
            text_parts: List[Dict[str, Any]] = []
            for p in parts_list:
                ptype = p.get("type", "")
                if ptype in ("text", "reasoning", "tool"):
                    text_parts.append({"type": ptype, "text": p.get("text", "")})
            msg: Dict[str, Any] = {
                "id": info.get("id", ""),
                "type": "assistant",
                "content": text_parts,
                "model": info.get("model"),
                "time": info.get("time", {}),
            }
            if structured is not None:
                msg["structured"] = structured
            return msg

        return result

    async def ask(
        self,
        text: str,
        *,
        files: Optional[List[Dict[str, Any]]] = None,
        model: Optional[Dict[str, str]] = None,
        format: Optional[Dict[str, Any]] = None,
        max_tool_rounds: int = 25,
        tool_executor: Optional[ToolExecutor] = None,
        quiet: bool = False,
    ) -> SessionMessage:
        if tool_executor is None:
            tool_executor = ToolExecutor()
        parts: List[Dict[str, Any]] = [{"type": "text", "text": text}]
        if files:
            parts.extend(files)

        for _round in range(max_tool_rounds):
            body: Dict[str, Any] = {"parts": parts}
            if model:
                body["model"] = model
            if format:
                body["format"] = format

            result = await self._client.session_send(self.id, body)
            if not isinstance(result, dict):
                return result

            parts_list = result.get("parts", [])
            info = result.get("info", {})

            tool_uses = [p for p in parts_list if p.get("type") == "tool-use"]
            if tool_uses:
                self._auto_confirmed = True
                results: List[Dict[str, Any]] = []
                for tu in tool_uses:
                    tool_name = tu.get("tool", {}).get("name", "")
                    tool_input = tu.get("tool", {}).get("input", {})
                    tool_id = tu.get("toolUseID", "")
                    if not quiet:
                        print(f"\033[33m[Tool] {tool_name}\033[0m")
                    output = tool_executor.execute(tool_name, tool_input)
                    results.append({
                        "type": "tool-result",
                        "toolUseID": tool_id,
                        "tool": {"name": tool_name},
                        "output": output,
                    })

                parts = results
                continue

            if not self._auto_confirmed:
                self._auto_confirmed = True
                parts = [{"type": "text", "text": "Exit plan mode and proceed with execution now. Use tools as needed."}]
                continue

            text_parts: List[Dict[str, Any]] = []
            for p in parts_list:
                ptype = p.get("type", "")
                if ptype in ("text", "reasoning", "tool"):
                    text_parts.append({"type": ptype, "text": p.get("text", "")})
            msg: Dict[str, Any] = {
                "id": info.get("id", ""),
                "type": "assistant",
                "content": text_parts,
                "model": info.get("model"),
                "time": info.get("time", {}),
            }
            structured = result.get("structured") or info.get("structured")
            if structured is not None:
                msg["structured"] = structured
            return msg

        raise RuntimeError(f"Tool loop exceeded {max_tool_rounds} rounds")

    async def messages(self, **kwargs) -> Any:
        return await self._client.v2_session_messages(self.id, **kwargs)

    async def context(self, **kwargs) -> List[SessionMessage]:
        return await self._client.v2_session_context(self.id, **kwargs)

    async def compact(self) -> Any:
        return await self._client.v2_session_compact(self.id)

    async def abort(self) -> Any:
        return await self._client.session_abort(self.id)

    async def fork(self, **kwargs) -> Any:
        return await self._client.session_fork(self.id, **kwargs)

    async def diff(self) -> Any:
        return await self._client.session_diff(self.id)

    async def todo(self) -> Any:
        return await self._client.session_todo(self.id)
