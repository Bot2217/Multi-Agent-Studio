#!/usr/bin/env bash
# Запуск студии. Обновление из git только по просьбе: ./start.sh --update
set -e
cd "$(dirname "$0")"
if [ "$1" = "--update" ] && command -v git >/dev/null 2>&1; then
  echo "git pull..."
  git pull --ff-only || echo "pull не удался, запускаю локальную версию"
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -q -r requirements.txt
exec streamlit run app.py
