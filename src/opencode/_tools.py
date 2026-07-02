from __future__ import annotations

import glob as glob_mod
import os
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

Permission = str
PERMIT_ALLOW: Permission = "allow"
PERMIT_ASK: Permission = "ask"
PERMIT_DENY: Permission = "deny"

DEFAULT_PERMISSIONS: Dict[str, Permission] = {
    "bash": PERMIT_ASK,
    "write": PERMIT_ALLOW,
    "edit": PERMIT_ALLOW,
    "read": PERMIT_ALLOW,
    "glob": PERMIT_ALLOW,
    "grep": PERMIT_ALLOW,
}


def _default_confirm(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    print(f"\n\033[33m[Tool] {tool_name}({tool_input!r})\033[0m")
    answer = input("  Allow? [Y/n] ").strip().lower()
    return answer not in ("n", "no")


class ToolExecutor:
    def __init__(
        self,
        permissions: Optional[Dict[str, Permission]] = None,
        confirm: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        workdir: Optional[str] = None,
    ):
        self._permissions = {**DEFAULT_PERMISSIONS, **(permissions or {})}
        self._confirm = confirm or _default_confirm
        self._workdir = workdir

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        permit = self._permissions.get(tool_name, PERMIT_ALLOW)
        if permit == PERMIT_DENY:
            return {"error": f"Tool '{tool_name}' is denied by configuration"}
        if permit == PERMIT_ASK:
            allowed = self._confirm(tool_name, tool_input)
            if not allowed:
                return {"error": f"Tool '{tool_name}' was rejected by user"}

        handler = self._handlers().get(tool_name)
        if not handler:
            return {"error": f"Unknown tool '{tool_name}'"}
        return handler(tool_input)

    def _handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
        return {
            "bash": self._bash,
            "write": self._write,
            "edit": self._edit,
            "read": self._read,
            "glob": self._glob,
            "grep": self._grep,
        }

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _bash(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        command = inp.get("command", "")
        timeout = inp.get("timeout", 30)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._workdir,
            )
            return {
                "exitStatus": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"exitStatus": -1, "stdout": "", "stderr": "Command timed out"}

    def _write(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        path = inp.get("path", "")
        content = inp.get("content", "")
        full_path = os.path.join(self._workdir, path) if self._workdir else path
        os.makedirs(os.path.dirname(os.path.abspath(full_path)), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path}

    def _edit(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        path = inp.get("path", "")
        old = inp.get("old", "")
        new = inp.get("new", "")
        full_path = os.path.join(self._workdir, path) if self._workdir else path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                text = f.read()
            if old not in text:
                return {"error": "old string not found", "success": False}
            text = text.replace(old, new, 1)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(text)
            return {"success": True}
        except FileNotFoundError:
            return {"error": f"File not found: {path}", "success": False}

    def _read(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        path = inp.get("path", "")
        full_path = os.path.join(self._workdir, path) if self._workdir else path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}

    def _glob(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        pattern = inp.get("pattern", "")
        full_pattern = os.path.join(self._workdir, pattern) if self._workdir else pattern
        files = glob_mod.glob(full_pattern, recursive=True)
        return {"files": files}

    def _grep(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        pattern = inp.get("pattern", "")
        search_path = inp.get("path", "")
        if search_path:
            full_path = os.path.join(self._workdir, search_path) if self._workdir else search_path
        else:
            full_path = self._workdir or "."
        import re

        results: List[Dict[str, Any]] = []
        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != ".git"]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for lineno, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                results.append({
                                    "path": os.path.relpath(fpath, self._workdir) if self._workdir else fpath,
                                    "line": lineno,
                                    "content": line.rstrip(),
                                })
                except Exception:
                    pass
        return {"results": results}
