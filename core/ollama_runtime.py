"""Ollama as a local runtime the hive can install, start and stop."""

from __future__ import annotations

import atexit
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from collections import deque
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.i18n import t
from core.local_runtime import (
    InstalledModel,
    LocalRuntimeError,
    Probe,
    default_models_dir,
    default_ollama_home,
)

DOWNLOAD_ROOT = "https://github.com/ollama/ollama/releases/latest/download/"
ASSETS = {
    ("win32", "amd64"): "ollama-windows-amd64.zip",
    ("win32", "arm64"): "ollama-windows-arm64.zip",
    ("linux", "x86_64"): "ollama-linux-amd64.tgz",
    ("linux", "aarch64"): "ollama-linux-arm64.tgz",
    ("darwin", "x86_64"): "ollama-darwin.tgz",
    ("darwin", "arm64"): "ollama-darwin.tgz",
}
_MANAGED: list[subprocess.Popen] = []


def _shutdown_managed() -> None:
    for proc in list(_MANAGED):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


atexit.register(_shutdown_managed)


def asset_name(system: str | None = None, machine: str | None = None) -> str:
    system = system or sys.platform
    machine = (machine or platform.machine() or "").lower()
    if machine in {"amd64", "x86_64"}:
        machine = "amd64" if system == "win32" else "x86_64"
    elif machine in {"arm64", "aarch64"}:
        machine = "arm64" if system != "linux" else "aarch64"
    name = ASSETS.get((system, machine))
    if not name:
        raise LocalRuntimeError(
            "download_failed",
            t("ollama.no_build", system=system, machine=machine),
        )
    return name


def gpu_available(
    which: Callable[[str], str | None] | None = None,
    devices: list[Path] | None = None,
) -> bool:
    finder = which or shutil.which
    if finder("nvidia-smi") or finder("rocminfo"):
        return True
    if devices is None and sys.platform == "darwin":
        return True
    candidates = devices if devices is not None else [Path("/dev/kfd"), Path("/dev/dri")]
    return any(path.exists() for path in candidates)


class UrllibClient:
    def get(self, url: str, timeout: float = 5) -> tuple[int, bytes]:
        return self._read("GET", url, None, timeout)

    def post(self, url: str, body: dict, timeout: float = 30) -> tuple[int, bytes]:
        return self._read("POST", url, body, timeout)

    def delete(self, url: str, body: dict, timeout: float = 30) -> tuple[int, bytes]:
        return self._read("DELETE", url, body, timeout)

    def open_stream(self, url: str, body: dict, timeout: float = 30):
        return urlopen(self._request("POST", url, body), timeout=timeout)

    def download(
        self,
        url: str,
        dest: Path,
        on_progress: Callable[[str, int, int], None],
        cancel: Callable[[], bool],
    ) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_suffix(dest.suffix + ".part")
        try:
            with urlopen(Request(url, headers={"User-Agent": "ulei"}), timeout=60) as response:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                with partial.open("wb") as handle:
                    while True:
                        if cancel():
                            raise LocalRuntimeError(
                                "download_failed", t("ollama.download_cancelled")
                            )
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        handle.write(chunk)
                        done += len(chunk)
                        on_progress(t("ollama.downloading_app"), done, total)
            partial.replace(dest)
        except LocalRuntimeError:
            partial.unlink(missing_ok=True)
            raise
        except (OSError, URLError, HTTPError) as exc:
            partial.unlink(missing_ok=True)
            raise LocalRuntimeError("download_failed") from exc

    def _read(self, method: str, url: str, body: dict | None, timeout: float) -> tuple[int, bytes]:
        try:
            with urlopen(self._request(method, url, body), timeout=timeout) as response:
                return response.status, response.read()
        except HTTPError as exc:
            payload = exc.read() if exc.fp else b""
            return exc.code, payload

    def _request(self, method: str, url: str, body: dict | None) -> Request:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"User-Agent": "ulei", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        return Request(url, data=data, headers=headers, method=method)


class OllamaRuntime:
    runtime_id = "ollama"

    @property
    def label(self) -> str:
        return t("ollama.provider")

    def __init__(
        self,
        home: Path | None = None,
        models_dir: Path | None = None,
        base_url: str = "http://127.0.0.1:11434",
        http: object | None = None,
        popen: Callable | None = None,
        which: Callable[[str], str | None] | None = None,
        gpu: Callable[[], bool] | None = None,
    ):
        self.home = Path(home) if home else default_ollama_home()
        self._models = Path(models_dir) if models_dir else default_models_dir()
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.http = http or UrllibClient()
        self._popen = popen or subprocess.Popen
        self._which = which or shutil.which
        self._gpu = gpu or (lambda: gpu_available(self._which))
        self._proc: subprocess.Popen | None = None
        self._log: deque[str] = deque(maxlen=400)

    def models_dir(self) -> Path:
        return self._models

    def set_models_dir(self, path: Path) -> None:
        self._models = Path(path)

    def disk_free(self) -> int:
        target = self._models if self._models.exists() else self._models.parent
        try:
            target.mkdir(parents=True, exist_ok=True)
            return shutil.disk_usage(target).free
        except OSError:
            return 0

    def ram_free(self) -> int | None:
        if sys.platform.startswith("linux"):
            try:
                for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) * 1024
            except (OSError, ValueError, IndexError):
                return None
        return None

    def log_tail(self, limit: int = 200) -> str:
        lines = list(self._log)[-limit:]
        return "\n".join(lines)

    def probe(self) -> Probe:
        binary = self._binary_path()
        note = "" if self._gpu() else t("ollama.no_gpu")
        try:
            status, payload = self.http.get(f"{self.base_url}/api/tags", timeout=3)
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, ConnectionRefusedError):
                return Probe(
                    binary=str(binary or ""), managed_binary=self._managed_binary(), gpu_note=note
                )
            return Probe(error="port_busy", binary=str(binary or ""), gpu_note=note)
        except OSError:
            return Probe(error="port_busy", binary=str(binary or ""), gpu_note=note)
        if status == 200 and _looks_like_tags(payload):
            return Probe(
                running=True,
                external=self._proc is None or (self._proc.poll() is not None),
                binary=str(binary or ""),
                managed_binary=self._managed_binary(),
                gpu_note=note,
            )
        return Probe(error="port_busy", binary=str(binary or ""), gpu_note=note)

    def install(
        self,
        on_progress: Callable[[str, int, int], None],
        cancel: Callable[[], bool],
    ) -> None:
        name = asset_name()
        archive = self.home / name
        url = DOWNLOAD_ROOT + name
        self.http.download(url, archive, on_progress, cancel)
        on_progress(t("ollama.unpacking"), 0, 0)
        try:
            _extract(archive, self.home)
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
            raise LocalRuntimeError("download_failed", t("ollama.archive_bad")) from exc
        finally:
            archive.unlink(missing_ok=True)
        binary = self._find_unpacked()
        if binary is None:
            raise LocalRuntimeError("binary_missing")
        if os.name != "nt":
            binary.chmod(binary.stat().st_mode | 0o755)
        (self.home / ".ulei-managed").write_text(str(binary), encoding="utf-8")

    def ensure_running(self) -> Probe:
        state = self.probe()
        if state.running:
            return state
        if state.error == "port_busy":
            raise LocalRuntimeError("port_busy")
        binary = self._binary_path()
        if binary is None:
            raise LocalRuntimeError("binary_missing")
        self._models.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = str(self._models)
        env["OLLAMA_HOST"] = self.base_url.replace("http://", "").replace("https://", "")
        try:
            proc = self._popen(
                [str(binary), "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise LocalRuntimeError("binary_missing") from exc
        self._proc = proc
        _MANAGED.append(proc)
        if proc.stdout is not None:
            _spawn_reader(proc, self._log)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise LocalRuntimeError(
                    "binary_missing",
                    t("ollama.exited"),
                )
            try:
                status, payload = self.http.get(f"{self.base_url}/api/tags", timeout=2)
            except (URLError, OSError):
                time.sleep(0.4)
                continue
            if status == 200 and _looks_like_tags(payload):
                return self.probe()
            time.sleep(0.4)
        raise LocalRuntimeError("port_busy", t("ollama.no_answer"))

    def shutdown(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def installed_models(self) -> list[InstalledModel]:
        status, payload = self._api_get("/api/tags")
        if status != 200:
            raise LocalRuntimeError("port_busy")
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LocalRuntimeError("port_busy") from exc
        models = []
        for item in data.get("models") or []:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            models.append(InstalledModel(str(item["name"]), int(item.get("size") or 0)))
        return models

    def pull(
        self,
        name: str,
        on_progress: Callable[[str, int, int], None],
        cancel: Callable[[], bool],
    ) -> None:
        stream = self.http.open_stream(f"{self.base_url}/api/pull", {"name": name, "stream": True})
        try:
            for raw in stream:
                if cancel():
                    raise LocalRuntimeError("download_failed", t("ollama.model_cancelled"))
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                status, completed, total, error = parse_pull_line(line)
                if error:
                    if "not found" in error.lower():
                        raise LocalRuntimeError("model_not_found")
                    if "space" in error.lower() or "disk" in error.lower():
                        raise LocalRuntimeError("disk_full")
                    raise LocalRuntimeError("download_failed", error)
                on_progress(status or t("ollama.pulling"), completed, total)
        finally:
            close = getattr(stream, "close", None)
            if close:
                close()

    def delete_model(self, name: str) -> None:
        status, payload = self.http.delete(
            f"{self.base_url}/api/delete", {"name": name}, timeout=60
        )
        if status == 404:
            raise LocalRuntimeError("model_not_found")
        if status >= 400:
            text = payload.decode("utf-8", errors="replace")
            raise LocalRuntimeError("download_failed", text or t("ollama.download_failed"))

    def warmup(self, name: str) -> None:
        status, payload = self.http.post(
            f"{self.base_url}/api/generate",
            {
                "model": name,
                "prompt": "ok",
                "stream": False,
                "keep_alive": "10m",
                "options": {"num_predict": 1},
            },
            timeout=600,
        )
        text = payload.decode("utf-8", errors="replace").lower()
        if status == 404 or "not found" in text:
            raise LocalRuntimeError("model_not_found")
        if "out of memory" in text or "insufficient memory" in text:
            raise LocalRuntimeError("out_of_memory")
        if status >= 400:
            raise LocalRuntimeError("download_failed", t("ollama.warmup_failed"))

    def _api_get(self, path: str) -> tuple[int, bytes]:
        try:
            return self.http.get(f"{self.base_url}{path}", timeout=5)
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, ConnectionRefusedError):
                raise LocalRuntimeError("binary_missing", t("ollama.not_running")) from exc
            raise LocalRuntimeError("port_busy") from exc
        except OSError as exc:
            raise LocalRuntimeError("port_busy") from exc

    def _managed_binary(self) -> bool:
        return (self.home / ".ulei-managed").is_file()

    def _binary_path(self) -> Path | None:
        marker = self.home / ".ulei-managed"
        if marker.is_file():
            recorded = Path(marker.read_text(encoding="utf-8").strip())
            if recorded.is_file():
                return recorded
        found = self._find_unpacked()
        if found:
            return found
        system = self._which("ollama")
        return Path(system) if system else None

    def _find_unpacked(self) -> Path | None:
        names = {"ollama.exe", "ollama"}
        if not self.home.exists():
            return None
        for path in self.home.rglob("*"):
            if path.is_file() and path.name.lower() in names:
                return path
        return None


def parse_pull_line(line: str) -> tuple[str, int, int, str]:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return line[:120], 0, 0, ""
    if not isinstance(data, dict):
        return "", 0, 0, ""
    error = str(data.get("error") or "")
    status = str(data.get("status") or "")
    completed = int(data.get("completed") or 0)
    total = int(data.get("total") or 0)
    return status, completed, total, error


def _looks_like_tags(payload: bytes) -> bool:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and "models" in data


def _extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(dest)
        return
    with tarfile.open(archive, "r:*") as handle:
        handle.extractall(dest, filter="data")


def _spawn_reader(proc: subprocess.Popen, sink: deque[str]) -> None:
    import threading

    def read() -> None:
        stream = proc.stdout
        if stream is None:
            return
        for raw in stream:
            sink.append(raw.decode("utf-8", errors="replace").rstrip())

    threading.Thread(target=read, daemon=True).start()


def open_runtime(kind: str = "ollama", **kwargs) -> OllamaRuntime:
    if kind == "ollama":
        return OllamaRuntime(**kwargs)
    raise LocalRuntimeError("unsupported")
