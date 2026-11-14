"""User-facing strings for the studio, the Ollama manager, and the desktop shell.

Language "auto" follows the operating system and falls back to Russian.
Callers that are not the UI leave the language at its default, Russian, so
tests stay stable on an English CI machine.
"""

from __future__ import annotations

import json
import locale
import os
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

from core.paths import code_root

SUPPORTED = ("ru", "en")
DEFAULT = "ru"
_language: ContextVar[str] = ContextVar("ulei_language", default=DEFAULT)


def locales_dir() -> Path:
    return code_root() / "locales"


@lru_cache(maxsize=4)
def _load(lang: str) -> dict[str, str]:
    path = locales_dir() / f"{lang}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def catalog(lang: str | None = None) -> dict[str, str]:
    chosen = lang or _language.get()
    if chosen not in SUPPORTED:
        chosen = DEFAULT
    return _load(chosen)


def system_language() -> str:
    """English when the OS locale is English. Anything else is Russian."""
    raw = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    if not raw:
        try:
            raw = locale.getlocale()[0] or ""
        except Exception:
            raw = ""
    return "en" if raw.lower().startswith("en") else DEFAULT


def resolve_language(choice: str | None) -> str:
    value = str(choice or "auto").strip().lower()
    if value == "auto":
        return system_language()
    if value in SUPPORTED:
        return value
    return DEFAULT


def set_language(choice: str | None) -> str:
    resolved = resolve_language(choice)
    _language.set(resolved)
    return resolved


def get_language() -> str:
    return _language.get()


def t(key: str, **kwargs: object) -> str:
    text = catalog().get(key)
    if text is None and get_language() != DEFAULT:
        text = _load(DEFAULT).get(key)
    if text is None:
        text = key
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (IndexError, KeyError, ValueError):
        return text


def role_word(count: int) -> str:
    """Russian and English plural for the chain caption."""
    if get_language() == "en":
        key = "chain.role_one" if count == 1 else "chain.role_many"
        return t(key, n=count)
    n10 = abs(count) % 10
    n100 = abs(count) % 100
    if n10 == 1 and n100 != 11:
        key = "chain.role_one"
    elif n10 in (2, 3, 4) and n100 not in (12, 13, 14):
        key = "chain.role_few"
    else:
        key = "chain.role_many"
    return t(key, n=count)
