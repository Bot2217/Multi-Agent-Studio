"""The frozen sidecar must contain api, and the smoke must reject the v0.1.2 crash."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bundle_listing_requires_the_api_package():
    verify = _load("verify_bundle", "desktop/verify_bundle.py")
    assert verify.missing_modules([]) == list(verify.REQUIRED)
    assert verify.missing_modules(["api.serve", "api.app", "contracts.v1", "core.paths"]) == []
    assert verify.has_module(["api/serve.py"], "api.serve")
    assert not verify.has_module(["core/paths.py"], "api.serve")


def test_smoke_rejects_the_missing_api_traceback():
    smoke = _load("smoke_sidecar", "desktop/smoke_sidecar.py")
    sample = "ModuleNotFoundError: No module named 'api'\n[PYI-1:ERROR] Failed to execute script"
    assert smoke.missing_api(sample)
    assert not smoke.missing_api("READY http://127.0.0.1:9\nAPI_READY http://127.0.0.1:10")


def test_build_script_puts_the_repo_root_on_the_module_path():
    script = (ROOT / "desktop" / "build-backend.sh").read_text(encoding="utf-8")
    assert "--paths ." in script
    assert '--add-data "api${SEP}api"' in script
    assert "verify_bundle.py" in script
