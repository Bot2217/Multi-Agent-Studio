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
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

SECRET_ENV_RE = re.compile(r"(API_KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE)

# Matched against the command with whitespace collapsed and lowercased.
_START = r"(?:^|[;&|(]\s*|\bsudo\s+|\bexec\s+)"
DEFAULT_DENY_PATTERNS: list[tuple[str, str]] = [
    (
        "rm of a system or home directory",
        r"\brm\s+(?:-\S+\s+)*(?:~/?\*?|\$home\b|\$\{home\}|/(?:home|root|usr|bin|sbin|etc|var|boot|sys|proc|dev|system|users|volumes|opt|lib|applications)(?:/|\s|$|[;&|])|/(?:\s|$|[;&|])|/\*(?:\s|$|[;&|]))",
    ),
    ("mkfs", _START + r"mkfs(?:\.\w+)?\b"),
    ("fork bomb", r":\s*\(\s*\)\s*\{"),
    ("dd to a device", r"\bdd\b[^;&|]*\bof=/dev/"),
    ("shutdown", _START + r"(?:\S*/)?(?:shutdown|reboot|poweroff|halt)\b"),
    ("curl or wget piped to a shell", r"\b(?:curl|wget)\b[^|&;]*\|\s*(?:ba|z)?sh\b"),
    (
        "windows recursive delete",
        _START + r"(?:del|erase|rd|rmdir)\b[^;&|]*\s/[a-z]*s\b",
    ),
    ("windows format drive", _START + r"format\s+[a-z]:"),
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

    def _kill(self, proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        if os.name == "nt":
            proc.terminate()
        else:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                proc.kill()
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    proc.kill()
            proc.wait(timeout=1)

    def run(
        self,
        command: str,
        cwd: Optional[str] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> str:
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
        if should_stop and should_stop():
            return "Stopped by user"

        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(workdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=clean_env(),
                start_new_session=(os.name != "nt"),
            )
        except Exception as exc:
            return f"Shell error: {exc}"

        deadline = time.monotonic() + self.timeout
        stopped = False
        timed_out = False
        while proc.poll() is None:
            if should_stop and should_stop():
                stopped = True
                self._kill(proc)
                break
            if time.monotonic() > deadline:
                timed_out = True
                self._kill(proc)
                break
            time.sleep(0.05)
        stdout, stderr = proc.communicate()
        if stopped:
            return "Stopped by user"
        if timed_out:
            return f"Command timed out after {self.timeout}s: {cmd}"
        out = []
        if stdout:
            out.append(stdout)
        if stderr:
            out.append("--- stderr ---\n" + stderr)
        out.append(f"\n[exit code: {proc.returncode}]")
        return "\n".join(out)
