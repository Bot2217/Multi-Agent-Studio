"""
Power management: keep system awake, optionally allow display sleep.
True S3 sleep while agent runs is not supported — processes freeze.
We support:
  - keep_awake: prevent idle sleep (CPU keeps running)
  - keep_display: also keep screen on
  - screen_off_ok: system stays awake, display may turn off
"""

from __future__ import annotations

import platform
import subprocess
import threading
from typing import Optional


class PowerManager:
    def __init__(self):
        self._active = False
        self._mode = "off"
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._system = platform.system()

    @property
    def status(self) -> str:
        return f"keep_awake={self._active}, mode={self._mode}, os={self._system}"

    def start(self, mode: str = "system") -> str:
        """
        mode:
          - system: prevent system sleep, display may sleep
          - display: prevent system + display sleep
        """
        if self._active:
            return f"Already active ({self._mode})"
        self._mode = mode
        self._stop.clear()
        self._active = True

        if self._try_wakepy(mode):
            return f"Keep-awake ON via wakepy (mode={mode})"
        if self._try_keep_awake():
            return f"Keep-awake ON via keep_awake (mode={mode})"
        if self._try_native(mode):
            return f"Keep-awake ON via native OS API (mode={mode})"
        self._active = False
        return (
            "Could not acquire sleep inhibitor. "
            "Install: pip install wakepy  (or keep_awake). "
            "On Linux you may need a desktop session / systemd-logind."
        )

    def stop(self) -> str:
        if not self._active:
            return "Keep-awake was not active"
        self._stop.set()
        self._active = False
        try:
            from wakepy import unset_keepawake
            unset_keepawake()
        except Exception:
            pass
        try:
            from keep_awake import allow_sleep
            allow_sleep()
        except Exception:
            pass
        if self._system == "Windows":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except Exception:
                pass
        return "Keep-awake OFF — system may sleep normally"

    def _try_wakepy(self, mode: str) -> bool:
        try:
            from wakepy import set_keepawake
            set_keepawake(keep_screen_awake=(mode == "display"))
            return True
        except Exception:
            return False

    def _try_keep_awake(self) -> bool:
        try:
            from keep_awake import prevent_sleep
            return bool(prevent_sleep())
        except Exception:
            return False

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
            # caffeinate -i (idle) or -dimsu
            args = ["caffeinate", "-i"]
            if mode == "display":
                args = ["caffeinate", "-dims"]
            try:
                self._proc = subprocess.Popen(args)
                return True
            except Exception:
                return False
        if self._system == "Linux":
            try:
                # systemd-inhibit
                what = "sleep:idle" if mode == "system" else "sleep:idle:handle-lid-switch"
                self._proc = subprocess.Popen(
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
                return True
            except Exception:
                return False
        return False
