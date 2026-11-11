from core.themes import (
    DEFAULT_PALETTE,
    DEFAULT_THEME,
    PALETTES,
    SCREENS,
    THEME_ORDER,
    contrast_issues,
    resolve_palette,
    resolve_screen,
    resolve_theme,
    theme_stylesheet,
)


def test_two_palettes_each_light_and_dark():
    assert THEME_ORDER == ("auto", "light", "dark")
    assert set(PALETTES) == {"graphite", "warm"}
    for pair in PALETTES.values():
        assert pair["light"]["mode"] == "light"
        assert pair["dark"]["mode"] == "dark"


def test_unknown_and_legacy_choices():
    from core.themes import LEGACY_APPEARANCE, migrate_appearance

    assert resolve_theme(None) == DEFAULT_THEME == "auto"
    assert resolve_theme("neon") == "auto"
    assert resolve_theme("  DARK ") == "dark"
    assert resolve_palette(None) == DEFAULT_PALETTE == "graphite"
    assert resolve_palette("WARM") == "warm"
    assert resolve_palette("neon") == "graphite"
    assert migrate_appearance("night") == ("dark", "graphite")
    assert migrate_appearance(" pine ") == ("dark", "graphite")
    assert migrate_appearance("paper", "graphite") == ("light", "warm")
    assert migrate_appearance("ember") == ("dark", "warm")
    assert migrate_appearance("kiln") == ("dark", "warm")
    assert migrate_appearance("dark", "warm") == ("dark", "warm")
    assert migrate_appearance("light", None) == ("light", "graphite")
    assert set(LEGACY_APPEARANCE) == {"night", "pine", "paper", "ember", "kiln"}


def test_every_theme_meets_contrast():
    for pair in PALETTES.values():
        for theme in pair.values():
            assert contrast_issues(theme) == []


def test_stylesheet_per_choice():
    for name, pair in PALETTES.items():
        light = theme_stylesheet("light", name)
        dark = theme_stylesheet("dark", name)
        auto = theme_stylesheet("auto", name)
        assert pair["light"]["bg"] in light and pair["dark"]["bg"] not in light
        assert pair["dark"]["bg"] in dark and pair["light"]["bg"] not in dark
        assert "prefers-color-scheme: dark" in auto
        assert pair["light"]["bg"] in auto and pair["dark"]["bg"] in auto
        for css in (light, dark, auto):
            assert css.startswith("<style>\n@import")
            assert "prefers-reduced-motion" in css
            assert "--badge-free-bg" in css
            assert "--accent-soft" in css
            assert "st-key-nav_run" in css
            assert "st-key-nav_settings" in css
            assert '[data-testid="stSlider"]' in css
            assert '[data-testid="stExpander"]' in css
        assert f"--primary-color: {pair['light']['accent']}" in light
        assert f"--primary-color: {pair['dark']['accent']}" in dark


def test_screens():
    assert SCREENS[0] == ("run", "Запуск")
    assert resolve_screen("models") == "models"
    assert resolve_screen("nope") == "run"
    assert resolve_screen("ssh") == "settings"


def test_saved_theme_roundtrip(tmp_path, monkeypatch):
    from core.themes import migrate_appearance
    from core.ui_helpers import load_user_settings, save_user_settings

    path = tmp_path / "user_settings.json"
    monkeypatch.setattr("core.ui_helpers.SETTINGS_PATH", path)
    save_user_settings({"theme": "dark", "palette": "warm"})
    loaded = load_user_settings()
    assert resolve_theme(loaded["theme"]) == "dark"
    assert resolve_palette(loaded["palette"]) == "warm"
    assert resolve_theme(loaded.get("missing")) == "auto"

    for legacy, expected in {
        "night": ("dark", "graphite"),
        "pine": ("dark", "graphite"),
        "paper": ("light", "warm"),
        "ember": ("dark", "warm"),
        "kiln": ("dark", "warm"),
    }.items():
        save_user_settings({"theme": legacy, "screen": "run"})
        raw = load_user_settings()
        theme, palette = migrate_appearance(raw.get("theme"), raw.get("palette"))
        save_user_settings({"theme": theme, "palette": palette, "screen": raw.get("screen")})
        again = load_user_settings()
        assert migrate_appearance(again["theme"], again["palette"]) == expected
        assert again["theme"] == expected[0]
        assert again["palette"] == expected[1]
        assert again["screen"] == "run"
