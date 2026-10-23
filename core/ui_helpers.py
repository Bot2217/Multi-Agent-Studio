from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
SETTINGS_PATH = ROOT / "user_settings.json"

KEY_NAMES = ["ANTHROPIC_API_KEY","OPENAI_API_KEY","GOOGLE_API_KEY","XAI_API_KEY","DEEPSEEK_API_KEY"]

def load_keys_from_env():
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH, override=True)
    return {k: os.getenv(k, "") or "" for k in KEY_NAMES}

def save_keys_to_env(keys, extra=None):
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            s=line.strip()
            if not s or s.startswith("#") or "=" not in line: continue
            k,_,v=line.partition("=")
            existing[k.strip()]=v.strip().strip('"').strip("'")
    for k,v in (keys or {}).items():
        if v and str(v).strip(): existing[k]=str(v).strip()
    if extra:
        for k,v in extra.items():
            if v and str(v).strip(): existing[k]=str(v).strip()
    ENV_PATH.write_text("\n".join(f"{k}={v}" for k,v in existing.items())+"\n", encoding="utf-8")
    for k,v in existing.items(): os.environ[k]=v
    return str(ENV_PATH)

def load_user_settings():
    if SETTINGS_PATH.exists():
        try: return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception: return {}
    return {}

def save_user_settings(data):
    data = dict(data)
    data["updated_at"]=datetime.now().isoformat(timespec="seconds")
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_models_catalog():
    p = ROOT / "config" / "models_catalog.yaml"
    if not p.exists(): return {}
    with open(p, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("models") or {}

def model_label(key, catalog, models_map):
    meta = catalog.get(key) or {}
    name = meta.get("name") or key
    free = " 🟢 FREE" if meta.get("free_tier") else ""
    price = meta.get("price_note") or ""
    return f"{name}{free}" + (f" · {price}" if price else "")

def preset_paths(default_ws):
    home = Path.home()
    items = [("Проект", default_ws), ("Home", home), ("Desktop", home/"Desktop"),
             ("Documents", home/"Documents"), ("Downloads", home/"Downloads")]
    for name in ("OneDrive/Desktop", "OneDrive/Рабочий стол"):
        p = home / Path(name)
        if p.exists(): items.append((name, p))
    return items
