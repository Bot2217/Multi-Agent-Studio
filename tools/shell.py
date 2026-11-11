"""
Local shell execution with a timeout, a working-directory fence and a deny-list.

This is a guard rail, not a sandbox: a command that runs can still touch anything
the user account can. The fence keeps the starting directory inside the workspace,
the deny-list stops the best-known destructive commands, and secrets are removed
from the environment so an agent command cannot read API keys.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional

SECRET_ENV_RE = re.compile(r"(API_KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE)

# Matched against the command with whitespace collapsed and lowercased.
_START = r"(?:^|[;&|(]\s*|\bsudo\s+|\bexec\s+)"
DEFAULT_DENY_PATTERNS: list[tuple[str, str]] = [
    ("rm on / or home", r"\brm\s+(?:-\S+\s+)*(?:/|/\*|~|~/|~/\*|\$home|\$\{home\})(?:\s|$|[;&|])"),
    ("mkfs", _START + r"mkfs(?:\.\w+)?\b"),
    ("fork bomb", r":\s*\(\s*\)\s*\{"),
    ("dd to a device", r"\bdd\b[^;&|]*\bof=/dev/"),
    ("shutdown", _START + r"(?:\S*/)?(?:shutdown|reboot|poweroff|halt)\b"),
]


def clean_env(env: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Environment for agent commands without API keys, tokens and passwords."""
    source = os.environ if env is None else env
    return {key: value for key, value in source.items() if not SECRET_ENV_RE.search(key)}


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
        # If allowlist is set, only these command names are allowed
        self.allowlist = allowlist
        if deny_patterns is None:
            self._deny = [(name, re.compile(rx)) for name, rx in DEFAULT_DENY_PATTERNS]
        else:
            self._deny = [(p, re.compile(re.escape(p.lower()))) for p in deny_patterns]

    def blocked_reason(self, command: str) -> Optional[str]:
        # Quotes are dropped too, so "shut""down" is seen as shutdown.
        normalized = " ".join(command.lower().replace('"', "").replace("'", "").split())
        for name, pattern in self._deny:
            if pattern.search(normalized):
                return name
        return None

    def _workdir(self, cwd: Optional[str]) -> Path:
        if not cwd:
            return self.cwd
        candidate = Path(cwd)
        if not candidate.is_absolute():
            candidate = self.cwd / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(self.cwd)
        except ValueError:
            raise PermissionError(f"Working directory outside workspace: {candidate}") from None
        return candidate

    def run(self, command: str, cwd: Optional[str] = None) -> str:
        cmd = command.strip()
        if not cmd:
            return "Empty command"

        reason = self.blocked_reason(cmd)
        if reason:
            return f"Blocked dangerous command pattern: {reason}"

        if self.allowlist:
            try:
                first = shlex.split(cmd)[0]
            except (ValueError, IndexError):
                return "Command could not be parsed"
            base = Path(first).name
            if base not in self.allowlist and first not in self.allowlist:
                return f"Command not in allowlist: {base}\nAllowed: {', '.join(self.allowlist)}"

        try:
            workdir = self._workdir(cwd)
        except PermissionError as exc:
            return str(exc)
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
                env=clean_env(),
            )
            out = []
            if result.stdout:
                out.append(result.stdout)
            if result.stderr:
                out.append("--- stderr ---\n" + result.stderr)
            out.append(f"\n[exit code: {result.returncode}]")
            return "\n".join(out)
        except subprocess.TimeoutExpired:
            return f"Command timed out after {self.timeout}s: {cmd}"
        except Exception as e:
            return f"Shell error: {e}"
