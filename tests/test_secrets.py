"""Keys move into the keychain and disappear from logs."""

from core.secrets import MemoryStore, redact, use_secret_store
from core.ui_helpers import load_keys_from_env, save_keys_to_env


def test_memory_store_migrates_plaintext_and_hides_it(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("GOOGLE_API_KEY=secret-value\n", encoding="utf-8")
    monkeypatch.setattr("core.ui_helpers.ENV_PATH", env_path)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    store = MemoryStore()
    use_secret_store(store)
    loaded = load_keys_from_env()
    assert loaded["GOOGLE_API_KEY"] == "secret-value"
    assert store.get("GOOGLE_API_KEY") == "secret-value"
    assert "secret-value" not in env_path.read_text(encoding="utf-8")
    use_secret_store(None)


def test_save_with_store_does_not_write_the_key_to_disk(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    monkeypatch.setattr("core.ui_helpers.ENV_PATH", env_path)
    store = MemoryStore()
    use_secret_store(store)
    save_keys_to_env({"GOOGLE_API_KEY": "another-secret"})
    assert store.get("GOOGLE_API_KEY") == "another-secret"
    assert "another-secret" not in env_path.read_text(encoding="utf-8")
    use_secret_store(None)


def test_redact_replaces_long_secrets_only():
    assert redact("key abcdef in the log", ["abcdef"]) == "key *** in the log"
    assert redact("short ab", ["ab"]) == "short ab"
