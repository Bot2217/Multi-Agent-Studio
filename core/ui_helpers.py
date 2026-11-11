from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from core.catalog import KEY_ENV

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
SETTINGS_PATH = ROOT / "user_settings.json"

KEY_NAMES = list(dict.fromkeys(KEY_ENV.values()))


def load_keys_from_env():
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH, override=True)
    return {k: os.getenv(k, "") or "" for k in KEY_NAMES}


def save_keys_to_env(keys, extra=None):
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            existing[k.strip()] = v.strip().strip('"').strip("'")
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
    ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in existing.items()) + "\n", encoding="utf-8")
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
        ("Проект", Path(default_ws)),
        ("Home", home),
        ("Desktop", home / "Desktop"),
        ("Documents", home / "Documents"),
        ("Downloads", home / "Downloads"),
    ]
    items = []
    for label, path in candidates:
        if label == "Проект" or path.exists():
            items.append((label, path))
    for name in ("OneDrive/Desktop", "OneDrive/Рабочий стол"):
        path = home / Path(name)
        if path.exists():
            items.append((name, path))
    return items
