"""The desktop shell and the Python package publish one version."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"', text)
    assert match, "pyproject.toml has no version"
    return match.group(1)


def test_release_version_matches_everywhere():
    version = _pyproject_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)

    cargo = (ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8")
    assert f'version = "{version}"' in cargo.split("[dependencies]", 1)[0]

    package = json.loads((ROOT / "desktop/package.json").read_text(encoding="utf-8"))
    assert package["version"] == version

    lock = json.loads((ROOT / "desktop/package-lock.json").read_text(encoding="utf-8"))
    assert lock["version"] == version
    assert lock["packages"][""]["version"] == version

    tauri = json.loads((ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    assert tauri["version"] == version

    cargo_lock = (ROOT / "desktop/src-tauri/Cargo.lock").read_text(encoding="utf-8")
    assert f'name = "ulei"\nversion = "{version}"' in cargo_lock
