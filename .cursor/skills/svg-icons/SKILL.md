---
name: svg-icons
description: Add or revise the studio icon set so every icon matches the 24px, 2px, currentColor rule. Use when drawing icons for navigation, status, or empty states.
---

# SVG icons

Icons live in `core/icons.py`. The UI and the nav masks both read that file.

## Draw

1. Open a 24 by 24 grid. Keep strokes on whole or half pixels so the line stays sharp.
2. Use `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`, round caps and joins.
3. One metaphor per icon. Match the weight of `play`, `folder`, and `terminal` already in `PATHS`.
4. Do not embed color, gradients, filters, or text. Do not export PNG.
5. Add the name to `PATHS`. If the icon is a section, map it in `NAV_ICONS` so the tab mask updates.
6. Check `icon(name)` in a test or a short Python snippet: viewBox is `0 0 24 24`, stroke width is 2, and the string contains `currentColor`.

## Use

- In HTML strings, call `icon("folder")`.
- Do not paste a second copy of the path into `app.py`.
