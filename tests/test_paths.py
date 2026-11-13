from pathlib import Path

from core.paths import data_root, migrate_user_files


def test_data_root_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MAS_DATA_DIR", str(tmp_path / "studio"))
    assert data_root() == tmp_path / "studio"
    assert (tmp_path / "studio").is_dir()


def test_migrate_copies_settings_once(tmp_path, monkeypatch):
    source = tmp_path / "Multi-Agent-Studio"
    source.mkdir()
    (source / "user_settings.json").write_text('{"theme": "night"}', encoding="utf-8")
    (source / ".env").write_text("GOOGLE_API_KEY=abc\n", encoding="utf-8")
    data = tmp_path / "data"
    monkeypatch.chdir(source)
    copied = migrate_user_files(data)
    assert copied == ["user_settings.json", ".env"]
    assert (data / "user_settings.json").read_text(encoding="utf-8").startswith("{")
    assert "abc" in (data / ".env").read_text(encoding="utf-8")
    (data / ".env").write_text("KEEP=1\n", encoding="utf-8")
    again = migrate_user_files(data)
    assert again == []
    assert (data / ".env").read_text(encoding="utf-8") == "KEEP=1\n"
    assert (data / "workspace").is_dir()


def test_desktop_data_dir_is_ulei(monkeypatch, tmp_path):
    monkeypatch.setenv("MAS_DESKTOP", "1")
    monkeypatch.delenv("MAS_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert data_root() == tmp_path / "ulei"
    assert (tmp_path / "ulei").is_dir()


def test_migrate_skips_the_destination_itself(tmp_path):
    (tmp_path / "user_settings.json").write_text("{}", encoding="utf-8")
    assert migrate_user_files(tmp_path) == []
    assert Path(tmp_path / "workspace").is_dir()
