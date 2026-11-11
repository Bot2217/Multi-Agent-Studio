# Agent notes

This is a local Streamlit studio. Interface copy is Russian.

## Run, test, lint

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
streamlit run app.py
ruff format --check .
ruff check .
pytest -q
```

Windows setup without opening the window: `start.bat setup`.

## UI work

- Design brief and tokens: `.cursor/rules/ui-design.mdc`
- Redesign workflow: `.cursor/skills/ui-redesign/SKILL.md`
- Icons: `.cursor/skills/svg-icons/SKILL.md`
- Implementation: `app.py`, `core/themes.py`, `core/icons.py`
- Theme (`auto`, `light`, `dark`) and palette (`graphite`, `warm`) persist in `user_settings.json`. Defaults are `auto` and `graphite`.
- User-facing guide: `docs/GUIDE.md`
