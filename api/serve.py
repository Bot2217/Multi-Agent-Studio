"""Bind the engine to 127.0.0.1 and remember the port for the desktop shell."""

from __future__ import annotations

import json
import os
import socket
import threading

from core.i18n import t
from core.paths import data_root


def _flag(argv: list[str], name: str) -> str:
    if name not in argv:
        return ""
    index = argv.index(name)
    if index + 1 >= len(argv):
        return ""
    return argv[index + 1].strip()


def parse_ports(argv: list[str]) -> tuple[str, str]:
    """Streamlit port is required. The engine port may be empty."""
    port = _flag(argv, "--port") or os.environ.get("MAS_PORT", "").strip()
    if not port.isdigit():
        raise SystemExit(t("shell.port_required"))
    api_port = _flag(argv, "--api-port") or os.environ.get("MAS_API_PORT", "").strip()
    if api_port and not api_port.isdigit():
        raise SystemExit(t("shell.api_port"))
    return port, api_port


def free_port() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return str(sock.getsockname()[1])


def write_endpoint(port: str) -> None:
    path = data_root() / "api.json"
    path.write_text(
        json.dumps(
            {
                "port": int(port),
                "health": f"http://127.0.0.1:{port}/api/v1/health",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def serve_in_thread(port: str | None = None):
    """Start uvicorn on a daemon thread. Returns the server and the port."""
    import uvicorn

    from api.app import create_app

    chosen = port or free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(),
            host="127.0.0.1",
            port=int(chosen),
            log_level="warning",
            access_log=False,
        )
    )
    threading.Thread(target=server.run, name="ulei-api", daemon=True).start()
    write_endpoint(chosen)
    print(f"API_READY http://127.0.0.1:{chosen}", flush=True)
    return server, chosen
