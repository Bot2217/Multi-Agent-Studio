"""Four studio themes. Colors are chosen so body text stays readable."""

from __future__ import annotations

DEFAULT_THEME = "paper"
THEME_ORDER = ("paper", "night", "kiln", "pine")

# Shared badge pairs. Light sheets for paper/kiln, dark chips for night/pine.
_LIGHT_BADGES = {
    "free": {"bg": "#dce8df", "fg": "#1a4a34"},
    "freemium": {"bg": "#f3d7cf", "fg": "#7a2a1c"},
    "paid": {"bg": "#f6d9d2", "fg": "#7a2418"},
    "local": {"bg": "#e7dfd2", "fg": "#4a3418"},
    "unknown": {"bg": "#e6e1d8", "fg": "#3f382f"},
    "deprecated": {"bg": "#f6e3c4", "fg": "#6a3d08"},
}
_DARK_BADGES = {
    "free": {"bg": "#1e3d30", "fg": "#b7e2c8"},
    "freemium": {"bg": "#3d241c", "fg": "#f0c2b2"},
    "paid": {"bg": "#4a241c", "fg": "#f3c2b4"},
    "local": {"bg": "#3a2e1c", "fg": "#edd9b0"},
    "unknown": {"bg": "#332c24", "fg": "#e4d8c8"},
    "deprecated": {"bg": "#4a3414", "fg": "#f3d7a4"},
}

THEMES: dict[str, dict] = {
    "paper": {
        "id": "paper",
        "label": "Бумага",
        "kicker": "типография",
        "blurb": "Тёплая бумага и красная краска печатного станка.",
        "mode": "light",
        "bg": "#f4efe4",
        "surface": "#fffaf3",
        "sidebar": "#ebe3d4",
        "ink": "#241c14",
        "muted": "#5c5146",
        "line": "#d9cfc0",
        "accent": "#b8432f",
        "on_accent": "#fffaf3",
        "link": "#1e4d3c",
        "note": "#fff6e8",
        "badges": _LIGHT_BADGES,
    },
    "night": {
        "id": "night",
        "label": "Ночь",
        "kicker": "ночная смена",
        "blurb": "Тёмная мастерская, латунная вывеска, без синего свечения.",
        "mode": "dark",
        "bg": "#17130f",
        "surface": "#241e18",
        "sidebar": "#100e0b",
        "ink": "#f6f1e7",
        "muted": "#d2c4b0",
        "line": "#3a322a",
        "accent": "#e0a15a",
        "on_accent": "#1c140c",
        "link": "#f0c48a",
        "note": "#2c2418",
        "badges": _DARK_BADGES,
    },
    "kiln": {
        "id": "kiln",
        "label": "Обжиг",
        "kicker": "глина и жар",
        "blurb": "Глиняный стол и горящая глазурь. Самая тёплая тема.",
        "mode": "light",
        "bg": "#f8e6d2",
        "surface": "#fff7ee",
        "sidebar": "#f0d2b4",
        "ink": "#2b160f",
        "muted": "#6d4a38",
        "line": "#e2c2a4",
        "accent": "#c2410c",
        "on_accent": "#fff7ee",
        "link": "#8d3014",
        "note": "#fff1e2",
        "badges": _LIGHT_BADGES,
    },
    "pine": {
        "id": "pine",
        "label": "Хвоя",
        "kicker": "лесная смена",
        "blurb": "Глубокая зелень и лимонный акцент, как хвоя на срезе.",
        "mode": "dark",
        "bg": "#10241c",
        "surface": "#1a3329",
        "sidebar": "#0b1a14",
        "ink": "#f4f7ec",
        "muted": "#c9d7c4",
        "line": "#2d4a3c",
        "accent": "#d6ef6a",
        "on_accent": "#14200c",
        "link": "#e4f08a",
        "note": "#1c382c",
        "badges": _DARK_BADGES,
    },
}


def resolve_theme(name: str | None) -> str:
    key = str(name or "").strip().lower()
    if key in THEMES:
        return key
    return DEFAULT_THEME


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
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,520;9..144,640&family=Outfit:wght@400;500;600&display=swap');
/* theme:{theme["id"]} */
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
}}
html, body, .stApp {{
  background: var(--bg);
  color: var(--ink);
  font-family: Outfit, "Avenir Next", "Segoe UI", sans-serif;
}}
.stApp::before {{
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  opacity: 0.045;
  background-image: radial-gradient(var(--ink) 0.6px, transparent 0.65px);
  background-size: 4px 4px;
  z-index: 0;
}}
.block-container {{
  padding-top: 1.4rem;
  padding-bottom: 3.5rem;
  max-width: 1120px;
  position: relative;
  z-index: 1;
}}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{
  background: var(--sidebar);
  border-right: 1px solid var(--line);
}}
[data-testid="stSidebar"] > div:first-child {{
  background: var(--sidebar);
}}
h1, h2, h3, [data-testid="stMetricValue"] {{
  font-family: Fraunces, "Iowan Old Style", Palatino, Georgia, serif;
  letter-spacing: -0.03em;
  color: var(--ink);
}}
h2 {{
  border-top: 1px solid var(--line);
  padding-top: 0.85rem;
  margin-top: 0.4rem;
}}
p, li, label, .stMarkdown {{ color: var(--ink); }}
a {{ color: var(--link); }}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: var(--muted) !important; }}
[data-testid="stMetric"] {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 0.45rem 0.85rem 0.6rem;
  transition: border-color 160ms ease, transform 160ms ease;
}}
[data-testid="stMetric"]:hover {{
  border-color: var(--accent);
  transform: translateY(-1px);
}}
[data-testid="stMetricLabel"] {{ color: var(--muted) !important; }}
[data-testid="stMetricValue"] {{ color: var(--ink) !important; }}
div[data-testid="stButton"] > button {{
  border-radius: 999px;
  font-family: Outfit, sans-serif;
  font-weight: 560;
  transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
}}
div[data-testid="stButton"] > button:hover {{ transform: translateY(-1px); }}
div[data-testid="stButton"] > button[kind="primary"] {{
  background: var(--accent);
  color: var(--on-accent);
  border: 1px solid var(--accent);
}}
div[data-testid="stButton"] > button[kind="secondary"] {{
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--line);
}}
div[data-testid="stButton"] > button:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
  background-color: var(--surface) !important;
  color: var(--ink) !important;
  border-color: var(--line) !important;
  border-radius: 12px !important;
}}
[data-baseweb="input"] input, textarea {{
  color: var(--ink) !important;
  caret-color: var(--ink);
}}
[data-testid="stExpander"] details {{
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: 16px;
}}
button[data-baseweb="tab"] {{
  font-family: Outfit, sans-serif;
  color: var(--muted);
}}
button[data-baseweb="tab"][aria-selected="true"] {{
  color: var(--ink) !important;
  border-bottom-color: var(--accent) !important;
}}
[data-testid="stAlert"],
[data-testid="stAlert"] * {{
  color: #241c14 !important;
}}
[data-testid="stAlert"] {{
  background: #fff6e8 !important;
  border: 1px solid #e4d3b4 !important;
  border-left: 4px solid var(--accent) !important;
  border-radius: 14px !important;
}}
[data-testid="stDataFrame"] {{
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--surface);
}}
.mast {{ display: flex; gap: 0.95rem; align-items: center; margin: 0.2rem 0 0.9rem; }}
.mark {{
  width: 56px; height: 56px; border-radius: 16px;
  background: var(--accent); color: var(--on-accent);
  display: grid; place-items: center;
  font-family: Fraunces, Georgia, serif; font-weight: 640; font-size: 1.2rem;
  box-shadow: 3px 3px 0 var(--line);
}}
.kicker {{
  font-family: Outfit, sans-serif;
  font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--accent); font-weight: 600; margin: 0 0 0.15rem;
}}
.studio-lead {{ color: var(--muted); margin: 0.25rem 0 0; font-size: 1.02rem; }}
.mast h1 {{ margin: 0; font-size: 2.35rem; line-height: 0.95; }}
.palette {{ display: flex; gap: 0.4rem; margin: 0.15rem 0 0.55rem; }}
.palette i {{
  width: 22px; height: 22px; border-radius: 50%;
  border: 1px solid var(--line); display: inline-block;
}}
.badge {{
  display: inline-block; padding: 0.12rem 0.55rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 650; letter-spacing: 0.02em;
  margin-right: 0.35rem; vertical-align: middle;
}}
{badge_css}
.chain {{ display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; margin: 0.35rem 0 0.85rem; }}
.chip {{
  background: var(--surface); color: var(--ink);
  border: 1px solid var(--line); border-radius: 999px;
  padding: 0.32rem 0.75rem; font-size: 0.88rem;
  transition: border-color 140ms ease, transform 140ms ease;
}}
.chip:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
.chip.off {{ opacity: 0.55; text-decoration: line-through; }}
.arrow {{ color: var(--muted); }}
.detail-card, .slip {{
  border: 1px solid var(--line); border-radius: 16px;
  padding: 0.95rem 1.05rem 0.35rem; background: var(--surface);
  box-shadow: 4px 4px 0 var(--line);
}}
.slip p:last-child {{ margin-bottom: 0.7rem; }}
@media (prefers-reduced-motion: reduce) {{
  .stApp::before {{ display: none; }}
  [data-testid="stMetric"], .chip, div[data-testid="stButton"] > button {{
    transition: none; transform: none;
  }}
}}
</style>
"""
