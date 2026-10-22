"""
Local shell / bash / cmd execution with timeout and optional allowlist.
"""

from __future__ import annotations

import os
import subprocess
import shlex
from pathlib import Path
from typing import Optional


class ShellRunner:
    def __init__(
        self,
        cwd: str | Path,
        timeout: int = 120,
        allowlist: Optional[list[str]] = None,
        deny_patterns: Optional[list[str]] = None,
    ):
        self.cwd = Path(cwd).resolve()
        self.timeout = timeout
        # If allowlist is set, only these command prefixes are allowed
        self.allowlist = allowlist
        self.deny_patterns = deny_patterns or [
            "rm -rf /",
            "mkfs",
            ":(){",  # fork bomb
            "dd if=/dev/zero",
            "shutdown",
            "reboot",
            "poweroff",
        ]

    def run(self, command: str, cwd: Optional[str] = None) -> str:
        cmd = command.strip()
        if not cmd:
            return "Empty command"

        lower = cmd.lower()
        for bad in self.deny_patterns:
            if bad.lower() in lower:
                return f"Blocked dangerous command pattern: {bad}"

        if self.allowlist:
            first = shlex.split(cmd)[0] if cmd else ""
            base = Path(first).name
            if base not in self.allowlist and first not in self.allowlist:
                return (
                    f"Command not in allowlist: {base}\n"
                    f"Allowed: {', '.join(self.allowlist)}"
                )

        workdir = Path(cwd).resolve() if cwd else self.cwd
        if not workdir.exists():
            return f"Working directory does not exist: {workdir}"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ},
            )
            out = []
            if result.stdout:
                out.append(result.stdout)
            if result.stderr:
                out.append("--- stderr ---\n" + result.stderr)
            out.append(f"\n[exit code: {result.returncode}]")
            return "\n".join(out) if out else f"[exit code: {result.returncode}] (no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {self.timeout}s: {cmd}"
        except Exception as e:
            return f"Shell error: {e}"
