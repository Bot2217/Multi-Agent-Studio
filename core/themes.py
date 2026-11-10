"""Design tokens and themes. Dark charcoal is the default."""

from __future__ import annotations

from core.icons import icon_css

DEFAULT_THEME = "night"
THEME_ORDER = ("night", "paper", "ember")
# Retired ids still resolve so saved user_settings.json keeps working.
_ALIASES = {"kiln": "ember", "pine": "night"}

SCREENS = (
    ("run", "Запуск"),
    ("agents", "Агенты"),
    ("models", "Модели"),
    ("files", "Файлы"),
    ("ssh", "SSH"),
    ("help", "Справка"),
)

_LIGHT_BADGES = {
    "free": {"bg": "#d7ebe3", "fg": "#0e4a36"},
    "freemium": {"bg": "#efe0c8", "fg": "#6a3d08"},
    "paid": {"bg": "#f3d5d2", "fg": "#7a241c"},
    "local": {"bg": "#e4e0f2", "fg": "#3a2f6b"},
    "unknown": {"bg": "#e6e4de", "fg": "#3c4038"},
    "deprecated": {"bg": "#f6e3c4", "fg": "#6a3d08"},
}
_DARK_BADGES = {
    "free": {"bg": "#16382c", "fg": "#b7f0d4"},
    "freemium": {"bg": "#3a2c14", "fg": "#ffd7a1"},
    "paid": {"bg": "#3d221e", "fg": "#ffc7bc"},
    "local": {"bg": "#2a2440", "fg": "#ddd4ff"},
    "unknown": {"bg": "#2a2d33", "fg": "#d5d8e0"},
    "deprecated": {"bg": "#3d3018", "fg": "#ffe0a8"},
}

THEMES: dict[str, dict] = {
    "night": {
        "id": "night",
        "label": "Ночь",
        "kicker": "студия",
        "blurb": "Уголь и лайм. Тема по умолчанию.",
        "mode": "dark",
        "bg": "#0d0e12",
        "surface": "#171a21",
        "sidebar": "#12141b",
        "ink": "#e7e9ee",
        "muted": "#b7becc",
        "line": "#2c313c",
        "accent": "#d6ff3e",
        "on_accent": "#14160a",
        "link": "#e7ff8a",
        "note": "#fff6e8",
        "badges": _DARK_BADGES,
    },
    "paper": {
        "id": "paper",
        "label": "Бумага",
        "kicker": "студия",
        "blurb": "Тёплый светлый фон, без чистого белого.",
        "mode": "light",
        "bg": "#efece6",
        "surface": "#f7f5f0",
        "sidebar": "#e6e1d6",
        "ink": "#1c1e24",
        "muted": "#5c6370",
        "line": "#d4cfc4",
        "accent": "#0f6b56",
        "on_accent": "#f6f3ec",
        "link": "#0c5a48",
        "note": "#fff6e8",
        "badges": _LIGHT_BADGES,
    },
    "ember": {
        "id": "ember",
        "label": "Жар",
        "kicker": "студия",
        "blurb": "Тёплый тёмный фон и медный акцент.",
        "mode": "dark",
        "bg": "#14110e",
        "surface": "#211c17",
        "sidebar": "#1a1612",
        "ink": "#f4ece4",
        "muted": "#d0bfae",
        "line": "#3c342c",
        "accent": "#ff9a4a",
        "on_accent": "#1a1008",
        "link": "#ffc48a",
        "note": "#fff6e8",
        "badges": _DARK_BADGES,
    },
}


def resolve_theme(name: str | None) -> str:
    key = str(name or "").strip().lower()
    key = _ALIASES.get(key, key)
    if key in THEMES:
        return key
    return DEFAULT_THEME


def resolve_screen(name: str | None) -> str:
    key = str(name or "").strip().lower()
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
    checks = [
        ("ink on bg", theme["ink"], theme["bg"], 7.0),
        ("ink on surface", theme["ink"], theme["surface"], 7.0),
        ("muted on bg", theme["muted"], theme["bg"], 4.5),
        ("ink on sidebar", theme["ink"], theme["sidebar"], 7.0),
        ("button label on accent", theme["on_accent"], theme["accent"], 4.5),
        ("link on bg", theme["link"], theme["bg"], 4.5),
    ]
    for name, colors in theme["badges"].items():
        checks.append((f"badge {name}", colors["fg"], colors["bg"], 4.5))
    issues = []
    for label, foreground, background, floor in checks:
        ratio = contrast_ratio(foreground, background)
        if ratio < floor:
            issues.append(f"{theme['id']}: {label} is {ratio:.2f}, need {floor}")
    return issues


def theme_stylesheet(theme_id: str | None) -> str:
    theme = THEMES[resolve_theme(theme_id)]
    badge_css = "\n".join(
        f".badge-{name} {{ background: {colors['bg']}; color: {colors['fg']}; }}"
        for name, colors in theme["badges"].items()
    )
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@420;520;640;720&family=JetBrains+Mono:wght@420;560&display=swap');
/* theme:{theme["id"]} fonts:Inter,JetBrains Mono */
:root {{
  --bg: {theme["bg"]};
  --surface: {theme["surface"]};
  --sidebar: {theme["sidebar"]};
  --ink: {theme["ink"]};
  --muted: {theme["muted"]};
  --line: {theme["line"]};
  --accent: {theme["accent"]};
  --on-accent: {theme["on_accent"]};
  --link: {theme["link"]};
  --note: {theme["note"]};
  --danger: #c4473a;
  --on-danger: #fff6f2;
  --font-ui: Inter, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --radius-s: 12px;
  --radius-m: 16px;
  --radius-l: 20px;
  --shadow: 0 1px 0 color-mix(in srgb, var(--ink) 8%, transparent);
  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
  --dur: 160ms;
  --type-xs: clamp(0.72rem, 0.7rem + 0.08vw, 0.8rem);
  --type-sm: clamp(0.84rem, 0.8rem + 0.15vw, 0.94rem);
  --type-md: clamp(0.96rem, 0.9rem + 0.2vw, 1.05rem);
  --type-lg: clamp(1.2rem, 1.05rem + 0.55vw, 1.5rem);
  --type-xl: clamp(1.7rem, 1.35rem + 1.1vw, 2.35rem);
}}
html, body, .stApp, [data-testid="stMarkdown"], p, li, label, input, textarea, button {{
  font-family: var(--font-ui);
}}
html, body, .stApp {{
  background: var(--bg);
  color: var(--ink);
  font-size: var(--type-md);
}}
.block-container {{
  padding-top: var(--space-5);
  padding-bottom: var(--space-6);
  max-width: 1120px;
}}
header[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"] {{
  background: color-mix(in srgb, var(--sidebar) 88%, transparent);
  border-right: 1px solid var(--line);
  backdrop-filter: blur(18px);
}}
h1, h2, h3, [data-testid="stMetricValue"] {{
  font-family: var(--font-ui);
  letter-spacing: -0.03em;
  color: var(--ink);
  font-weight: 640;
}}
h1 {{ font-size: var(--type-xl); line-height: 1.05; margin: 0; }}
h2 {{ font-size: var(--type-lg); margin: 0; }}
p, li, label {{ color: var(--ink); }}
a {{ color: var(--link); }}
code, pre, kbd, samp, [data-testid="stCode"] {{
  font-family: var(--font-mono) !important;
}}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: var(--muted) !important; }}
[data-testid="stMetric"] {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-m);
  padding: var(--space-3) var(--space-4);
  transition: border-color var(--dur) var(--ease), transform var(--dur) var(--ease);
}}
[data-testid="stMetric"]:hover {{ border-color: var(--accent); }}
[data-testid="stMetricLabel"] {{ color: var(--muted) !important; font-size: var(--type-xs); }}
[data-testid="stMetricValue"] {{ color: var(--ink) !important; font-size: var(--type-lg); }}
div[data-testid="stButton"] > button {{
  border-radius: var(--radius-s);
  font-weight: 600;
  min-height: 44px;
  transition: transform var(--dur) var(--ease), background var(--dur) var(--ease), border-color var(--dur) var(--ease);
}}
div[data-testid="stButton"] > button:hover {{ transform: translateY(-1px); }}
div[data-testid="stButton"] > button:active {{ transform: scale(0.98); }}
div[data-testid="stButton"] > button[kind="primary"] {{
  background: var(--accent);
  color: var(--on-accent);
  border: 1px solid var(--accent);
}}
div[data-testid="stButton"] > button[kind="secondary"] {{
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--line);
}}
div[data-testid="stButton"] > button[kind="tertiary"] {{
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  min-height: 36px;
}}
[class*="st-key-danger"] button {{
  background: var(--danger) !important;
  color: var(--on-danger) !important;
  border-color: var(--danger) !important;
}}
.st-key-tabbar {{
  display: flex;
  gap: var(--space-2);
  margin: var(--space-4) 0 var(--space-5);
}}
[class*="st-key-nav_"] button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-pill, 999px);
  min-height: 40px;
}}
[class*="st-key-nav_"] button[kind="primary"] {{
  box-shadow: 0 0 0 1px var(--accent);
}}
[class*="st-key-launch_run"] button {{
  min-height: 52px;
  font-size: var(--type-md);
  border-radius: var(--radius-m);
}}
div[data-testid="stButton"] > button:focus-visible,
input:focus-visible, textarea:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
  background: var(--surface) !important;
  color: var(--ink) !important;
  border-color: var(--line) !important;
  border-radius: var(--radius-s) !important;
}}
[data-baseweb="input"] input, textarea {{
  color: var(--ink) !important;
  caret-color: var(--accent);
  font-family: var(--font-ui) !important;
}}
[data-testid="stSlider"] [role="slider"] {{
  background: var(--accent) !important;
}}
[data-testid="stExpander"] details {{
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: var(--radius-m);
}}
.st-key-card_folder, .st-key-card_status, .st-key-card_pipeline,
.st-key-card_task, .st-key-result_panel, .st-key-card_screen {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-l);
  padding: var(--space-4) var(--space-5) var(--space-3);
  margin-bottom: var(--space-4);
}}
[data-testid="stAlert"], [data-testid="stAlert"] * {{ color: #241c14 !important; }}
[data-testid="stAlert"] {{
  background: var(--note) !important;
  border: 1px solid #e4d3b4 !important;
  border-left: 4px solid var(--accent) !important;
  border-radius: var(--radius-m) !important;
}}
[data-testid="stSpinner"] {{ color: var(--accent); }}
.sheet-wrap {{
  max-height: 440px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-m);
  background: var(--surface);
}}
table.sheet {{ width: 100%; border-collapse: collapse; font-size: var(--type-sm); }}
table.sheet th {{
  position: sticky; top: 0; text-align: left;
  font-size: var(--type-xs); letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--muted); background: var(--sidebar);
  padding: var(--space-3); border-bottom: 1px solid var(--line);
}}
table.sheet td {{
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--line);
}}
table.sheet td code {{ font-family: var(--font-mono); }}
.mast {{ display: flex; gap: var(--space-4); align-items: center; margin-bottom: var(--space-4); }}
.mark {{
  width: 48px; height: 48px; border-radius: var(--radius-m);
  background: var(--accent); color: var(--on-accent);
  display: grid; place-items: center; font-weight: 720;
}}
.kicker {{
  font-size: var(--type-xs); letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--accent); font-weight: 640; margin: 0 0 4px;
}}
.studio-lead {{ color: var(--muted); margin: 4px 0 0; font-size: var(--type-sm); }}
.ico {{ vertical-align: -4px; margin-right: 6px; }}
.step {{ display: flex; gap: var(--space-3); align-items: flex-start; margin: 0 0 var(--space-3); }}
.step-no {{
  width: 28px; height: 28px; border-radius: 8px;
  background: var(--accent); color: var(--on-accent);
  display: grid; place-items: center; font-weight: 700; flex: none;
}}
.step h2 {{ font-size: var(--type-lg); }}
.step-hint {{ color: var(--muted); margin: 2px 0 0; font-size: var(--type-sm); }}
.progress {{ display: flex; gap: 6px; margin: 0 0 var(--space-4); }}
.progress .seg {{
  height: 4px; flex: 1; border-radius: 99px; background: var(--line);
}}
.progress .seg.on {{ background: var(--accent); }}
.chain {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
.chip {{
  background: color-mix(in srgb, var(--ink) 6%, var(--surface));
  border: 1px solid var(--line); border-radius: 999px;
  padding: 6px 10px; font-size: var(--type-sm);
  transition: border-color var(--dur) var(--ease);
}}
.chip:hover {{ border-color: var(--accent); }}
.chip.off {{ opacity: 0.55; }}
.badge {{
  display: inline-block; padding: 2px 8px; border-radius: 999px;
  font-size: var(--type-xs); font-weight: 650; margin-right: 6px;
}}
{badge_css}
{icon_css()}
.slip {{
  border: 1px dashed var(--line); border-radius: var(--radius-m);
  padding: var(--space-4); background: transparent;
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before {{ transition: none !important; animation: none !important; }}
  div[data-testid="stButton"] > button:hover,
  div[data-testid="stButton"] > button:active {{ transform: none; }}
}}
</style>
"""
