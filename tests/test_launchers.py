"""Launch scripts must survive real shells.

cmd.exe splits batch files on CRLF. A UTF-8 LF file loses a byte at every
line break, so `echo` becomes `cho` and `https` becomes `ttps`. Russian
Windows consoles also read batch files in CP866; `chcp 65001` makes the
parser mis-count those bytes. The working copy of start.bat is therefore
CP866 + CRLF, with no code-page switch.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _bytes(name: str) -> bytes:
    return (ROOT / name).read_bytes()


def test_windows_launcher_is_cp866_crlf_and_runs_setup():
    raw = _bytes("start.bat")
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert not raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("cp866")
    for line in text.splitlines():
        assert not line.strip().lower().startswith("chcp")
    assert "%PY% -m venv .venv" in text
    assert "pip install -r requirements.txt" in text
    assert "streamlit run app.py" in text
    assert 'if /I "%~1"=="setup" goto setup' in text
    assert "Внимание: git pull не удался" in text
    assert "Браузер: http://localhost:8501" in text
    assert "https://git-scm.com/download/win" in text


def test_shell_launchers_stay_lf_and_do_not_use_cmd_syntax():
    for name in ("start.sh", "run.sh"):
        raw = _bytes(name)
        assert b"\r" not in raw, name
        text = raw.decode("utf-8")
        assert text.startswith("#!")
        assert "streamlit run app.py" in text
        assert "pip install" in text
        assert "chcp" not in text.lower()
