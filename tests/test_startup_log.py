from core.startup_log import log_path


def test_windows_log_is_under_local_appdata(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\User\AppData\Local")
    path = log_path("win32")
    assert path.parts[-3:] == ("ulei", "logs", "sidecar.log")
    assert "AppData" in str(path) and "Local" in str(path)


def test_other_platforms_are_not_the_install_dir():
    mac = log_path("darwin")
    assert mac.parts[-3:] == ("Logs", "ulei", "sidecar.log")
    linux = log_path("linux")
    assert linux.name == "sidecar.log"
    assert "Улей" not in str(linux)
