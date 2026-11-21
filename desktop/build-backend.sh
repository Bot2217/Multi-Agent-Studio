#!/usr/bin/env bash
# Freeze the Streamlit app into the sidecar name Tauri expects for this host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m pip install -q -r requirements.txt pyinstaller
HOST="$(rustc -vV | sed -n 's/^host: //p')"
if [[ -z "$HOST" ]]; then
  echo "rustc не сообщил host triple" >&2
  exit 1
fi
SEP=":"
EXT=""
CODESIGN=()
case "$HOST" in
  *windows*) SEP=";"; EXT=".exe" ;;
esac
if [[ "$(uname -s)" == "Darwin" ]]; then
  CODESIGN=(--codesign-identity - --osx-entitlements-file desktop/src-tauri/entitlements.plist)
fi
# backend_entry.py lives in desktop/, and PyInstaller searches only that
# directory unless the repo root is on --paths. v0.1.2 therefore shipped a
# sidecar whose module graph listed "missing module named api" and crashed
# with ModuleNotFoundError before it listened. --paths . is what collects
# api, contracts and the rest of this repo. The add-data copies keep the
# same packages on disk if a later analysis pass skips a delayed import.
pyinstaller --noconfirm --clean --onefile --name ulei-backend \
  --paths . \
  --collect-all streamlit \
  --collect-all litellm \
  --collect-all fastapi \
  --collect-all starlette \
  --collect-all uvicorn \
  --collect-submodules core \
  --collect-submodules tools \
  --collect-submodules api \
  --collect-submodules contracts \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import websockets \
  --collect-all websockets \
  --hidden-import api \
  --hidden-import api.serve \
  --hidden-import api.app \
  --hidden-import api.trust \
  --hidden-import api.runner \
  --hidden-import api.hive \
  --hidden-import api.bus \
  --hidden-import contracts \
  --hidden-import contracts.v1 \
  --hidden-import core \
  --hidden-import core.paths \
  --hidden-import core.startup_log \
  --hidden-import yaml \
  --add-data "app.py${SEP}." \
  --add-data "api${SEP}api" \
  --add-data "contracts${SEP}contracts" \
  --add-data "core${SEP}core" \
  --add-data "config${SEP}config" \
  --add-data "tools${SEP}tools" \
  --add-data ".streamlit${SEP}.streamlit" \
  --add-data "locales${SEP}locales" \
  ${CODESIGN[@]+"${CODESIGN[@]}"} \
  desktop/backend_entry.py
python3 desktop/verify_bundle.py "dist/ulei-backend${EXT}"
mkdir -p desktop/src-tauri/binaries
SIDECAR="desktop/src-tauri/binaries/ulei-backend-${HOST}${EXT}"
cp "dist/ulei-backend${EXT}" "$SIDECAR"
chmod +x "$SIDECAR" || true
if [[ "$(uname -s)" == "Darwin" ]]; then
  codesign --force --sign - --timestamp=none \
    --entitlements desktop/src-tauri/entitlements.plist \
    "$SIDECAR"
  codesign --verify --strict --verbose=2 "$SIDECAR"
fi
echo "sidecar $SIDECAR"
