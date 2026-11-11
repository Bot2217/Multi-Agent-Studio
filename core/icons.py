"""Inline icons: 24px grid, 2px stroke, currentColor. No emoji, no raster."""

from __future__ import annotations

from urllib.parse import quote

# Each drawing is stroke geometry inside a 24x24 viewBox.
PATHS = {
    "play": '<path d="M8 6.5v11l10-5.5-10-5.5z"/>',
    "users": (
        '<circle cx="9" cy="8" r="2.5"/>'
        '<circle cx="16" cy="9" r="2"/>'
        '<path d="M4.5 18.5c.8-2.6 2.6-4 4.5-4s3.7 1.4 4.5 4"/>'
        '<path d="M13.5 14.8c1.2-.5 2.5-.6 3.6-.2 1.5.5 2.4 1.8 2.9 3.9"/>'
    ),
    "grid": (
        '<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/>'
        '<rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/>'
        '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/>'
        '<rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>'
    ),
    "folder": '<path d="M4 8.5V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-6L10 6H6a2 2 0 0 0-2 2.5z"/>',
    "terminal": '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15H17"/>',
    "help": (
        '<circle cx="12" cy="12" r="8"/>'
        '<path d="M9.5 9.6a2.5 2.5 0 0 1 4.4 1.6c0 1.5-2.1 1.8-2.1 3.2"/>'
        '<path d="M12 17.2h.01"/>'
    ),
    "key": '<circle cx="8" cy="14" r="3"/><path d="M10.8 14H20v2.5h-2.2V14"/>',
    "check": '<path d="M5 12.5 9.5 17 19 7.5"/>',
    "alert": '<path d="M12 4.5 20.5 19h-17z"/><path d="M12 10v4.2M12 16.8h.01"/>',
    "sun": '<circle cx="12" cy="12" r="3.5"/><path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6 18 18M18 6l-1.4 1.4M7.4 16.6 6 18"/>',
    "gear": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M5.6 5.6l1.5 1.5M16.9 16.9l1.5 1.5M18.4 5.6l-1.5 1.5M7.1 16.9l-1.5 1.5"/>'
    ),
}

NAV_ICONS = {
    "run": "play",
    "agents": "users",
    "models": "grid",
    "files": "folder",
    "settings": "gear",
}


def icon(name: str, size: int = 24) -> str:
    body = PATHS[name]
    return (
        f'<svg class="ico" viewBox="0 0 24 24" width="{size}" height="{size}" '
        'fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{body}</svg>"
    )


def _mask_svg(name: str) -> str:
    body = PATHS[name]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )


def icon_css() -> str:
    rules = []
    for screen, name in NAV_ICONS.items():
        url = quote(_mask_svg(name), safe="")
        rules.append(
            f'[class*="st-key-nav_{screen}"] button::before {{'
            f"content:''; width:18px; height:18px; margin-right:8px; flex:none;"
            f"background: currentColor;"
            f'-webkit-mask: url("data:image/svg+xml,{url}") center / contain no-repeat;'
            f'mask: url("data:image/svg+xml,{url}") center / contain no-repeat;'
            "}"
        )
    return "\n".join(rules)
