"""Generate src/opencode/_async_client.py from _client.py (sync -> async transform).

Usage:
    python scripts/gen-async-client.py && ruff format src/opencode/_async_client.py
"""

import re
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "src" / "opencode"
s = (PKG / "_client.py").read_text()

# imports / names
s = s.replace(
    "import os\nimport random\nimport time\n", "import asyncio\nimport os\nimport random\n"
)
s = s.replace("class _RawResponseContextManager:", "class _AsyncRawResponseContextManager:")
s = s.replace("_RawResponseContextManager(", "_AsyncRawResponseContextManager(")
s = s.replace("-> _RawResponseContextManager:", "-> _AsyncRawResponseContextManager:")
s = s.replace("class OpencodeClient:", "class AsyncOpendcodeClient:")
s = re.sub(r"\bOpencodeClient\b", "AsyncOpendcodeClient", s)
s = s.replace("httpx.Client", "httpx.AsyncClient")
s = s.replace("time.sleep(", "await asyncio.sleep(")

# reuse module-level helpers from the sync client instead of duplicating them
i = s.index("DEFAULT_MAX_RETRIES = 2")
j = s.index("class _AsyncRawResponseContextManager:")
s = s[:i] + "\n" + s[j:]
SHARED = [
    "_ENVELOPE_KEYS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_USERNAME",
    "INITIAL_RETRY_DELAY",
    "MAX_RETRY_DELAY",
    "PASSWORD_ENV",
    "RETRYABLE_STATUS_CODES",
    "_compact",
    "model_ref",
]
shared_import = "".join(f"    {name},\n" for name in SHARED)
s = s.replace(
    "import httpx\n\n",
    f"import httpx\n\nfrom opencode._client import (\n{shared_import})\n",
)

# request plumbing
s = s.replace("    def _request(\n", "    async def _request(\n")
s = s.replace("    def _request_stream(\n", "    async def _request_stream(\n")
s = s.replace("response = self._client.request(", "response = await self._client.request(")
s = s.replace("response = self._client.send(", "response = await self._client.send(")
s = s.replace(
    "            response.read()\n            response.close()\n",
    "            await response.aread()\n            await response.aclose()\n",
)

# public endpoint methods: everything after the "# Server" section header
k = s.index("    # Server\n")
head, body = s[:k], s[k:]
body = re.sub(r"^    def (\w+)\(", r"    async def \1(", body, flags=re.M)
body = body.replace("self._request(", "await self._request(")
body = body.replace("self._request_stream(", "await self._request_stream(")
body = body.replace(
    "    async def close(self) -> None:\n        self._client.close()\n",
    "    async def close(self) -> None:\n        await self._client.aclose()\n\n"
    "    async def __aenter__(self) -> AsyncOpendcodeClient:\n        return self\n\n"
    "    async def __aexit__(self, *args: Any) -> None:\n        await self.close()\n",
)
header = "# Generated from _client.py by scripts/gen-async-client.py — do not edit by hand.\n"
out = head + body
out = out.replace(
    "from __future__ import annotations\n", header + "from __future__ import annotations\n", 1
)
(PKG / "_async_client.py").write_text(out)
