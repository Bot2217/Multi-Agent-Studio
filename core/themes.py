"""Two standard themes, light and dark, plus "auto" that follows the system setting."""

from __future__ import annotations

import os

from core.icons import icon_css

DEFAULT_THEME = "auto"
THEME_ORDER = ("auto", "light", "dark")
THEME_LABELS = {"auto": "Авто", "light": "Светлая", "dark": "Тёмная"}
# Older saved theme ids carried both the mode and the palette.
# night/pine were the charcoal theme, paper the light paper theme,
# ember/kiln the dark warm theme.
LEGACY_APPEARANCE = {
    "night": ("dark", "graphite"),
    "pine": ("dark", "graphite"),
    "paper": ("light", "warm"),
    "ember": ("dark", "warm"),
    "kiln": ("dark", "warm"),
}

# Left-hand menu. First item is the home flow.
SCREENS = (
    ("run", "Запуск"),
    ("agents", "Агенты"),
    ("models", "Модели"),
    ("files", "Файлы"),
    ("settings", "Настройки"),
)
LEGACY_SCREENS = {"ssh": "settings", "help": "settings"}

DEFAULT_PALETTE = "graphite"
PALETTE_ORDER = ("graphite", "warm")
PALETTE_LABELS = {"graphite": "Графит", "warm": "Тёплая"}

_COOL_LIGHT_BADGES = {
    "free": {"bg": "#dcefe3", "fg": "#17603a"},
    "freemium": {"bg": "#e1eafb", "fg": "#1f4aa8"},
    "paid": {"bg": "#eceef1", "fg": "#3d4550"},
    "local": {"bg": "#ece6f8", "fg": "#573897"},
    "unknown": {"bg": "#f3eeda", "fg": "#6a5210"},
    "deprecated": {"bg": "#fbe4e0", "fg": "#8f2a1c"},
}
_COOL_DARK_BADGES = {
    "free": {"bg": "#173626", "fg": "#9be0b8"},
    "freemium": {"bg": "#1c2c4f", "fg": "#a9c4fb"},
    "paid": {"bg": "#2a2e34", "fg": "#cfd5dd"},
    "local": {"bg": "#2c2444", "fg": "#cbb6f5"},
    "unknown": {"bg": "#3a3118", "fg": "#ecd58a"},
    "deprecated": {"bg": "#45211c", "fg": "#f5b5aa"},
}
_WARM_LIGHT_BADGES = {
    "free": {"bg": "#dce8df", "fg": "#1a4a34"},
    "freemium": {"bg": "#f3d7cf", "fg": "#7a2a1c"},
    "paid": {"bg": "#f6d9d2", "fg": "#7a2418"},
    "local": {"bg": "#e7dfd2", "fg": "#4a3418"},
    "unknown": {"bg": "#e6e1d8", "fg": "#3f382f"},
    "deprecated": {"bg": "#f6e3c4", "fg": "#6a3d08"},
}
_WARM_DARK_BADGES = {
    "free": {"bg": "#1e3d30", "fg": "#b7e2c8"},
    "freemium": {"bg": "#3d241c", "fg": "#f0c2b2"},
    "paid": {"bg": "#4a241c", "fg": "#f3c2b4"},
    "local": {"bg": "#3a2e1c", "fg": "#edd9b0"},
    "unknown": {"bg": "#332c24", "fg": "#e4d8c8"},
    "deprecated": {"bg": "#4a3414", "fg": "#f3d7a4"},
}

# graphite: charcoal with a lime accent. warm: the original paper and night colors.
PALETTES: dict[str, dict[str, dict]] = {
    "graphite": {
        "light": {
            "id": "graphite-light",
            "mode": "light",
            "bg": "#f1f2f5",
            "surface": "#fbfbfc",
            "raised": "#eceef2",
            "sidebar": "#e9ebef",
            "ink": "#14161b",
            "muted": "#596070",
            "line": "#d9dce3",
            "accent": "#2c6a12",
            "on_accent": "#f6fbf1",
            "accent_soft": "rgba(44, 106, 18, 0.10)",
            "link": "#2c6a12",
            "note": "#e8f1e2",
            "danger": "#a3261c",
            "ok": "#1c6a44",
            "badges": _COOL_LIGHT_BADGES,
        },
        "dark": {
            "id": "graphite-dark",
            "mode": "dark",
            "bg": "#0d0e12",
            "surface": "#15171d",
            "raised": "#1c1f27",
            "sidebar": "#0b0c0f",
            "ink": "#eef0f4",
            "muted": "#9aa3b2",
            "line": "#272b35",
            "accent": "#c2f24e",
            "on_accent": "#12160a",
            "accent_soft": "rgba(194, 242, 78, 0.12)",
            "link": "#c2f24e",
            "note": "#1b2112",
            "danger": "#ff9c94",
            "ok": "#6fe0a8",
            "badges": _COOL_DARK_BADGES,
        },
    },
    "warm": {
        "light": {
            "id": "warm-light",
            "mode": "light",
            "bg": "#f4efe4",
            "surface": "#fffaf3",
            "raised": "#ebe3d4",
            "sidebar": "#ebe3d4",
            "ink": "#241c14",
            "muted": "#5c5146",
            "line": "#d9cfc0",
            "accent": "#b8432f",
            "on_accent": "#fffaf3",
            "accent_soft": "rgba(184, 67, 47, 0.10)",
            "link": "#1e4d3c",
            "note": "#fff6e8",
            "danger": "#8c2f24",
            "ok": "#1a4a34",
            "badges": _WARM_LIGHT_BADGES,
        },
        "dark": {
            "id": "warm-dark",
            "mode": "dark",
            "bg": "#17130f",
            "surface": "#241e18",
            "raised": "#2c2418",
            "sidebar": "#100e0b",
            "ink": "#f6f1e7",
            "muted": "#d2c4b0",
            "line": "#3a322a",
            "accent": "#e0a15a",
            "on_accent": "#1c140c",
            "accent_soft": "rgba(224, 161, 90, 0.14)",
            "link": "#f0c48a",
            "note": "#2c2418",
            "danger": "#f3c2b4",
            "ok": "#b7e2c8",
            "badges": _WARM_DARK_BADGES,
        },
    },
}
# Kept for older imports: the warm pair.
THEMES = PALETTES["warm"]


def resolve_palette(name: str | None) -> str:
    key = str(name or "").strip().lower()
    return key if key in PALETTES else DEFAULT_PALETTE


def resolve_theme(name: str | None) -> str:
    key = str(name or "").strip().lower()
    if key in LEGACY_APPEARANCE:
        return LEGACY_APPEARANCE[key][0]
    if key in THEME_ORDER:
        return key
    return DEFAULT_THEME


def migrate_appearance(theme: str | None, palette: str | None = None) -> tuple[str, str]:
    """Mode and palette for a saved pair, including pre-palette theme ids."""
    key = str(theme or "").strip().lower()
    if key in LEGACY_APPEARANCE:
        return LEGACY_APPEARANCE[key]
    return resolve_theme(theme), resolve_palette(palette)


def resolve_screen(name: str | None) -> str:
    key = str(name or "").strip().lower()
    key = LEGACY_SCREENS.get(key, key)
    known = {screen_id for screen_id, _label in SCREENS}
    if key in known:
        return key
    return SCREENS[0][0]


def _channel(value: int) -> float:
    channel = value / 255
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    red = int(raw[0:2], 16)
    green = int(raw[2:4], 16)
    blue = int(raw[4:6], 16)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(foreground: str, background: str) -> float:
    lighter = max(luminance(foreground), luminance(background))
    darker = min(luminance(foreground), luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def contrast_issues(theme: dict) -> list[str]:
    """Pairs that miss the contrast floor. Empty list means the theme is safe to ship."""
    checks = [
        ("ink on bg", theme["ink"], theme["bg"], 7.0),
        ("ink on surface", theme["ink"], theme["surface"], 7.0),
        ("ink on sidebar", theme["ink"], theme["sidebar"], 7.0),
        ("ink on note", theme["ink"], theme["note"], 7.0),
        ("muted on bg", theme["muted"], theme["bg"], 4.5),
        ("muted on surface", theme["muted"], theme["surface"], 4.5),
        ("muted on sidebar", theme["muted"], theme["sidebar"], 4.5),
        ("button label on accent", theme["on_accent"], theme["accent"], 4.5),
        ("accent on surface", theme["accent"], theme["surface"], 4.5),
        ("link on bg", theme["link"], theme["bg"], 4.5),
        ("danger on surface", theme["danger"], theme["surface"], 4.5),
        ("ok on surface", theme["ok"], theme["surface"], 4.5),
    ]
    for name, colors in theme["badges"].items():
        checks.append((f"badge {name}", colors["fg"], colors["bg"], 4.5))
    issues = []
    for label, foreground, background, floor in checks:
        ratio = contrast_ratio(foreground, background)
        if ratio < floor:
            issues.append(f"{theme['id']}: {label} is {ratio:.2f}, need {floor}")
    return issues


def _variables(theme: dict) -> str:
    lines = [f"color-scheme: {theme['mode']};"]
    for key in (
        "bg",
        "surface",
        "raised",
        "sidebar",
        "ink",
        "muted",
        "line",
        "accent",
        "on_accent",
        "accent_soft",
        "link",
        "note",
        "danger",
        "ok",
    ):
        lines.append(f"--{key.replace('_', '-')}: {theme[key]};")
    lines.append(f"--primary-color: {theme['accent']};")
    for name, colors in theme["badges"].items():
        lines.append(f"--badge-{name}-bg: {colors['bg']};")
        lines.append(f"--badge-{name}-fg: {colors['fg']};")
    return "\n  ".join(lines)


FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500&display=swap');"
)


def _desktop_css() -> str:
    if os.environ.get("MAS_DESKTOP") != "1":
        return ""
    return """
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
#MainMenu, footer, [data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding-top: 1.1rem; }
"""


def theme_stylesheet(theme_id: str | None, palette: str | None = None) -> str:
    choice = resolve_theme(theme_id)
    pair = PALETTES[resolve_palette(palette)]
    if choice == "auto":
        colors = (
            f":root {{\n  {_variables(pair['light'])}\n}}\n"
            "@media (prefers-color-scheme: dark) {\n"
            f":root {{\n  {_variables(pair['dark'])}\n}}\n}}"
        )
    else:
        colors = f":root {{\n  {_variables(pair[choice])}\n}}"
    badge_css = "\n".join(
        f".badge-{name} {{ background: var(--badge-{name}-bg); color: var(--badge-{name}-fg); }}"
        for name in pair["light"]["badges"]
    )
    return (
        f"<style>\n{FONT_IMPORT}\n/* theme:{choice} palette:{resolve_palette(palette)} */\n"
        f"{colors}\n{_BASE_CSS}\n{icon_css()}\n{badge_css}\n{_desktop_css()}\n</style>"
    )


_BASE_CSS = """
:root {
  --font-body: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px;
  --radius-s: 8px; --radius-m: 12px; --radius-pill: 999px;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  --type-xs: 0.75rem; --type-sm: 0.875rem; --type-md: 1rem; --type-lg: 1.25rem; --type-xl: 1.75rem;
}
html, body, .stApp, :root body p, :root body li, :root body label, :root body input, :root body textarea, :root body button,
[data-testid="stMarkdownContainer"] {
  font-family: var(--font-body);
}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: var(--bg);
  color: var(--ink);
}
.block-container { padding-top: 2.5rem; padding-bottom: 4rem; max-width: 880px; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
  background: var(--sidebar);
}
[data-testid="stSidebar"] { border-right: 1px solid var(--line); }
:root body h1, :root body h2, :root body h3, :root body h4 {
  font-family: var(--font-body); color: var(--ink); letter-spacing: -0.01em; font-weight: 650;
}
:root body h1 { font-size: var(--type-xl); line-height: 1.15; padding: 0 0 var(--space-2); }
:root body h2 { font-size: var(--type-lg); padding: var(--space-4) 0 var(--space-1); }
:root body h3 { font-size: 1.05rem; padding: var(--space-3) 0 var(--space-1); }
:root body p, :root body li, :root body label, [data-testid="stWidgetLabel"] p { color: var(--ink); }
:root body a { color: var(--link); }
:root body code, :root body pre, [data-testid="stCode"] * { font-family: var(--font-mono) !important; }
:root body :not(pre) > code {
  background: var(--note); color: var(--ink); border-radius: 4px; padding: 0.1em 0.35em;
}
[data-testid="stCode"], [data-testid="stCode"] pre {
  background: var(--surface) !important; color: var(--ink) !important;
  border-radius: var(--radius-s);
}
[data-testid="stCode"] { border: 1px solid var(--line); }
[data-testid="stCode"] pre code, [data-testid="stCode"] pre span {
  color: var(--ink) !important; background: transparent !important;
}
[data-testid="stCode"] pre ~ div, [data-testid="stCode"] code ~ div > div {
  background: var(--surface) !important; color: var(--muted);
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
:root body p.lead { color: var(--muted); margin: 0 0 var(--space-3); }

/* Buttons */
:root body button[kind], :root body [data-testid="stDownloadButton"] button {
  border-radius: var(--radius-s); font-weight: 550; min-height: 40px;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}
:root body button[kind="primary"], :root body button[kind="primaryFormSubmit"] {
  background: var(--accent); color: var(--on-accent); border: 1px solid var(--accent);
}
:root body button[kind="primary"] p, :root body button[kind="primaryFormSubmit"] p { color: var(--on-accent); }
:root body button[kind="primary"]:hover, :root body button[kind="primaryFormSubmit"]:hover {
  filter: brightness(1.08); color: var(--on-accent); border-color: var(--accent);
}
:root body button[kind="secondary"], :root body button[kind="secondaryFormSubmit"],
:root body [data-testid="stDownloadButton"] button, :root body [data-testid="stPopover"] button {
  background: var(--surface); color: var(--ink); border: 1px solid var(--line);
}
:root body button[kind="secondary"]:hover, :root body button[kind="secondaryFormSubmit"]:hover,
:root body [data-testid="stDownloadButton"] button:hover, :root body [data-testid="stPopover"] button:hover {
  border-color: var(--accent); color: var(--accent);
}
:root body button[kind="secondary"]:hover p { color: var(--accent); }
:root body button[kind="tertiary"] { background: transparent; color: var(--muted); border: 1px solid transparent; }
:root body button[kind="tertiary"] p { color: var(--muted); }
:root body button[kind="tertiary"]:hover p { color: var(--ink); }
:root body button:disabled, :root body button:disabled p { cursor: not-allowed; }
:root body button[kind]:disabled {
  background: var(--line); border-color: var(--line); color: var(--muted); filter: none;
}
:root body button[kind]:disabled p { color: var(--muted); }
:root body textarea:disabled, :root body input:disabled {
  color: var(--muted) !important; -webkit-text-fill-color: var(--muted); opacity: 1;
}
:root body button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
:root body [class*="st-key-launch_run"] button { min-height: 48px; font-size: 1.02rem; }
:root body [class*="st-key-stop_run"] button { color: var(--danger); border-color: var(--line); }
:root body [class*="st-key-stop_run"] button p { color: var(--danger); }

/* Sidebar navigation */
.brand { font-weight: 700; font-size: 1.05rem; color: var(--ink); margin: 0 0 var(--space-4); }
.brand span { color: var(--accent); }
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button {
  display: inline-flex; align-items: center;
  justify-content: flex-start; text-align: left; min-height: 38px;
  background: transparent; border: 1px solid transparent; color: var(--ink);
}
:root body [class*="st-key-ex_"] button {
  height: auto; min-height: 40px; white-space: normal; text-align: left;
  justify-content: flex-start;
}
:root body [class*="st-key-ex_"] button p {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
  line-height: 1.35;
}
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button > div,
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button > span {
  justify-content: flex-start; width: 100%; gap: var(--space-2);
}
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button p { color: inherit; font-weight: 500; }
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button:hover { background: var(--surface); color: var(--ink); }
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] {
  background: var(--surface); border-color: var(--line); color: var(--accent); box-shadow: var(--shadow);
  filter: none;
}
:root body [data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] p { font-weight: 650; color: var(--accent); }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem; }
.side-label {
  font-size: var(--type-xs); color: var(--muted); text-transform: uppercase;
  letter-spacing: 0.06em; margin: var(--space-5) 0 var(--space-2); padding-left: 2px;
}

/* Inputs */
:root body [data-baseweb="input"], :root body [data-baseweb="base-input"], :root body [data-baseweb="textarea"],
:root body [data-baseweb="select"] > div, :root body [data-testid="stNumberInputContainer"] {
  background-color: var(--surface) !important; color: var(--ink) !important;
  border-color: var(--line) !important; border-radius: var(--radius-s) !important;
}
:root body [data-baseweb="input"]:focus-within, :root body [data-baseweb="textarea"]:focus-within,
:root body [data-baseweb="select"] > div:focus-within { border-color: var(--accent) !important; }
:root body input, :root body textarea, :root body [data-baseweb="select"] div, :root body [data-baseweb="select"] span {
  color: var(--ink) !important; caret-color: var(--ink); -webkit-text-fill-color: var(--ink);
}
:root body [data-baseweb="input"] input, :root body [data-baseweb="base-input"] input,
:root body [data-baseweb="textarea"] textarea, :root body [data-baseweb="base-input"] {
  background-color: var(--surface) !important;
}
:root body input::placeholder, :root body textarea::placeholder {
  color: var(--muted) !important; -webkit-text-fill-color: var(--muted); opacity: 0.8;
}
:root body [data-baseweb="input"] button, :root body [data-testid="stNumberInputContainer"] button {
  background: transparent !important; color: var(--muted) !important; border: 0 !important; min-height: 0;
}
:root body [data-baseweb="select"] svg { fill: var(--muted); color: var(--muted); }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul[role="listbox"],
[data-baseweb="popover"] > div, [data-testid="stPopoverBody"], [data-baseweb="tooltip"] > div,
[data-testid="stTooltipContent"] {
  background: var(--surface) !important; color: var(--ink) !important;
}
[data-baseweb="popover"] > div, [data-testid="stPopoverBody"] {
  border: 1px solid var(--line); border-radius: var(--radius-m) !important;
}
[data-baseweb="popover"] li[role="option"], [data-baseweb="popover"] li[role="option"] * {
  color: var(--ink) !important; background: transparent;
}
[data-baseweb="popover"] li[role="option"]:hover, [data-baseweb="popover"] li[aria-selected="true"] {
  background: var(--note) !important;
}
[data-testid="stPopoverBody"] *, [data-testid="stTooltipContent"] * { color: var(--ink); }
:root, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
  --primary-color: var(--accent) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div,
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBar"] {
  background: var(--accent) !important;
}
[data-testid="stSlider"] [role="slider"] {
  background: var(--accent) !important; border: 2px solid var(--surface) !important;
}
[data-testid="stSlider"] [data-testid="stSliderThumbValue"] { color: var(--accent) !important; }
[data-testid="stSlider"] [data-testid="stSliderTickBar"] * { color: var(--muted) !important; }
[data-testid="stToggle"] [data-baseweb="checkbox"] div,
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child {
  border-color: var(--line) !important;
}
[data-testid="stToggle"] [aria-checked="true"],
[data-testid="stToggle"] [aria-checked="true"] div,
[data-testid="stToggle"] [data-baseweb="checkbox"] [aria-checked="true"] {
  background: var(--accent) !important; border-color: var(--accent) !important;
}
:root body label[data-baseweb="checkbox"] > div:first-child { border-color: var(--line); }

/* Current Streamlit widgets (no baseweb attributes) */
:root body [data-testid="stTextAreaRootElement"], :root body [data-testid="stTextInputRootElement"],
:root body [data-testid="stNumberInputContainer"], :root body [data-testid="stSelectbox"] [role="group"],
:root body [data-testid="stMultiSelect"] [role="group"] {
  background: var(--surface) !important; border-color: var(--line) !important; color: var(--ink);
  border-radius: var(--radius-s);
}
:root body [data-testid="stTextAreaRootElement"]:focus-within,
:root body [data-testid="stTextInputRootElement"]:focus-within,
:root body [data-testid="stSelectbox"] [role="group"]:focus-within { border-color: var(--accent) !important; }
:root body [data-testid="stSelectbox"] [role="group"] button { background: transparent; border: 0; min-height: 0; }
:root body [data-testid="stSelectbox"] svg, :root body [data-testid="stTextInputRootElement"] svg { color: var(--muted); }
[role="listbox"] {
  background: var(--surface) !important; color: var(--ink) !important; border-color: var(--line) !important;
}
[role="option"], [role="option"] * { color: var(--ink) !important; }
[role="option"]:hover, [role="option"][aria-selected="true"], [role="option"][data-highlighted],
[role="option"][data-focused] { background: var(--note) !important; }
[data-testid="stWidgetLabel"] svg, [data-testid="stTooltipIcon"] svg { color: var(--muted); }

/* Pills and segmented control */
:root body [data-testid="stButtonGroup"] button {
  background: var(--surface); color: var(--ink); border: 1px solid var(--line); min-height: 34px;
}
:root body [data-testid="stButtonGroup"] button p { color: inherit; }
:root body [data-testid="stButtonGroup"] button:hover { border-color: var(--accent); }
:root body [data-testid="stButtonGroup"] button[aria-checked="true"],
:root body [data-testid="stButtonGroup"] button[aria-pressed="true"] {
  background: var(--note); color: var(--accent); border-color: var(--accent);
}
:root body [data-testid="stButtonGroup"] button[aria-checked="true"] p { font-weight: 650; }
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button { padding: 0 0.6rem; min-height: 32px; }
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button p { font-size: var(--type-sm); }
[data-testid="stSidebar"] [data-testid="stButtonGroup"] [role="radiogroup"] { flex-wrap: nowrap; }

/* Containers */
[data-testid="stExpander"] details,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:active {
  background: var(--surface) !important; color: var(--ink) !important;
  border-color: var(--line) !important;
}
[data-testid="stExpander"] details {
  border: 1px solid var(--line) !important; border-radius: var(--radius-m);
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: var(--ink) !important; }
[data-testid="stExpander"] summary:hover { background: var(--raised) !important; }
[data-testid="stExpander"] summary:hover, [data-testid="stExpander"] summary:hover * { color: var(--accent) !important; }
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stForm"],
:root body [class*="st-key-card_"], :root body .st-key-result_panel, :root body .st-key-live_panel {
  border-color: var(--line) !important;
}
:root body [class*="st-key-card_"], :root body .st-key-result_panel, :root body .st-key-live_panel {
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-m);
  padding: var(--space-4);
}
.st-key-result_panel h1, .st-key-result_panel h2 { font-size: 1.1rem; padding: var(--space-2) 0 0; }
[data-testid="stAlert"] > div, [data-testid="stAlertContainer"] {
  background: var(--note) !important; color: var(--ink) !important;
  border: 1px solid var(--line) !important; border-radius: var(--radius-m) !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] svg { color: var(--ink) !important; }
hr { border-color: var(--line) !important; }

/* Own pieces */
.status { display: flex; gap: var(--space-2); align-items: center; font-weight: 600; margin: 0; }
.status small { color: var(--muted); font-weight: 400; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--muted); flex: none; }
.dot.ok { background: var(--ok); }
.dot.bad { background: var(--danger); }
.dot.live { background: var(--accent); animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.35; } }
.badge {
  display: inline-block; padding: 0.1rem 0.5rem; border-radius: var(--radius-pill);
  font-size: var(--type-xs); font-weight: 600; margin-right: 0.35rem; vertical-align: middle;
  white-space: nowrap;
}
.chain { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0 0 var(--space-2); }
.chip {
  background: var(--surface); color: var(--ink); border: 1px solid var(--line);
  border-radius: var(--radius-pill); padding: 0.25rem 0.7rem; font-size: var(--type-sm);
}
.chip small { color: var(--muted); }
.chip.nokey { border-style: dashed; }
.arrow { color: var(--muted); }
.empty {
  border: 1px dashed var(--line); border-radius: var(--radius-m); padding: var(--space-5);
  color: var(--muted); text-align: center;
}
.sheet-wrap {
  max-height: 460px; overflow: auto; border: 1px solid var(--line);
  border-radius: var(--radius-m); background: var(--surface);
}
table.sheet { width: 100%; border-collapse: collapse; font-size: var(--type-sm); }
table.sheet th {
  position: sticky; top: 0; text-align: left; font-size: var(--type-xs); font-weight: 600;
  color: var(--muted); background: var(--sidebar); padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--line); white-space: nowrap;
}
table.sheet td {
  padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--line);
  color: var(--ink); vertical-align: middle;
}
table.sheet tr:last-child td { border-bottom: 0; }
table.sheet td.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
table.sheet td small {
  color: var(--muted); font-family: var(--font-mono); font-size: 0.72rem; white-space: nowrap;
}
table.sheet tbody tr:hover td { background: var(--note); }
@media (prefers-reduced-motion: reduce) {
  .dot.live { animation: none; }
  :root body button[kind] { transition: none; }
}
/* Bento layer: cards, eyebrows, tags, tactile states */
:root { --radius-l: 20px; --type-xl: clamp(1.6rem, 1.2vw + 1.1rem, 2.1rem); }
:root body .block-container { max-width: 1120px; padding-top: 2rem; }
:root body h1 { font-size: var(--type-xl); font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; padding: 0; }
:root body [class*="st-key-card_"], :root body .st-key-result_panel, :root body .st-key-live_panel {
  border-radius: var(--radius-l); padding: 20px; transition: border-color 160ms ease;
}
:root body [class*="st-key-card_"]:hover { border-color: color-mix(in srgb, var(--accent) 35%, var(--line)); }
:root body .st-key-live_panel { border-color: var(--accent); }
:root body button[kind] {
  transition: transform 120ms ease, background 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
  border-radius: 14px;
}
:root body button[kind]:active:not(:disabled) { transform: scale(0.97); }
:root body button[kind="primary"]:hover:not(:disabled) { box-shadow: 0 0 0 4px var(--accent-soft); filter: none; }
:root body [data-testid="stTextAreaRootElement"], :root body [data-testid="stTextInputRootElement"],
:root body [data-testid="stSelectbox"] [role="group"] { border-radius: 14px; }
:root body [data-testid="stTextAreaRootElement"]:focus-within,
:root body [data-testid="stTextInputRootElement"]:focus-within,
:root body [data-testid="stSelectbox"] [role="group"]:focus-within { box-shadow: 0 0 0 3px var(--accent-soft); }
:root body .st-key-card_task [data-testid="stTextAreaRootElement"] { background: var(--bg) !important; }
:root body .st-key-card_task textarea { font-size: 1rem; line-height: 1.5; background: transparent !important; }
:root body p.eyebrow, .eyebrow {
  font-size: var(--type-xs); font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted); margin: 0;
}
.page-head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 0 0 8px; }
.page-head > div { display: flex; flex-direction: column; gap: 4px; }
.page-head .tags { flex-direction: row; flex-wrap: wrap; gap: 8px; }
:root body .page-head p.sub { color: var(--muted); font-size: var(--type-sm); margin: 4px 0 0; }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 0 0 4px; }
.tag {
  display: inline-flex; align-items: center; height: 22px; padding: 0 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600; background: var(--accent-soft); color: var(--accent); white-space: nowrap;
}
.tag.quiet { background: var(--raised); color: var(--muted); }
ol.steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
:root body ol.steps li {
  display: flex; gap: 12px; align-items: center; padding: 12px; margin: 0;
  border-radius: 14px; border: 1px solid var(--line); background: var(--raised);
}
:root body ol.steps li.nokey { border-style: dashed; background: transparent; }
ol.steps .num {
  width: 28px; height: 28px; border-radius: 9px; flex: none; display: grid; place-items: center;
  background: var(--accent-soft); color: var(--accent); font-weight: 700; font-size: var(--type-sm);
}
ol.steps .who { display: flex; flex-direction: column; min-width: 0; line-height: 1.3; }
ol.steps .who b { font-weight: 600; color: var(--ink); }
ol.steps .who small { font-family: var(--font-mono); font-size: var(--type-xs); color: var(--muted); }
ol.steps .tag { margin-left: auto; }
.rows { display: flex; flex-direction: column; gap: 8px; }
.rows .row { display: flex; align-items: center; gap: 10px; min-height: 28px; color: var(--ink); min-width: 0; }
.rows .row svg { color: var(--accent); flex: none; }
.rows .row .name { font-family: var(--font-mono); font-size: var(--type-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rows .row .label { font-weight: 500; }
.rows .row .state { margin-left: auto; font-size: var(--type-sm); color: var(--muted); white-space: nowrap; }
.rows .row .state.ok { color: var(--ok); }
.brand { display: flex; align-items: center; gap: 12px; }
.brand svg { color: var(--accent); flex: none; }
.brand b { display: block; font-weight: 700; font-size: 0.95rem; letter-spacing: -0.01em; line-height: 1.15; color: var(--ink); }
.brand small { display: block; font-size: var(--type-xs); color: var(--muted); font-weight: 400; }
.dot.live { box-shadow: 0 0 0 4px var(--accent-soft); }
:root body [class*="st-key-ex_"] button, :root body [class*="st-key-hist_"] button {
  min-height: 34px; border-radius: 999px; background: var(--raised); justify-content: flex-start;
}
:root body [class*="st-key-ex_"] button p, :root body [class*="st-key-hist_"] button p {
  font-size: var(--type-sm); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
:root body [class*="st-key-hist_"] button { border-radius: 12px; width: 100%; }
@media (prefers-reduced-motion: reduce) {
  :root body button[kind], :root body [class*="st-key-card_"] { transition: none; }
  :root body button[kind]:active:not(:disabled) { transform: none; }
}
"""
