"""
Filesystem tools with automatic backups before destructive operations.
All paths are restricted to the configured workspace root (and optional extra roots).
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


class WorkspaceFS:
    def __init__(
        self,
        workspace_root: str | Path,
        backup_dir: str | Path,
        extra_roots: Optional[list[str | Path]] = None,
    ):
        self.root = Path(workspace_root).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.extra_roots = [Path(r).resolve() for r in (extra_roots or [])]
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str | Path) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        p = p.resolve()
        allowed = [self.root] + self.extra_roots
        if not any(str(p).startswith(str(r)) for r in allowed):
            raise PermissionError(
                f"Path outside allowed workspace: {p}. Allowed roots: {allowed}"
            )
        return p

    def _backup(self, path: Path) -> Optional[Path]:
        if not path.exists():
            return None
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        rel = path.relative_to(self.root) if str(path).startswith(str(self.root)) else path.name
        dest = self.backup_dir / f"{ts}_{str(rel).replace(os.sep, '__')}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)
        return dest

    def list_dir(self, path: str = ".") -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"Path does not exist: {p}"
        if not p.is_dir():
            return f"Not a directory: {p}"
        lines = []
        for item in sorted(p.iterdir()):
            kind = "DIR " if item.is_dir() else "FILE"
            size = item.stat().st_size if item.is_file() else 0
            lines.append(f"{kind}  {item.name}  ({size} bytes)")
        return "\n".join(lines) or "(empty)"

    def read_file(self, path: str, max_bytes: int = 200_000) -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"File not found: {p}"
        if not p.is_file():
            return f"Not a file: {p}"
        data = p.read_bytes()
        if len(data) > max_bytes:
            return (
                data[:max_bytes].decode("utf-8", errors="replace")
                + f"\n\n... [truncated, total {len(data)} bytes]"
            )
        return data.decode("utf-8", errors="replace")

    def write_file(self, path: str, content: str, create_dirs: bool = True) -> str:
        p = self._resolve(path)
        backup = None
        if p.exists():
            backup = self._backup(p)
        if create_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        msg = f"Written: {p}"
        if backup:
            msg += f"\nBackup: {backup}"
        return msg

    def append_file(self, path: str, content: str) -> str:
        p = self._resolve(path)
        if p.exists():
            self._backup(p)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to: {p}"

    def delete_path(self, path: str) -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"Nothing to delete: {p}"
        backup = self._backup(p)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return f"Deleted: {p}\nBackup: {backup}"

    def move_path(self, src: str, dst: str) -> str:
        s = self._resolve(src)
        d = self._resolve(dst)
        if not s.exists():
            return f"Source not found: {s}"
        if d.exists():
            self._backup(d)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        return f"Moved: {s} -> {d}"

    def copy_path(self, src: str, dst: str) -> str:
        s = self._resolve(src)
        d = self._resolve(dst)
        if not s.exists():
            return f"Source not found: {s}"
        if d.exists():
            self._backup(d)
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
        return f"Copied: {s} -> {d}"

    def search_text(self, pattern: str, path: str = ".", max_hits: int = 50) -> str:
        root = self._resolve(path)
        hits = []
        for file in root.rglob("*"):
            if not file.is_file():
                continue
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.lower() in line.lower():
                    hits.append(f"{file.relative_to(self.root)}:{i}: {line.strip()[:200]}")
                    if len(hits) >= max_hits:
                        return "\n".join(hits)
        return "\n".join(hits) if hits else "No matches"
