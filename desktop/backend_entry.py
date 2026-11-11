"""PyInstaller entry: Streamlit on 127.0.0.1, files in the per-user data dir."""

from __future__ import annotations

import os
import sys


def _parse_port(argv: list[str]) -> str:
    port = os.environ.get("MAS_PORT", "").strip()
    if "--port" in argv:
        index = argv.index("--port")
        if index + 1 < len(argv):
            port = argv[index + 1].strip()
    if not port.isdigit():
        raise SystemExit("Нужен порт: --port 12345")
    return port


def main() -> None:
    port = _parse_port(sys.argv[1:])
    os.environ["MAS_DESKTOP"] = "1"
    from core.paths import code_root, data_root, migrate_user_files

    data = data_root()
    copied = migrate_user_files(data)
    if copied:
        print("Перенесены файлы: " + ", ".join(copied), flush=True)

    os.environ["MAS_DESKTOP"] = "1"
    os.environ["MAS_DATA_DIR"] = str(data)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ["STREAMLIT_SERVER_PORT"] = port
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_CLIENT_TOOLBAR_MODE"] = "minimal"
    os.environ["STREAMLIT_SERVER_ENABLECORS"] = "false"
    os.environ["STREAMLIT_SERVER_ENABLEXSRFPROTECTION"] = "false"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENTMODE"] = "false"

    app = code_root() / "app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        port,
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--client.toolbarMode",
        "minimal",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
        "--global.developmentMode",
        "false",
    ]
    from streamlit.web import cli as stcli

    print(f"READY http://127.0.0.1:{port}", flush=True)
    stcli.main()


if __name__ == "__main__":
    main()
