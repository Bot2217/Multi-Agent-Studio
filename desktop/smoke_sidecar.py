"""Run a frozen sidecar outside the source tree and wait until it is healthy.

The v0.1.2 executable exited immediately:

    ModuleNotFoundError: No module named 'api'

A passing run uses ``--port`` and ``--api-port``, the same arguments Tauri
passes, with ``PYTHONPATH`` removed. ``--in-place`` launches the file where
it was installed instead of copying it out first.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure_stdio() -> None:
    """Windows CI captures stdout as cp1252. A Cyrillic install path must not abort the smoke."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


def emit(text: str) -> None:
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("utf-8", "backslashreplace").decode("ascii"), flush=True)


def missing_api(text: str) -> bool:
    return "No module named 'api'" in text or 'No module named "api"' in text


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def default_executable() -> Path:
    for name in ("ulei-backend.exe", "ulei-backend"):
        path = ROOT / "dist" / name
        if path.is_file():
            return path
    raise SystemExit("no dist/ulei-backend executable; build the sidecar first")


def http_ok(url: str, headers: dict[str, str] | None = None, timeout: float = 2) -> bool:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def token_candidates(data_home: Path) -> list[Path]:
    """Where api.json lands for the HOME / APPDATA / XDG values this smoke sets."""
    return [
        data_home / "ulei" / "api.json",
        data_home / "Roaming" / "ulei" / "api.json",
        data_home / "Library" / "Application Support" / "ulei" / "api.json",
    ]


def wait_token(data_home: Path, deadline: float) -> str:
    candidates = token_candidates(data_home)
    while time.monotonic() < deadline:
        for path in candidates:
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            token = str(payload.get("token") or "")
            if token:
                return token
        time.sleep(0.25)
    return ""


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def failure(what: str, proc: subprocess.Popen, log: Path, url: str) -> str:
    text = ""
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace")[-4000:]
    return f"SMOKE_FAIL {what} url={url} exit={proc.poll()}\n{text}"


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", nargs="?", type=Path)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args(argv)

    source = (args.executable or default_executable()).resolve()
    if not source.is_file():
        print(f"missing sidecar: {source}", file=sys.stderr)
        return 1
    if args.in_place and _inside(source, ROOT):
        print(f"refusing to smoke an executable inside the checkout: {source}", file=sys.stderr)
        return 1

    stage_parent = Path(tempfile.mkdtemp(prefix="ulei-sidecar-smoke-"))
    data_home = stage_parent / "home"
    data_home.mkdir()
    if _inside(stage_parent, ROOT):
        print(f"smoke stage is inside the checkout: {stage_parent}", file=sys.stderr)
        return 1

    if args.in_place:
        executable = source
        workdir = source.parent
    else:
        workdir = stage_parent / "app"
        workdir.mkdir()
        executable = workdir / source.name
        shutil.copy2(source, executable)
        if os.name != "nt":
            executable.chmod(0o755)
        if _inside(workdir, ROOT):
            print(f"smoke workdir is inside the checkout: {workdir}", file=sys.stderr)
            return 1

    port = free_port()
    api_port = free_port()
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH"):
        env.pop(key, None)
    env["PYTHONNOUSERSITE"] = "1"
    env["HOME"] = str(data_home)
    env["USERPROFILE"] = str(data_home)
    env["APPDATA"] = str(data_home / "Roaming")
    env["LOCALAPPDATA"] = str(data_home / "Local")
    env["XDG_DATA_HOME"] = str(data_home)
    env["XDG_STATE_HOME"] = str(data_home / "state")
    env["XDG_CONFIG_HOME"] = str(data_home / "config")

    log = stage_parent / "smoke.log"
    emit(f"SMOKE exe={executable} cwd={workdir} port={port} api={api_port} data={data_home}")
    popen_kwargs: dict = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        proc = subprocess.Popen(
            [str(executable), "--port", str(port), "--api-port", str(api_port)],
            cwd=workdir,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            **popen_kwargs,
        )
        page = f"http://127.0.0.1:{port}/_stcore/health"
        engine = f"http://127.0.0.1:{api_port}/api/v1/health"
        deadline = time.monotonic() + args.timeout
        page_ok = False
        engine_ok = False
        token = ""
        try:
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                if http_ok(page):
                    page_ok = True
                    break
                time.sleep(0.25)
            if not page_ok:
                print(failure("streamlit health", proc, log, page), file=sys.stderr)
                return 1
            # The engine writes api.json before Streamlit is healthy. Keep a
            # little time for that file even when the page itself was slow.
            token_deadline = max(deadline, time.monotonic() + 30)
            token = wait_token(data_home, token_deadline)
            if not token:
                print(failure("api.json token", proc, log, engine), file=sys.stderr)
                return 1
            while time.monotonic() < token_deadline:
                if proc.poll() is not None:
                    break
                if http_ok(engine, {"Authorization": f"Bearer {token}"}):
                    engine_ok = True
                    break
                time.sleep(0.25)
            if not engine_ok:
                print(failure("engine health", proc, log, engine), file=sys.stderr)
                return 1
        finally:
            stop(proc)

    text = log.read_text(encoding="utf-8", errors="replace")
    if missing_api(text):
        print(failure("missing api module", proc, log, page), file=sys.stderr)
        return 1
    emit(f"SMOKE_OK {page} {engine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
