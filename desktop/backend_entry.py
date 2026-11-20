"""PyInstaller entry: Streamlit on 127.0.0.1, files in the per-user data dir."""

from __future__ import annotations

import os
import sys


def main() -> None:
    import multiprocessing

    multiprocessing.freeze_support()
    from api.serve import parse_ports

    port, api_port = parse_ports(sys.argv[1:])
    os.environ["MAS_DESKTOP"] = "1"
    from core.paths import code_root, data_root, migrate_user_files

    data = data_root()
    copied = migrate_user_files(data)
    if copied:
        from core.i18n import t

        print(t("shell.migrated", names=", ".join(copied)), flush=True)

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

    try:
        from api.serve import serve_in_thread

        serve_in_thread(api_port or None)
    except Exception as exc:
        print(f"API_FAILED {exc}", flush=True)

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
