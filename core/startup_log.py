"""Where the desktop sidecar writes its startup log.

Windows uses LocalAppData, not the install folder and not Roaming settings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def log_path(system: str | None = None) -> Path:
    platform = system or sys.platform
    if platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "ulei" / "logs" / "sidecar.log"
    if platform == "darwin":
        return Path.home() / "Library" / "Logs" / "ulei" / "sidecar.log"
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return base / "ulei" / "logs" / "sidecar.log"
