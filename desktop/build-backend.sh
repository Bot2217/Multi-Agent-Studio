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
pyinstaller --noconfirm --clean --onefile --name ulei-backend \
  --collect-all streamlit \
  --collect-all litellm \
  --collect-submodules core \
  --collect-submodules tools \
  --add-data "app.py${SEP}." \
  --add-data "core${SEP}core" \
  --add-data "config${SEP}config" \
  --add-data "tools${SEP}tools" \
  --add-data ".streamlit${SEP}.streamlit" \
  ${CODESIGN[@]+"${CODESIGN[@]}"} \
  desktop/backend_entry.py
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
