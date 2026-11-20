from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from core.catalog import KEY_ENV
from core.paths import data_root

_DATA = data_root()
ENV_PATH = _DATA / ".env"
SETTINGS_PATH = _DATA / "user_settings.json"

KEY_NAMES = list(dict.fromkeys(KEY_ENV.values()))


def load_keys_from_env():
    from dotenv import load_dotenv

    from core.secrets import active_store, enable_system_keyring

    load_dotenv(ENV_PATH, override=True)
    file_keys = {name: os.getenv(name, "") or "" for name in KEY_NAMES}
    enable_system_keyring()
    store = active_store()
    if store is None:
        return file_keys
    loaded = {}
    migrated = False
    for name in KEY_NAMES:
        stored = store.get(name) or ""
        if stored:
            loaded[name] = stored
            os.environ[name] = stored
            if file_keys.get(name):
                migrated = True
        elif file_keys.get(name):
            store.set(name, file_keys[name])
            loaded[name] = file_keys[name]
            migrated = True
        else:
            loaded[name] = ""
    if migrated:
        _write_env({key: value for key, value in _read_env().items() if key not in KEY_NAMES})
    return loaded


def _read_env() -> dict[str, str]:
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            existing[key.strip()] = value.strip().strip('"').strip("'")
    return existing


def _write_env(existing: dict[str, str]) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{key}={value}" for key, value in existing.items())
    ENV_PATH.write_text((body + "\n") if body else "", encoding="utf-8")


def save_keys_to_env(keys, extra=None):
    from core.secrets import active_store

    existing = _read_env()
    for k, v in (keys or {}).items():
        if v and str(v).strip():
            existing[k] = str(v).strip()
        elif k in existing:
            # An emptied field removes the key instead of silently keeping the old one.
            del existing[k]
            os.environ.pop(k, None)
    if extra:
        for k, v in extra.items():
            if v and str(v).strip():
                existing[k] = str(v).strip()
    store = active_store()
    if store is not None:
        for name in list(existing):
            if name in KEY_NAMES and existing[name]:
                store.set(name, existing[name])
                os.environ[name] = existing[name]
                del existing[name]
    _write_env(existing)
    for k, v in existing.items():
        os.environ[k] = v
    return str(ENV_PATH)


def load_user_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_user_settings(data):
    data = dict(data)
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def preset_paths(default_ws):
    home = Path.home()
    candidates = [
        ("project", Path(default_ws)),
        ("Home", home),
        ("Desktop", home / "Desktop"),
        ("Documents", home / "Documents"),
        ("Downloads", home / "Downloads"),
    ]
    items = []
    for label, path in candidates:
        if label == "project" or path.exists():
            items.append((label, path))
    for name in ("OneDrive/Desktop", "OneDrive/Рабочий стол"):
        path = home / Path(name)
        if path.exists():
            items.append((name, path))
    return items
