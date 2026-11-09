from core.ui_helpers import (
    load_keys_from_env,
    load_user_settings,
    preset_paths,
    save_keys_to_env,
    save_user_settings,
)


def test_keys_roundtrip_skips_blanks(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    monkeypatch.setattr("core.ui_helpers.ENV_PATH", env_path)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    save_keys_to_env({"GOOGLE_API_KEY": "abc", "OPENAI_API_KEY": "  "})
    text = env_path.read_text(encoding="utf-8")
    assert "GOOGLE_API_KEY=abc" in text
    assert "OPENAI_API_KEY" not in text
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    loaded = load_keys_from_env()
    assert loaded["GOOGLE_API_KEY"] == "abc"


def test_user_settings_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "user_settings.json"
    monkeypatch.setattr("core.ui_helpers.SETTINGS_PATH", path)
    save_user_settings(
        {"pipeline": "code_only", "agent_overrides": {"developer": {"model": "gemini_38_flash"}}}
    )
    loaded = load_user_settings()
    assert loaded["pipeline"] == "code_only"
    assert loaded["agent_overrides"]["developer"]["model"] == "gemini_38_flash"
    assert "updated_at" in loaded


def test_project_preset_is_always_offered(tmp_path):
    missing = tmp_path / "does-not-exist"
    labels = [label for label, _path in preset_paths(missing)]
    assert "Проект" in labels
