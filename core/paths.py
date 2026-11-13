"""Where the program files live, and where a desktop install keeps user data."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def code_root() -> Path:
    """Directory that contains app.py, config/ and core/."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def desktop_data_dir() -> Path:
    """Per-user folder for the installed app. The directory name is the Latin id."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "ulei"


def data_root() -> Path:
    """Settings, keys and the default workspace.

    The desktop build (MAS_DESKTOP=1) uses desktop_data_dir unless MAS_DATA_DIR
    is set. A checkout leaves data next to the code.
    """
    override = os.environ.get("MAS_DATA_DIR", "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if os.environ.get("MAS_DESKTOP") == "1":
        path = desktop_data_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path
    return code_root()


def _migration_sources() -> list[Path]:
    home = Path.home()
    names = ("Multi-Agent-Studio", "Multi-Agent-Studio-main")
    bases = [
        Path.cwd(),
        home,
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "Рабочий стол",
    ]
    extra = os.environ.get("MAS_MIGRATE_FROM", "").strip()
    if extra:
        bases.insert(0, Path(extra))
    found: list[Path] = []
    seen: set[Path] = set()
    for base in bases:
        candidates = [base, *[base / name for name in names]]
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen or not candidate.is_dir():
                continue
            seen.add(resolved)
            found.append(candidate)
    return found


def migrate_user_files(data: Path | None = None) -> list[str]:
    """Copy user_settings.json and .env into the data dir once.

    Existing files in the data dir are left alone. Returns the names copied.
    """
    destination = data or data_root()
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in ("user_settings.json", ".env"):
        target = destination / name
        if target.exists():
            continue
        for source_dir in _migration_sources():
            source = source_dir / name
            if not source.is_file():
                continue
            try:
                if source.resolve() == target.resolve():
                    continue
            except OSError:
                continue
            shutil.copy2(source, target)
            copied.append(name)
            break
    for folder in ("workspace", "results", "backups"):
        (destination / folder).mkdir(exist_ok=True)
    return copied
