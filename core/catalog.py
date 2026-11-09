"""Model catalog: loading, validation, prices, and provider routing."""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "config" / "models_catalog.yaml"

BILLING_VALUES = {"free", "freemium", "paid", "local", "unknown"}
PRICE_STATUS_VALUES = {"known", "unknown"}
AVAILABILITY_VALUES = {"available", "deprecated", "preview", "alias", "unknown"}
FREE_BILLINGS = {"free", "freemium", "local"}

# Hosted providers. Ollama runs on the user's machine and does not need a key.
KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
}

LOCAL_PROVIDERS = {"ollama"}

# Longer prefixes first so "openrouter/" is not mistaken for another provider.
PROVIDER_PREFIXES = (
    ("openrouter/", "openrouter"),
    ("ollama_chat/", "ollama"),
    ("ollama/", "ollama"),
    ("anthropic/", "anthropic"),
    ("openai/", "openai"),
    ("gemini/", "gemini"),
    ("xai/", "xai"),
    ("deepseek/", "deepseek"),
    ("groq/", "groq"),
    ("mistral/", "mistral"),
    ("cerebras/", "cerebras"),
)

BILLING_BADGE = {
    "free": "Free",
    "freemium": "Free tier",
    "paid": "Paid",
    "local": "Local",
    "unknown": "Unknown",
}

REQUIRED_STRINGS = (
    "litellm",
    "name",
    "provider",
    "billing",
    "price_status",
    "price_note",
    "context",
    "best_for",
    "summary",
    "source",
    "last_verified",
    "availability",
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_models_catalog(path: Path | None = None) -> dict[str, dict[str, Any]]:
    catalog_path = Path(path) if path else CATALOG_PATH
    if not catalog_path.exists():
        return {}
    with open(catalog_path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    models = data.get("models") or {}
    if not isinstance(models, dict):
        raise ValueError("models_catalog.yaml: 'models' must be a mapping")
    return models


def provider_of(model_id: str) -> str:
    lowered = str(model_id or "").lower()
    for prefix, name in PROVIDER_PREFIXES:
        if lowered.startswith(prefix):
            return name
    return "openai"


def is_free_option(meta: dict[str, Any]) -> bool:
    return meta.get("billing") in FREE_BILLINGS


def is_runnable(meta: dict[str, Any]) -> bool:
    return bool(meta.get("runnable", True))


def api_base_for(model_id: str, meta: dict[str, Any] | None = None) -> str | None:
    if meta and meta.get("api_base"):
        return str(meta["api_base"])
    if provider_of(model_id) == "ollama":
        return os.getenv("OLLAMA_API_BASE") or "http://localhost:11434"
    return None


def credential_env(model_id: str) -> str | None:
    return KEY_ENV.get(provider_of(model_id))


def needs_api_key(model_id: str) -> bool:
    return provider_of(model_id) not in LOCAL_PROVIDERS


def format_price(meta: dict[str, Any]) -> str:
    if meta.get("price_status") != "known":
        return "unknown"
    price_in = meta.get("price_input_per_1m")
    price_out = meta.get("price_output_per_1m")
    if price_in is None or price_out is None:
        return "unknown"
    return f"${_num(price_in)} / ${_num(price_out)} за 1M"


def _num(value: Any) -> str:
    number = float(value)
    if number == 0:
        return "0"
    if number.is_integer():
        return str(int(number))
    text = f"{number:.4f}".rstrip("0")
    whole, frac = text.split(".")
    if len(frac) < 2:
        frac = frac.ljust(2, "0")
    return f"{whole}.{frac}"


def model_label(
    key: str,
    catalog: dict[str, dict[str, Any]],
    models_map: dict | None = None,
) -> str:
    meta = catalog.get(key) or {}
    name = meta.get("name") or key
    badge = BILLING_BADGE.get(str(meta.get("billing") or ""), "")
    parts = [str(name)]
    if badge:
        parts.append(badge)
    if meta:
        parts.append(format_price(meta))
    elif models_map and key in models_map:
        parts.append(str(models_map[key]))
    return " · ".join(parts)


def resolve_model(
    model_key: str,
    cfg: dict | None = None,
    catalog: dict | None = None,
) -> str:
    catalog = catalog or {}
    cfg = cfg or {}
    litellm_id = (catalog.get(model_key) or {}).get("litellm")
    if litellm_id:
        return str(litellm_id)
    models = cfg.get("models") or {}
    if model_key in models:
        return str(models[model_key])
    return str(model_key)


def missing_credentials(
    model_keys: list[str],
    api_keys: dict[str, str] | None,
    catalog: dict[str, dict[str, Any]],
    cfg: dict | None = None,
) -> list[tuple[str, str, str]]:
    """Hosted models whose API key is empty. Local models are skipped."""
    missing: list[tuple[str, str, str]] = []
    keys = api_keys or {}
    for model_key in model_keys:
        model_id = resolve_model(model_key, cfg, catalog)
        if not needs_api_key(model_id):
            continue
        env_name = credential_env(model_id)
        if not env_name:
            continue
        if not str(keys.get(env_name) or "").strip():
            missing.append((model_key, provider_of(model_id), env_name))
    return missing


def runnable_models(catalog: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {key: meta for key, meta in catalog.items() if is_runnable(meta)}


def sorted_model_keys(catalog: dict[str, dict[str, Any]]) -> list[str]:
    """Free options first, then provider and name."""

    def sort_key(model_key: str) -> tuple:
        meta = catalog.get(model_key) or {}
        return (
            0 if is_free_option(meta) else 1,
            str(meta.get("provider") or ""),
            str(meta.get("name") or model_key).lower(),
        )

    return sorted(catalog, key=sort_key)


def validate_catalog(
    catalog: dict[str, dict[str, Any]],
    today: date | None = None,
) -> list[str]:
    today = today or date.today()
    errors: list[str] = []
    if not catalog:
        return ["catalog is empty"]
    for key, meta in catalog.items():
        if not isinstance(meta, dict):
            errors.append(f"{key}: entry must be a mapping")
            continue
        for field in REQUIRED_STRINGS:
            value = meta.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{key}: missing {field}")
        billing = meta.get("billing")
        if billing not in BILLING_VALUES:
            errors.append(f"{key}: bad billing {billing!r}")
        status = meta.get("price_status")
        if status not in PRICE_STATUS_VALUES:
            errors.append(f"{key}: bad price_status {status!r}")
        availability = meta.get("availability")
        if availability not in AVAILABILITY_VALUES:
            errors.append(f"{key}: bad availability {availability!r}")
        if "runnable" in meta and not isinstance(meta["runnable"], bool):
            errors.append(f"{key}: runnable must be bool")
        if "free_tier" in meta and not isinstance(meta["free_tier"], bool):
            errors.append(f"{key}: free_tier must be bool")
        litellm_id = str(meta.get("litellm") or "")
        if "/" not in litellm_id:
            errors.append(f"{key}: litellm id must include a provider prefix")
        source = str(meta.get("source") or "")
        parsed = urlparse(source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{key}: source must be an http(s) URL")
        verified = str(meta.get("last_verified") or "")
        if not DATE_RE.match(verified):
            errors.append(f"{key}: last_verified must be YYYY-MM-DD")
        else:
            year, month, day = (int(part) for part in verified.split("-"))
            try:
                seen = date(year, month, day)
            except ValueError:
                errors.append(f"{key}: last_verified is not a real date")
            else:
                if seen > today:
                    errors.append(f"{key}: last_verified is in the future")
        context_tokens = meta.get("context_tokens", None)
        if context_tokens is not None and (
            isinstance(context_tokens, bool)
            or not isinstance(context_tokens, int)
            or context_tokens <= 0
        ):
            errors.append(f"{key}: context_tokens must be a positive int or null")
        price_in = meta.get("price_input_per_1m", None)
        price_out = meta.get("price_output_per_1m", None)
        if status == "unknown":
            if price_in is not None or price_out is not None:
                errors.append(f"{key}: unknown price must not invent numbers")
        elif status == "known":
            if not _is_price(price_in) or not _is_price(price_out):
                errors.append(f"{key}: known price needs numeric input and output per 1M")
            elif billing in {"free", "local"} and (float(price_in) != 0 or float(price_out) != 0):
                errors.append(f"{key}: free/local token price must be 0")
            elif billing == "freemium" and (float(price_in) <= 0 or float(price_out) <= 0):
                errors.append(f"{key}: freemium stores the paid rate and it must be > 0")
        if billing in FREE_BILLINGS and meta.get("free_tier") is not True:
            errors.append(f"{key}: free_tier must be true when a free option exists")
        if billing in {"paid", "unknown"} and meta.get("free_tier") is True:
            errors.append(f"{key}: free_tier must not be true for paid/unknown billing")
        note = str(meta.get("price_note") or "")
        if status == "unknown" and "unknown" not in note.lower():
            errors.append(f"{key}: unverifiable price_note must contain 'unknown'")
        if billing == "freemium" and "free" not in note.lower():
            errors.append(f"{key}: freemium price_note must mention the free tier")
    return errors


def _is_price(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) >= 0


def markdown_table(catalog: dict[str, dict[str, Any]]) -> str:
    header = (
        "| Модель | Провайдер | ID | Доступ | Цена, USD / 1M in → out | Контекст | Проверено |\n"
        "| --- | --- | --- | --- | --- | --- | --- |"
    )
    lines = [header]
    badge = {
        "free": "Free",
        "freemium": "Free tier",
        "paid": "Paid",
        "local": "Local",
        "unknown": "Unknown",
    }
    for meta in catalog.values():
        price = format_price(meta)
        if meta.get("price_status") == "known" and meta.get("billing") == "freemium":
            price = f"{price} (paid); free tier $0"
        context = meta.get("context") or "unknown"
        lines.append(
            "| {name} | {provider} | `{litellm}` | {access} | {price} | {context} | {verified} |".format(
                name=meta.get("name", ""),
                provider=meta.get("provider", ""),
                litellm=meta.get("litellm", ""),
                access=badge.get(meta.get("billing"), meta.get("billing")),
                price=price,
                context=context,
                verified=meta.get("last_verified", ""),
            )
        )
    return "\n".join(lines)
