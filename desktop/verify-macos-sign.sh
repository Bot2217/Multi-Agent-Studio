#!/usr/bin/env bash
# Confirm the macOS app (and the updater archive, when this build produced one)
# is ad-hoc signed deeply enough for codesign --verify --deep --strict.
# `spctl` is printed and ignored: ad-hoc builds are not notarized, so Gatekeeper
# still needs `xattr -cr` or a right-click Open.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "codesign is macOS-only; skipping"
  exit 0
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/desktop/src-tauri/target/release/bundle/macos"

if [[ ! -d "$BUNDLE" ]]; then
  echo "Нет каталога $BUNDLE" >&2
  exit 1
fi

APP="$(find "$BUNDLE" -name '*.app' -type d -print -quit)"
if [[ -z "$APP" ]]; then
  echo "Не найден .app в $BUNDLE" >&2
  exit 1
fi

echo "codesign --verify --deep --strict: $APP"
codesign --verify --deep --strict --verbose=2 "$APP"

TAR="$(find "$BUNDLE" -name '*.app.tar.gz' -print -quit || true)"
if [[ -n "$TAR" ]]; then
  tmp="$(mktemp -d)"
  tar -xzf "$TAR" -C "$tmp"
  inner="$(find "$tmp" -name '*.app' -type d -print -quit)"
  if [[ -z "$inner" ]]; then
    echo "В $TAR нет .app" >&2
    exit 1
  fi
  echo "codesign --verify --deep --strict (архив обновления): $TAR"
  codesign --verify --deep --strict --verbose=2 "$inner"
  rm -rf "$tmp"
elif [[ "${REQUIRE_UPDATER_ARCHIVE:-}" == "1" ]]; then
  echo "Нет .app.tar.gz, архив обновления не собран из подписанного приложения" >&2
  exit 1
fi

echo "spctl (информационно, отказ Gatekeeper для ad-hoc ожидаем):"
spctl -a -vv "$APP" || true
echo "Подпись codesign в порядке"
