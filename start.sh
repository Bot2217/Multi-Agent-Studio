#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "=== Multi-Agent Studio: update + run ==="
if command -v git >/dev/null 2>&1; then
  echo "[1/3] git pull..."
  git pull origin main || echo "pull failed, continue local"
else
  echo "[1/3] git not found, skip"
fi
echo "[2/3] deps..."
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo "[3/3] streamlit..."
exec streamlit run app.py
