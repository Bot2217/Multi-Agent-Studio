"""Locale catalogs stay in lockstep, and the UI does not keep Russian in source."""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.i18n import get_language, resolve_language, set_language, system_language, t

ROOT = Path(__file__).resolve().parent.parent
UI_FILES = (
    "app.py",
    "core/local_runtime.py",
    "core/ollama_runtime.py",
    "core/themes.py",
    "core/ui_helpers.py",
    "core/orchestrator.py",
    "core/runner.py",
    "core/catalog.py",
    "desktop/backend_entry.py",
    "desktop/index.html",
    "desktop/src-tauri/src/lib.rs",
)
STRINGS = re.compile(
    r"""(?sx)
    (?P<q>\"\"\"|'''|\"|')
    (?P<body>(?:\\.|(?!(?P=q)).)*?)
    (?P=q)
    """
)
CYRILLIC = re.compile(r"[А-Яа-яЁё]+")
# A filesystem folder name, and the marker the orchestrator uses to split a handoff.
ALLOWED_LITERALS = {"OneDrive/Рабочий стол", "=== ИТОГ"}


def test_ru_and_en_have_the_same_keys():
    ru = json.loads((ROOT / "locales" / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    assert set(ru) == set(en)
    empty = [key for key, value in {**ru, **en}.items() if not str(value).strip()]
    assert empty == []


def test_language_switch_and_fallback(monkeypatch):
    set_language("en")
    assert get_language() == "en"
    assert t("nav.run") == "Run"
    assert "11434" in t("ollama.port_busy")
    set_language("ru")
    assert t("nav.run") == "Запуск"
    set_language("de")
    assert get_language() == "ru"
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    monkeypatch.delenv("LANG", raising=False)
    assert system_language() == "en"
    assert resolve_language("auto") == "en"
    monkeypatch.setenv("LC_ALL", "ru_RU.UTF-8")
    assert resolve_language("auto") == "ru"
    monkeypatch.setenv("LC_ALL", "C")
    assert resolve_language("auto") == "ru"


def test_ui_sources_do_not_keep_hardcoded_russian():
    leftovers = []
    for relative in UI_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for match in STRINGS.finditer(text):
            body = match.group("body")
            words = CYRILLIC.findall(body)
            if not words:
                continue
            if body in ALLOWED_LITERALS or all(word == "Улей" for word in words):
                continue
            line = text[: match.start()].count("\n") + 1
            leftovers.append(f"{relative}:{line}: {body[:80]!r}")
    assert leftovers == []
