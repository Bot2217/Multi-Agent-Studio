"""Provider-agnostic local model runtimes.

Ollama is the first implementation. LM Studio and a llama.cpp server can
follow the same interface later without changing the hive.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import yaml

from core.i18n import t
from core.paths import code_root

LIBRARY_PATH = code_root() / "config" / "ollama_library.yaml"
GIB = 1024**3


def message_for(code: str) -> str:
    key = f"ollama.{code}"
    text = t(key)
    return t("ollama.failed") if text == key else text


class LocalRuntimeError(Exception):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.message = message or message_for(code)
        super().__init__(self.message)


@dataclass
class ModelTag:
    tag: str
    size_bytes: int
    ram_bytes: int

    @property
    def ref_suffix(self) -> str:
        return "" if self.tag in {"", "latest"} else f":{self.tag}"


@dataclass
class LibraryModel:
    model_id: str
    name: str
    summary: str
    tags: list[ModelTag] = field(default_factory=list)

    def reference(self, tag: str) -> str:
        chosen = next((item for item in self.tags if item.tag == tag), None)
        suffix = chosen.ref_suffix if chosen else ("" if tag in {"", "latest"} else f":{tag}")
        return f"{self.model_id}{suffix}"


@dataclass
class InstalledModel:
    name: str
    size_bytes: int


@dataclass
class Probe:
    running: bool = False
    external: bool = False
    binary: str = ""
    managed_binary: bool = False
    error: str = ""
    gpu_note: str = ""


@dataclass
class Fit:
    disk_ok: bool
    ram_ok: bool
    message: str = ""


@dataclass
class RuntimeStatus:
    state: str
    detail: str = ""


class LocalRuntime(Protocol):
    runtime_id: str
    label: str

    def probe(self) -> Probe: ...

    def install(
        self, on_progress: Callable[[str, int, int], None], cancel: Callable[[], bool]
    ) -> None: ...

    def ensure_running(self) -> Probe: ...

    def shutdown(self) -> None: ...

    def installed_models(self) -> list[InstalledModel]: ...

    def pull(
        self,
        name: str,
        on_progress: Callable[[str, int, int], None],
        cancel: Callable[[], bool],
    ) -> None: ...

    def delete_model(self, name: str) -> None: ...

    def warmup(self, name: str) -> None: ...

    def log_tail(self, limit: int = 200) -> str: ...

    def models_dir(self) -> Path: ...

    def disk_free(self) -> int: ...

    def ram_free(self) -> int | None: ...


def app_local_dir() -> Path:
    """Folder the installer does not wipe. Windows uses Local, not Roaming."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "Улей"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Улей"
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "Улей"


def default_ollama_home() -> Path:
    return app_local_dir() / "ollama"


def default_models_dir() -> Path:
    return default_ollama_home() / "models"


def format_bytes(size: int) -> str:
    if size <= 0:
        return t("ollama.size_unknown")
    value = float(size)
    units = [t("unit.b"), t("unit.kb"), t("unit.mb"), t("unit.gb"), t("unit.tb")]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == units[0]:
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} {units[-1]}"


def _gb(value: float) -> int:
    return int(float(value) * GIB)


def load_bundled_library(path: Path | None = None) -> list[LibraryModel]:
    catalog_path = path or LIBRARY_PATH
    if not catalog_path.is_file():
        return []
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    models: list[LibraryModel] = []
    for item in data.get("models") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        tags = []
        for raw in item.get("tags") or []:
            if not isinstance(raw, dict):
                continue
            tags.append(
                ModelTag(
                    tag=str(raw.get("tag") or "latest"),
                    size_bytes=_gb(raw.get("size_gb") or 0),
                    ram_bytes=_gb(raw.get("ram_gb") or 0),
                )
            )
        models.append(
            LibraryModel(
                model_id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                summary=str(item.get("summary") or ""),
                tags=tags or [ModelTag("latest", 0, 0)],
            )
        )
    return models


_LIBRARY_LINK = re.compile(r'href="/library/([a-zA-Z0-9][a-zA-Z0-9._-]*)"', re.I)


def parse_library_html(page: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _LIBRARY_LINK.finditer(page or ""):
        name = match.group(1).strip().lower()
        if not name or name in seen or name in {"library", "search"}:
            continue
        seen.add(name)
        found.append(name)
    return found


def load_library(
    fetch: Callable[[], str] | None = None,
    cache: Path | None = None,
    bundled: list[LibraryModel] | None = None,
    max_age: float = 86400,
    now: float | None = None,
) -> list[LibraryModel]:
    """Live library names when the site answers, otherwise the shipped list."""
    import time

    bundled = list(bundled) if bundled is not None else load_bundled_library()
    page = ""
    if cache and cache.is_file():
        age = (now if now is not None else time.time()) - cache.stat().st_mtime
        if age <= max_age:
            page = cache.read_text(encoding="utf-8")
    if not page and fetch is not None:
        try:
            page = fetch()
        except Exception:
            page = ""
        else:
            if cache is not None:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(page, encoding="utf-8")
    names = parse_library_html(page) if page else []
    return merge_library(bundled, names)


def merge_library(bundled: list[LibraryModel], remote_names: list[str]) -> list[LibraryModel]:
    """Keep curated tags. Names seen only on the site get a single latest tag."""
    known = {model.model_id: model for model in bundled}
    if not remote_names:
        return list(bundled)
    merged: list[LibraryModel] = []
    seen: set[str] = set()
    for name in remote_names:
        seen.add(name)
        merged.append(known.get(name) or LibraryModel(name, name, "", [ModelTag("latest", 0, 0)]))
    for model in bundled:
        if model.model_id not in seen:
            merged.append(model)
    return merged


def assess_fit(size_bytes: int, free_disk: int, ram_bytes: int, free_ram: int | None) -> Fit:
    disk_ok = size_bytes <= 0 or free_disk > size_bytes + 256 * 1024 * 1024
    ram_ok = True
    if ram_bytes > 0 and free_ram is not None and free_ram < ram_bytes:
        ram_ok = False
    if not disk_ok:
        message = f"{t('ollama.disk_full')} " + t(
            "ollama.need_bytes", need=format_bytes(size_bytes), free=format_bytes(free_disk)
        )
    elif not ram_ok:
        message = f"{t('ollama.out_of_memory')} " + t(
            "ollama.need_ram", need=format_bytes(ram_bytes), free=format_bytes(free_ram or 0)
        )
    else:
        message = ""
    return Fit(disk_ok=disk_ok, ram_ok=ram_ok, message=message)


def catalog_entry(model_name: str) -> dict:
    """A free picker row for a model that is already on disk."""
    slug = re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_") or "model"
    return {
        "name": t("ollama.picker_name", name=model_name),
        "provider": t("ollama.provider"),
        "billing": "local",
        "litellm": f"ollama_chat/{model_name}",
        "price_status": "known",
        "price_input_per_1m": 0,
        "price_output_per_1m": 0,
        "free_tier": True,
        "runnable": True,
        "summary": t("ollama.summary"),
        "context": t("ollama.context"),
        "best_for": t("ollama.best_for"),
        "price_note": t("ollama.price_note"),
        "source": "https://ollama.com/library",
        "last_verified": "2026-11-13",
        "availability": "available",
        "_local_key": f"local_{slug}",
    }


def installed_catalog(models: list[InstalledModel]) -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for model in models:
        meta = catalog_entry(model.name)
        catalog[str(meta.pop("_local_key"))] = meta
    return catalog
