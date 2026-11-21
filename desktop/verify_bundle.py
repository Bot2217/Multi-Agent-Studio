"""Fail the sidecar build when the frozen archive is missing first-party modules.

v0.1.2 collected nothing from the repo root, so the installed executable died
with ``ModuleNotFoundError: No module named 'api'``. PyInstaller still exited 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED = ("api.serve", "api.app", "contracts.v1", "core.paths")


def has_module(names: list[str], module: str) -> bool:
    slashed = module.replace(".", "/") + ".py"
    for name in names:
        normalized = name.replace("\\", "/")
        if normalized in {module, slashed} or normalized.endswith("/" + slashed):
            return True
    return False


def missing_modules(names: list[str], required: tuple[str, ...] = REQUIRED) -> list[str]:
    return [module for module in required if not has_module(names, module)]


def archive_names(path: Path) -> list[str]:
    from PyInstaller.archive.readers import pkg_archive_contents

    return list(pkg_archive_contents(str(path)))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_bundle.py <ulei-backend>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"sidecar archive is missing: {path}", file=sys.stderr)
        return 1
    names = archive_names(path)
    missing = missing_modules(names)
    if missing:
        print(
            "sidecar bundle is missing modules "
            f"({', '.join(missing)}). This is the v0.1.2 failure: "
            "ModuleNotFoundError: No module named 'api'.",
            file=sys.stderr,
        )
        return 1
    print(f"bundle ok {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
