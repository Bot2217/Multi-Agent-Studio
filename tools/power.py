"""
Power management: keep the system awake while a long task runs.

  - mode "system": prevent idle sleep, the display may turn off
  - mode "display": also keep the screen on

Native OS tools come first (caffeinate, SetThreadExecutionState, systemd-inhibit);
wakepy is a fallback. stop() always releases whatever start() acquired.
"""

from __future__ import annotations

import contextlib
import platform
import subprocess
from typing import Optional


class PowerManager:
    def __init__(self):
        self._active = False
        self._mode = "off"
        self._system = platform.system()
        self._proc: Optional[subprocess.Popen] = None
        self._wakepy_stack: Optional[contextlib.ExitStack] = None

    @property
    def status(self) -> str:
        return f"keep_awake={self._active}, mode={self._mode}, os={self._system}"

    def start(self, mode: str = "system") -> str:
        if self._active:
            return f"Already active ({self._mode})"
        mode = "display" if mode == "display" else "system"
        for name, attempt in (("native OS API", self._try_native), ("wakepy", self._try_wakepy)):
            if attempt(mode):
                self._active = True
                self._mode = mode
                return f"Keep-awake ON via {name} (mode={mode})"
        return "Could not acquire a sleep inhibitor on this system; the task runs without it."

    def stop(self) -> str:
        if not self._active:
            return "Keep-awake was not active"
        self._active = False
        self._mode = "off"
        if self._proc is not None:
            with contextlib.suppress(Exception):
                self._proc.terminate()
                self._proc.wait(timeout=5)
            self._proc = None
        if self._wakepy_stack is not None:
            with contextlib.suppress(Exception):
                self._wakepy_stack.close()
            self._wakepy_stack = None
        if self._system == "Windows":
            with contextlib.suppress(Exception):
                import ctypes

                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        return "Keep-awake OFF — system may sleep normally"

    def _spawn(self, args: list[str]) -> bool:
        try:
            self._proc = subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            self._proc = None
            return False
        return True

    def _try_native(self, mode: str) -> bool:
        if self._system == "Windows":
            try:
                import ctypes

                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | optional ES_DISPLAY_REQUIRED
                flags = 0x80000000 | 0x00000001
                if mode == "display":
                    flags |= 0x00000002
                ctypes.windll.kernel32.SetThreadExecutionState(flags)
                return True
            except Exception:
                return False
        if self._system == "Darwin":
            return self._spawn(["caffeinate", "-dims" if mode == "display" else "-i"])
        if self._system == "Linux":
            what = "sleep:idle" if mode == "system" else "sleep:idle:handle-lid-switch"
            return self._spawn(
                [
                    "systemd-inhibit",
                    f"--what={what}",
                    "--who=AgentStudio",
                    "--why=Agent long-running task",
                    "--mode=block",
                    "sleep",
                    "infinity",
                ]
            )
        return False

    def _try_wakepy(self, mode: str) -> bool:
        try:
            from wakepy import keep

            stack = contextlib.ExitStack()
            stack.enter_context(keep.presenting() if mode == "display" else keep.running())
        except Exception:
            return False
        self._wakepy_stack = stack
        return True
