---
name: ui-redesign
description: Redesign Multi-Agent Studio screens with the bento layout, shared tokens, and theme screenshots. Use when changing app.py, themes, icons, or the visual layout.
---

# UI redesign

Read `.cursor/rules/ui-design.mdc` and `AGENTS.md` before editing.

## Workflow

1. Audit the current screens: Запуск, Агенты, Модели, Файлы, SSH, Справка. Note the primary action on each (run the task, save roles, filter models, read a file, run SSH, read help).
2. Keep those actions. Do not drop a control to simplify a picture.
3. Group each screen into bento cards (`st.container` with a `card_` key). Gaps are 24 px, card padding 16 px, radius 12–20 px.
4. Reuse icons from `core/icons.py`. Add a new icon there instead of pasting a one-off SVG.
5. Use the tokens in `core/themes.py`. Night stays the default charcoal. Paper and ember stay distinct. Check contrast with `contrast_issues()`.
6. Motion stays at 160 ms. Disable it under `prefers-reduced-motion`. Focus rings stay visible.
7. Run `pytest -q` and `ruff format --check .` and `ruff check .`.
8. Screenshot every screen in every theme with Playwright against `streamlit run app.py`. Update `docs/GUIDE.md` if theme names or fonts changed. Replace the README image only when the default screen no longer matches.

## Critical path

Key in the sidebar, folder and task on Запуск, then «Запустить». A redesign that hides that path is incomplete.
