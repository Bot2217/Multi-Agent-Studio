"""Bind the engine to 127.0.0.1 and remember the port for the desktop shell."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from contextlib import contextmanager

from core.i18n import t
from core.paths import data_root


class ApiStartupError(RuntimeError):
    """The engine thread died or never accepted a connection."""


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


def _silence_signals(server) -> None:
    """Do not install signal handlers from the engine thread.

    On Windows, uvicorn's handler registration raises NotImplementedError
    when it runs on the main thread of a frozen app, and from a side thread
    it can steal Ctrl+C from Streamlit. The desktop shell owns shutdown.
    """

    @contextmanager
    def _noop():
        yield

    if hasattr(server, "capture_signals"):
        server.capture_signals = _noop


def wait_until_listening(
    port: str, thread: threading.Thread, errors: list[BaseException], timeout: float
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if errors:
            return False
        if not thread.is_alive() and not _port_open(port):
            return False
        if _port_open(port):
            return True
        time.sleep(0.05)
    return _port_open(port)


def _port_open(port: str) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.2):
            return True
    except OSError:
        return False


def serve_in_thread(port: str | None = None, *, timeout: float = 30):
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
    _silence_signals(server)
    errors: list[BaseException] = []

    def target() -> None:
        try:
            server.run()
        except BaseException as exc:  # noqa: BLE001 — report and let Streamlit continue
            errors.append(exc)

    thread = threading.Thread(target=target, name="ulei-api", daemon=True)
    thread.start()
    if not wait_until_listening(chosen, thread, errors, timeout):
        detail = errors[0] if errors else "timed out"
        raise ApiStartupError(f"engine did not listen on 127.0.0.1:{chosen}: {detail}")
    write_endpoint(chosen)
    print(f"API_READY http://127.0.0.1:{chosen}", flush=True)
    return server, chosen
