from core.icons import PATHS, icon
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


def test_themes_are_distinct_and_night_is_default():
    assert DEFAULT_THEME == "night"
    assert THEME_ORDER == ("night", "paper", "ember")
    assert len(THEME_ORDER) <= 4
    backgrounds = {THEMES[theme_id]["bg"] for theme_id in THEME_ORDER}
    assert len(backgrounds) == 3
    assert THEMES["night"]["bg"] == "#0d0e12"
    assert THEMES["night"]["bg"] not in {"#000000", "#ffffff"}
    assert THEMES["paper"]["surface"] not in {"#ffffff", "#000000"}


def test_unknown_and_retired_themes():
    assert resolve_theme(None) == "night"
    assert resolve_theme("neon") == "night"
    assert resolve_theme("  PAPER ") == "paper"
    assert resolve_theme("kiln") == "ember"
    assert resolve_theme("pine") == "night"


def test_every_theme_meets_contrast_and_css():
    for theme_id in THEME_ORDER:
        assert contrast_issues(THEMES[theme_id]) == []
        css = theme_stylesheet(theme_id)
        assert f"theme:{theme_id}" in css
        assert THEMES[theme_id]["bg"] in css
        assert THEMES[theme_id]["accent"] in css
        assert "prefers-reduced-motion" in css
        assert "clamp(" in css
        assert "Inter" in css
        assert "JetBrains Mono" in css
        assert "--space-4: 16px" in css
        assert "--space-5: 24px" in css
        assert "--radius-s: 12px" in css
        assert "--radius-l: 20px" in css


def test_icons_are_stroke_svgs():
    for name in PATHS:
        svg = icon(name)
        assert 'viewBox="0 0 24 24"' in svg
        assert 'stroke-width="2"' in svg
        assert "currentColor" in svg
        assert "emoji" not in svg
    assert contrast_ratio("#f6f3ec", "#0f6b56") >= 4.5


def test_nav_and_saved_theme(tmp_path, monkeypatch):
    from core.ui_helpers import load_user_settings, save_user_settings

    assert SCREENS[0] == ("run", "Запуск")
    assert resolve_screen("models") == "models"
    assert resolve_screen("nope") == "run"
    path = tmp_path / "user_settings.json"
    monkeypatch.setattr("core.ui_helpers.SETTINGS_PATH", path)
    save_user_settings({"theme": "ember", "pipeline": "code_only"})
    loaded = load_user_settings()
    assert resolve_theme(loaded["theme"]) == "ember"
    assert resolve_theme(loaded.get("missing")) == "night"
