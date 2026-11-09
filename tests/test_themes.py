from core.themes import (
    DEFAULT_THEME,
    SCREENS,
    THEME_ORDER,
    THEMES,
    contrast_issues,
    contrast_ratio,
    resolve_screen,
    resolve_theme,
    theme_stylesheet,
)


def test_four_distinct_themes():
    assert THEME_ORDER == ("paper", "night", "kiln", "pine")
    backgrounds = {THEMES[theme_id]["bg"] for theme_id in THEME_ORDER}
    assert len(backgrounds) == 4
    assert {THEMES[theme_id]["mode"] for theme_id in THEME_ORDER} == {"light", "dark"}


def test_unknown_theme_falls_back_to_paper():
    assert resolve_theme(None) == DEFAULT_THEME
    assert resolve_theme("") == "paper"
    assert resolve_theme("neon") == "paper"
    assert resolve_theme("  NIGHT ") == "night"


def test_every_theme_meets_contrast_and_css():
    for theme_id in THEME_ORDER:
        assert contrast_issues(THEMES[theme_id]) == []
        css = theme_stylesheet(theme_id)
        assert f"theme:{theme_id}" in css
        assert THEMES[theme_id]["bg"] in css
        assert THEMES[theme_id]["accent"] in css
        assert "prefers-reduced-motion" in css


def test_design_tokens_fonts_and_nav():
    css = theme_stylesheet("paper")
    for token in ("--space-4", "--radius-m", "--shadow", "--font-mono", "--danger", "--type-lg"):
        assert token in css
    assert "Literata" in css
    assert "Golos Text" in css
    assert "JetBrains Mono" in css
    assert contrast_ratio("#fffaf3", "#8c2f24") >= 4.5
    assert SCREENS[0] == ("run", "Запуск")
    assert resolve_screen("models") == "models"
    assert resolve_screen("nope") == "run"


def test_saved_theme_roundtrip(tmp_path, monkeypatch):
    from core.ui_helpers import load_user_settings, save_user_settings

    path = tmp_path / "user_settings.json"
    monkeypatch.setattr("core.ui_helpers.SETTINGS_PATH", path)
    save_user_settings({"theme": "pine", "pipeline": "code_only"})
    loaded = load_user_settings()
    assert resolve_theme(loaded["theme"]) == "pine"
    assert resolve_theme(loaded.get("missing")) == "paper"
