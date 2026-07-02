from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Optional

from opencode._async_client import AsyncOpendcodeClient
from opencode._async_session import AsyncSession
from opencode._models import SessionMessage
from opencode._opencode import _extract_text, _resolve_model
from opencode._server import OpencodeServer, create_opencode_server


class AsyncOpendcode:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        hostname: str = "127.0.0.1",
        port: int = 4096,
        directory: Optional[str] = None,
        workspace: Optional[str] = None,
        server_timeout: float = 30.0,
        client_timeout: float = 300.0,
        config: Optional[Dict[str, Any]] = None,
        opencode_binary: Optional[str] = None,
    ):
        self._model = model
        self._hostname = hostname
        self._port = port
        self._directory = directory
        self._workspace = workspace
        self._server_timeout = server_timeout
        self._client_timeout = client_timeout
        self._config = config
        self._opencode_binary = opencode_binary

        self._server: Optional[OpencodeServer] = None
        self._client: Optional[AsyncOpendcodeClient] = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> AsyncOpendcode:
        self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Server / Client lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._client is not None:
            return
        server = create_opencode_server(
            hostname=self._hostname,
            port=self._port,
            timeout=self._server_timeout,
            config=self._config,
            opencode_binary=self._opencode_binary,
        )
        client = AsyncOpendcodeClient(
            base_url=server.url,
            directory=self._directory,
            workspace=self._workspace,
            timeout=self._client_timeout,
        )
        self._server = server
        self._client = client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        if self._server:
            self._server.close()
            self._server = None

    @property
    def client(self) -> AsyncOpendcodeClient:
        assert self._client is not None
        return self._client

    @property
    def server(self) -> OpencodeServer:
        assert self._server is not None
        return self._server

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    async def create_session(self, agent: Optional[str] = None, **kwargs) -> AsyncSession:
        if agent:
            kwargs["agent"] = agent
        raw = await self.client.session_create(**kwargs)
        sid = raw["id"]
        return AsyncSession(self.client, sid)

    async def ask(
        self,
        prompt: str,
        *,
        files: Optional[Dict[str, Any]] = None,
        auto_tools: bool = False,
        agent: Optional[str] = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> str:
        session = await self.create_session(agent=agent)
        model = _resolve_model(model=self._model, config=self._config)
        if auto_tools:
            from opencode._tools import ToolExecutor

            msg = await session.ask(
                prompt,
                files=files,
                model=model,
                tool_executor=ToolExecutor(),
            )
        else:
            msg = await session.prompt(
                prompt,
                files=files,
                wait=wait,
                model=model,
                poll_interval=poll_interval,
                poll_timeout=poll_timeout,
            )
        return _extract_text(msg)

    async def ask_stream(
        self,
        prompt: str,
        *,
        files: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        import json

        session = await self.create_session()
        prompt_body: Dict[str, Any] = {"text": prompt}
        if files:
            prompt_body["files"] = files

        await self.client.v2_session_prompt(session.id, prompt_body, delivery="steer")

        import httpx

        response = await self.client.event_subscribe()
        assert isinstance(response, httpx.Response)
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            if payload.get("type") == "message.part.delta":
                delta = payload.get("properties", {}).get("delta", "")
                if delta:
                    yield delta
