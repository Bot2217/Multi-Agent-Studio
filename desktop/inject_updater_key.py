"""Drop the updater public key into tauri.conf.json when the CI secret is set."""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "src-tauri" / "tauri.conf.json"


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    pubkey = os.environ.get("TAURI_SIGNING_PUBLIC_KEY", "").strip()
    private = os.environ.get("TAURI_SIGNING_PRIVATE_KEY", "").strip()
    if pubkey:
        config.setdefault("plugins", {}).setdefault("updater", {})["pubkey"] = pubkey
    if pubkey and private:
        config.setdefault("bundle", {})["createUpdaterArtifacts"] = True
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = "signed updater" if pubkey and private else "installers only, no updater signature"
    print(state)


if __name__ == "__main__":
    main()
