from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

HERE = Path(__file__).parent


def start_opencode(port: int) -> subprocess.Popen:
    from opencode._binary import ensure_opencode

    binary = ensure_opencode()
    proc = subprocess.Popen(
        [binary, "serve", f"--port={port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(100):
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{port}/global/health")
            if r.status == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError("opencode server did not start")
    return proc


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    opencode_port: int = 4096

    def do_GET(self) -> None:
        if self._serve_static():
            return
        self._proxy("GET")

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self._proxy("POST", body)

    def do_DELETE(self) -> None:
        self._proxy("DELETE")

    def do_PATCH(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self._proxy("PATCH", body)

    def _serve_static(self) -> bool:
        path = self.path.split("?")[0]
        if path == "/":
            path = "/index.html"
        file_path = HERE / path.lstrip("/")
        if file_path.is_file():
            self._serve_file(file_path)
            return True
        return False

    def _serve_file(self, file_path: Path) -> None:
        ext = file_path.suffix
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }
        ctype = content_types.get(ext, "application/octet-stream")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _proxy(self, method: str, body: Optional[bytes] = None) -> None:
        target = f"http://127.0.0.1:{self.opencode_port}{self.path}"
        req = urllib.request.Request(target, data=body, method=method)
        for key in ("Content-Type", "Content-Length"):
            if key in self.headers:
                req.add_header(key, self.headers[key])
        try:
            resp = urllib.request.urlopen(req)
            data = resp.read()
            self.send_response(resp.status)
            ct = resp.headers.get("Content-Type", "application/json")
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            data = e.read()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    # Suppress default logging
    def log_message(self, format: str, *args: Any) -> None:
        pass


def main() -> None:
    opencode_port = 4096
    web_port = 3000

    args = sys.argv[1:]
    if args:
        web_port = int(args[0])
    if len(args) > 1:
        opencode_port = int(args[1])

    print(f"Starting opencode server on port {opencode_port}...")
    opencode_proc = start_opencode(opencode_port)

    ProxyHandler.opencode_port = opencode_port
    server = http.server.HTTPServer(("127.0.0.1", web_port), ProxyHandler)

    print(f"Web UI: http://127.0.0.1:{web_port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        opencode_proc.kill()
        opencode_proc.wait()


if __name__ == "__main__":
    main()
