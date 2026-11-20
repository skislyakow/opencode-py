from __future__ import annotations

import time
from typing import Any, cast

from opencode._async_client import AsyncOpendcodeClient
from opencode._errors import APITimeoutError, OpencodeError
from opencode._models import SessionMessage
from opencode._opencode import _extract_text
from opencode._response_models import OpencodeResponse, PageResponse, SessionResponse
from opencode._session import (
    _build_reply,
    _check_format,
    _permission_reply,
    _PromptWatch,
    _user_message,
)
from opencode._tools import ToolExecutor


class AsyncSession:
    def __init__(self, client: AsyncOpendcodeClient, session_id: str):
        self._client = client
        self.id = session_id

    async def prompt(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        model: str | dict[str, str] | None = None,
        format: dict[str, Any] | None = None,
        wait: bool = True,
        poll_timeout: float = 600.0,
        collect: bool = False,
        tool_executor: ToolExecutor | None = None,
        quiet: bool = True,
    ) -> OpencodeResponse | SessionMessage:
        """Async version of :meth:`Session.prompt`."""
        _check_format(format)
        if model is not None:
            await self._client.session_switch_model(self.id, model)
        if not wait:
            sent = await self._client.session_prompt(
                self.id, text, files=files, agents=agents, skills=skills
            )
            return _user_message(sent, text)

        deadline = time.monotonic() + poll_timeout
        stream = await self._client.event_subscribe()
        try:
            sent = await self._client.session_prompt(
                self.id, text, files=files, agents=agents, skills=skills
            )
            watch = _PromptWatch(self.id, sent.id or "", collect=collect, quiet=quiet)
            async for line in stream.aiter_lines():
                event = watch.feed(line)
                decision = _permission_reply(event, tool_executor)
                if event is not None and decision is not None:
                    await self._client.session_permission_reply(
                        self.id, event.properties["id"], decision
                    )
                if watch.done:
                    break
                if time.monotonic() > deadline:
                    raise APITimeoutError(
                        f"No reply from session {self.id} within {poll_timeout}s",
                        request=stream.request,
                    )
            else:
                raise OpencodeError(f"Event stream closed before session {self.id} finished")
        finally:
            await stream.aclose()

        reply = _build_reply(await self._client.session_context(self.id), sent.id or "")
        if collect:
            return OpencodeResponse(text=_extract_text(reply), events=list(watch.events))
        return reply

    async def ask(
        self,
        text: str,
        *,
        files: list[dict[str, Any]] | None = None,
        model: str | dict[str, str] | None = None,
        format: dict[str, Any] | None = None,
        tool_executor: ToolExecutor | None = None,
        quiet: bool = False,
        poll_timeout: float = 600.0,
        collect: bool = False,
    ) -> OpencodeResponse | SessionMessage:
        """Async version of :meth:`Session.ask`."""
        return await self.prompt(
            text,
            files=files,
            model=model,
            format=format,
            poll_timeout=poll_timeout,
            collect=collect,
            tool_executor=tool_executor or ToolExecutor(),
            quiet=quiet,
        )

    async def info(self) -> SessionResponse:
        return await self._client.session_get(self.id)

    async def messages(self, **params: Any) -> PageResponse:
        return await self._client.session_messages(self.id, **params)

    async def context(self) -> list[SessionMessage]:
        return cast("list[SessionMessage]", await self._client.session_context(self.id))

    async def compact(self) -> Any:
        return await self._client.session_compact(self.id)

    async def abort(self) -> Any:
        return await self._client.session_interrupt(self.id)

    async def fork(self, *, before: str | None = None) -> SessionResponse:
        return await self._client.session_fork(self.id, before=before)

    async def diff(self) -> Any:
        return await self._client.session_diff(self.id)

    async def delete(self) -> None:
        await self._client.session_delete(self.id)
