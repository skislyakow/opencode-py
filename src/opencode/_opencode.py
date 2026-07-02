from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from opencode._client import OpencodeClient
from opencode._models import SessionMessage
from opencode._server import OpencodeServer, create_opencode_server
from opencode._session import Session


class Opencode:
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
        self._client: Optional[OpencodeClient] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Opencode:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
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
        client = OpencodeClient(
            base_url=server.url,
            directory=self._directory,
            workspace=self._workspace,
            timeout=self._client_timeout,
        )
        self._server = server
        self._client = client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        if self._server:
            self._server.close()
            self._server = None

    @property
    def client(self) -> OpencodeClient:
        self.start()
        assert self._client is not None
        return self._client

    @property
    def server(self) -> OpencodeServer:
        self.start()
        assert self._server is not None
        return self._server

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def create_session(self, **kwargs) -> Session:
        raw = self.client.session_create(**kwargs)
        sid = raw["id"]
        return Session(self.client, sid)

    def ask(
        self,
        prompt: str,
        *,
        files: Optional[List[Dict[str, Any]]] = None,
        wait: bool = True,
        poll_interval: float = 0.5,
        poll_timeout: float = 600.0,
    ) -> str:
        session = self.create_session()
        msg = session.prompt(
            prompt,
            files=files,
            wait=wait,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
        )
        return _extract_text(msg)

    def ask_stream(
        self,
        prompt: str,
        *,
        files: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        import json

        session = self.create_session()
        prompt_body: Dict[str, Any] = {"text": prompt}
        if files:
            prompt_body["files"] = files

        self.client.v2_session_prompt(session.id, prompt_body, delivery="immediate")

        import httpx

        response = self.client.event_subscribe()
        assert isinstance(response, httpx.Response)
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            if payload.get("type") == "message.part.delta":
                delta = payload.get("properties", {}).get("delta", "")
                if delta:
                    yield delta


def _extract_text(msg: SessionMessage) -> str:
    if isinstance(msg, dict) and msg.get("type") == "assistant":
        parts = msg.get("content", [])
        texts: List[str] = []
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
        return "\n".join(texts)
    if isinstance(msg, dict) and msg.get("type") == "user":
        return msg.get("text", "")
    return str(msg)


def opencode(
    prompt: str,
    *,
    model: Optional[str] = None,
    port: int = 4096,
    directory: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    cfg = dict(config or {})
    if model:
        cfg["model"] = model
    with Opencode(port=port, directory=directory, config=cfg or None) as ai:
        return ai.ask(prompt)
