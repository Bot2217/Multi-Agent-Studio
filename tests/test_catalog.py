from datetime import date
from pathlib import Path

from core.catalog import (
    format_price,
    is_free_option,
    load_models_catalog,
    missing_credentials,
    model_label,
    provider_of,
    resolve_model,
    validate_catalog,
)
from core.orchestrator import load_config


def test_shipped_catalog_is_valid():
    catalog = load_models_catalog()
    assert len(catalog) >= 40
    errors = validate_catalog(catalog, today=date(2026, 11, 9))
    assert errors == []


def test_known_corrections():
    catalog = load_models_catalog()
    assert catalog["gpt_5"]["context_tokens"] == 400000
    assert catalog["gpt_5"]["availability"] == "deprecated"
    assert catalog["gpt_6_luna"]["context_tokens"] == 1050000
    assert catalog["gpt_6_luna"]["price_input_per_1m"] == 0.10
    assert catalog["claude_sonnet_45"]["availability"] == "deprecated"
    assert catalog["claude_sonnet_55"]["price_input_per_1m"] == 2
    assert catalog["claude_sonnet_55"]["price_output_per_1m"] == 10
    assert catalog["gemini_25_flash"]["billing"] == "freemium"
    assert catalog["gemini_25_flash"]["context_tokens"] == 1000000
    assert catalog["gemini_25_flash"]["price_output_per_1m"] == 2.50
    assert catalog["deepseek_flash"]["litellm"] == "deepseek/deepseek-flash"
    assert catalog["deepseek_flash"]["price_input_per_1m"] == 0.15
    assert catalog["grok_47"]["litellm"] == "xai/grok-4.7"
    assert catalog["grok_build"]["litellm"] == "xai/grok-build-0.1"
    assert all(meta["litellm"] != "xai/grok-4" for meta in catalog.values())
    assert all("deepseek-chat" not in meta["litellm"] for meta in catalog.values())
    assert catalog["or_gemma_4_31b"]["price_input_per_1m"] == 0
    assert catalog["or_gemma_4_31b"]["billing"] == "free"
    assert catalog["cerebras_gpt_oss_120b"]["price_status"] == "unknown"
    assert catalog["cerebras_gpt_oss_120b"]["price_input_per_1m"] is None
    assert "unknown" in catalog["cerebras_gpt_oss_120b"]["price_note"]
    assert catalog["ollama_gemma4"]["billing"] == "local"
    assert catalog["mistral_moderation"]["runnable"] is False


def test_free_filter_and_labels():
    catalog = load_models_catalog()
    free = [key for key, meta in catalog.items() if is_free_option(meta)]
    assert len(free) >= 20
    assert "gemini_38_flash" in free
    assert "ollama_gemma4" in free
    assert "gpt_6_astra" not in free
    label = model_label("gemini_25_flash_lite", catalog)
    assert "Free tier" in label
    assert "unknown" == format_price(catalog["cerebras_qwen38_27b"])


def test_provider_routing():
    assert provider_of("openrouter/google/gemma-4-31b-it:free") == "openrouter"
    assert provider_of("ollama_chat/gemma4") == "ollama"
    assert provider_of("groq/openai/gpt-oss-20b") == "groq"
    assert provider_of("gemini/gemini-2.5-flash") == "gemini"
    assert provider_of("anthropic/claude-sonnet-5-5") == "anthropic"
    assert provider_of("xai/grok-4.7") == "xai"
    assert provider_of("deepseek/deepseek-flash") == "deepseek"
    assert provider_of("mistral/mistral-large-4") == "mistral"
    assert provider_of("cerebras/gpt-oss-120b") == "cerebras"


def test_resolve_prefers_catalog_over_stale_map():
    catalog = {"demo": {"litellm": "gemini/gemini-2.5-flash"}}
    cfg = {"models": {"demo": "openai/gpt-4o"}}
    assert resolve_model("demo", cfg, catalog) == "gemini/gemini-2.5-flash"
    assert resolve_model("openai/gpt-4o-mini", {}, {}) == "openai/gpt-4o-mini"


def test_missing_credentials_skips_local():
    catalog = load_models_catalog()
    missing = missing_credentials(
        ["gemini_38_flash", "ollama_gemma4"],
        {},
        catalog,
    )
    assert missing == [("gemini_38_flash", "gemini", "GOOGLE_API_KEY")]
    assert missing_credentials(["gemini_38_flash"], {"GOOGLE_API_KEY": "k"}, catalog) == []


def test_agent_config_points_at_catalog():
    catalog = load_models_catalog()
    cfg = load_config()
    for key, litellm_id in (cfg.get("models") or {}).items():
        assert key in catalog
        assert catalog[key]["litellm"] == litellm_id
    for agent_id, agent in (cfg.get("agents") or {}).items():
        assert agent["model"] in catalog
        assert catalog[agent["model"]]["runnable"] is True
    for _role, suggestions in (cfg.get("recommendations") or {}).items():
        for key in suggestions:
            assert key in catalog


def test_readme_lists_every_model():
    readme = Path("README.md").read_text(encoding="utf-8")
    for meta in load_models_catalog().values():
        assert meta["name"] in readme
        assert meta["litellm"] in readme


def test_validator_rejects_invented_unknown_price():
    bad = {
        "x": {
            "litellm": "openai/x",
            "name": "X",
            "provider": "OpenAI",
            "billing": "paid",
            "free_tier": False,
            "price_status": "unknown",
            "price_input_per_1m": 1,
            "price_output_per_1m": 2,
            "price_note": "unknown but we guessed",
            "context": "unknown",
            "context_tokens": None,
            "best_for": "test",
            "summary": "test",
            "source": "https://example.com",
            "last_verified": "2026-11-09",
            "availability": "unknown",
            "runnable": True,
        }
    }
    errors = validate_catalog(bad, today=date(2026, 11, 9))
    assert any("must not invent" in error for error in errors)
