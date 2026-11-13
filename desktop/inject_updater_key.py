"""Put the updater public key into tauri.conf.json for a release build.

The public key comes from the TAURI_SIGNING_PUBLIC_KEY secret. The private
key is never written into the config. ``--require`` is for the tag build:
without both secrets the updater manifest cannot be signed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "src-tauri" / "tauri.conf.json"
PLACEHOLDER = "REPLACE_ME"


def looks_like_private_key(value: str) -> bool:
    lowered = value.lower()
    return "private key" in lowered or "secret key" in lowered or "BEGIN" in value


def main() -> None:
    require = "--require" in sys.argv[1:]
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    pubkey = os.environ.get("TAURI_SIGNING_PUBLIC_KEY", "").strip()
    private = os.environ.get("TAURI_SIGNING_PRIVATE_KEY", "").strip()
    updater = config.setdefault("plugins", {}).setdefault("updater", {})
    if pubkey:
        if looks_like_private_key(pubkey):
            raise SystemExit(
                "TAURI_SIGNING_PUBLIC_KEY looks like a private key; refusing to write it"
            )
        updater["pubkey"] = pubkey
    signed = bool(pubkey and private)
    if signed:
        config.setdefault("bundle", {})["createUpdaterArtifacts"] = True
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    written = str(updater.get("pubkey", "")).strip()
    if require and (not signed or not written or written == PLACEHOLDER):
        raise SystemExit(
            "Release needs TAURI_SIGNING_PUBLIC_KEY and TAURI_SIGNING_PRIVATE_KEY "
            "so the build can sign updater artifacts"
        )
    print("signed updater" if signed else "installers only, no updater signature")


if __name__ == "__main__":
    main()
