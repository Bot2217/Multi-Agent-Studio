"""Ollama manager logic with HTTP, downloads and processes mocked."""

import io
import json
import tarfile
from pathlib import Path
from urllib.error import URLError

import pytest

from core.local_runtime import (
    MESSAGES,
    LibraryModel,
    ModelTag,
    assess_fit,
    catalog_entry,
    load_bundled_library,
    load_library,
    merge_library,
    parse_library_html,
)
from core.ollama_runtime import (
    OllamaRuntime,
    asset_name,
    gpu_available,
    open_runtime,
    parse_pull_line,
)


class FakeStream(io.BytesIO):
    def __iter__(self):
        yield from self.getvalue().splitlines(keepends=True)


class FakeHttp:
    def __init__(self):
        self.gets = {}
        self.posts = []
        self.deleted = []
        self.pull = []
        self.archive = b""
        self.downloads = []

    def get(self, url, timeout=5):
        if url not in self.gets:
            raise URLError(ConnectionRefusedError())
        return self.gets[url]

    def post(self, url, body, timeout=30):
        self.posts.append((url, body))
        if body.get("model") == "missing":
            return 404, b'{"error":"model not found"}'
        if body.get("model") == "huge":
            return 500, b'{"error":"out of memory"}'
        return 200, b"{}"

    def delete(self, url, body, timeout=30):
        self.deleted.append(body["name"])
        return 200, b"{}"

    def open_stream(self, url, body, timeout=30):
        raw = "".join(self.pull).encode("utf-8")
        return FakeStream(raw)

    def download(self, url, dest, on_progress, cancel):
        self.downloads.append(url)
        if cancel():
            from core.local_runtime import LocalRuntimeError

            raise LocalRuntimeError("download_failed", "Загрузка отменена.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.archive)
        on_progress("Скачиваю Ollama", len(self.archive), len(self.archive))


class FakeProc:
    def __init__(self):
        self.stdout = None
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.returncode = -9


def test_messages_are_russian():
    assert "11434" in MESSAGES["port_busy"]
    assert "администратора" in MESSAGES["binary_missing"]
    assert "памяти" in MESSAGES["out_of_memory"]
    assert "процессор" in MESSAGES["no_gpu"]
    assert "диске" in MESSAGES["disk_full"]


def test_library_html_and_merge():
    page = '<a href="/library/llama3.2">Llama</a><a href="/library/new-model">'
    assert parse_library_html(page) == ["llama3.2", "new-model"]
    bundled = [
        LibraryModel("llama3.2", "Llama 3.2", "", [ModelTag("3b", 10, 20)]),
        LibraryModel("mistral", "Mistral", "", [ModelTag("7b", 5, 6)]),
    ]
    merged = merge_library(bundled, ["llama3.2", "new-model"])
    by_id = {item.model_id: item for item in merged}
    assert by_id["llama3.2"].tags[0].tag == "3b"
    assert by_id["new-model"].tags[0].tag == "latest"
    assert "mistral" in by_id
    assert merge_library(bundled, []) == bundled


def test_bundled_catalog_has_expected_families():
    models = {item.model_id: item for item in load_bundled_library()}
    for name in (
        "llama3.2",
        "qwen2.5",
        "qwen2.5-coder",
        "qwen3",
        "mistral",
        "gemma3",
        "phi4",
        "deepseek-r1",
        "codellama",
        "nomic-embed-text",
    ):
        assert name in models
        assert models[name].tags
        assert models[name].reference(models[name].tags[0].tag).startswith(name)


def test_fit_blocks_disk_and_warns_on_ram():
    tight = assess_fit(5_000, 1_000, 0, None)
    assert not tight.disk_ok
    assert "диске" in tight.message
    ram = assess_fit(100, 10**12, 8 * 1024**3, 2 * 1024**3)
    assert ram.disk_ok and not ram.ram_ok
    assert "памяти" in ram.message
    ok = assess_fit(100, 10**12, 1024, 10**12)
    assert ok.disk_ok and ok.ram_ok and ok.message == ""


def test_picker_entry_is_free_local():
    meta = catalog_entry("llama3.2:3b")
    assert meta["provider"] == "Ollama (локально)"
    assert meta["billing"] == "local"
    assert meta["price_input_per_1m"] == 0
    assert meta["litellm"] == "ollama_chat/llama3.2:3b"
    assert meta["free_tier"] is True


def test_library_fetch_falls_back_to_cache_and_bundle(tmp_path):
    bundled = [LibraryModel("llama3.2", "Llama", "", [ModelTag("3b", 1, 1)])]
    cache = tmp_path / "library.html"
    cache.write_text('<a href="/library/cached-model">', encoding="utf-8")
    used = {"fetch": 0}

    def fetch():
        used["fetch"] += 1
        raise OSError("offline")

    fresh = load_library(fetch=fetch, cache=cache, bundled=bundled, now=cache.stat().st_mtime + 10)
    assert used["fetch"] == 0
    assert any(item.model_id == "cached-model" for item in fresh)
    stale = load_library(
        fetch=fetch, cache=cache, bundled=bundled, now=cache.stat().st_mtime + 10**9
    )
    assert used["fetch"] == 1
    assert [item.model_id for item in stale] == ["llama3.2"]


def test_asset_names():
    assert asset_name("win32", "AMD64") == "ollama-windows-amd64.zip"
    assert asset_name("linux", "x86_64") == "ollama-linux-amd64.tgz"
    assert asset_name("darwin", "arm64") == "ollama-darwin.tgz"
    with pytest.raises(Exception):
        asset_name("haiku", "m68k")


def test_gpu_check_can_be_forced_off():
    assert gpu_available(which=lambda _name: None, devices=[]) is False
    assert (
        gpu_available(which=lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None)
        is True
    )


def test_pull_line_and_cancel(tmp_path):
    assert parse_pull_line('{"status":"pulling","completed":5,"total":10}') == (
        "pulling",
        5,
        10,
        "",
    )
    assert parse_pull_line('{"error":"model not found"}')[3] == "model not found"
    http = FakeHttp()
    http.pull = [
        '{"status":"pulling","completed":1,"total":4}\n',
        '{"error":"model not found"}\n',
    ]
    runtime = OllamaRuntime(
        home=tmp_path, models_dir=tmp_path / "models", http=http, gpu=lambda: True
    )
    seen = []
    with pytest.raises(Exception) as caught:
        runtime.pull(
            "nope", lambda status, done, total: seen.append((status, done, total)), lambda: False
        )
    assert caught.value.code == "model_not_found"
    assert seen == [("pulling", 1, 4)]

    http.pull = ['{"status":"pulling","completed":1,"total":2}\n']
    with pytest.raises(Exception) as cancelled:
        runtime.pull("llama3.2:3b", lambda *_args: None, lambda: True)
    assert "отменена" in str(cancelled.value)


def test_reuses_running_server_and_does_not_spawn(tmp_path):
    http = FakeHttp()
    http.gets["http://127.0.0.1:11434/api/tags"] = (200, b'{"models":[]}')
    spawned = []
    runtime = OllamaRuntime(
        home=tmp_path,
        http=http,
        popen=lambda *args, **kwargs: spawned.append(args) or FakeProc(),
        which=lambda _name: None,
        gpu=lambda: True,
    )
    state = runtime.ensure_running()
    assert state.running and state.external
    assert spawned == []
    runtime.shutdown()
    assert spawned == []


def test_starts_managed_process_and_stops_only_that(tmp_path):
    http = FakeHttp()
    binary = tmp_path / "ollama"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    (tmp_path / ".ulei-managed").write_text(str(binary), encoding="utf-8")
    proc = FakeProc()
    calls = []

    def popen(cmd, **kwargs):
        calls.append((cmd, kwargs["env"]["OLLAMA_MODELS"]))
        http.gets["http://127.0.0.1:11434/api/tags"] = (200, b'{"models":[]}')
        return proc

    runtime = OllamaRuntime(
        home=tmp_path, models_dir=tmp_path / "models", http=http, popen=popen, gpu=lambda: False
    )
    state = runtime.ensure_running()
    assert calls and calls[0][0][1] == "serve"
    assert state.running
    assert state.gpu_note == MESSAGES["no_gpu"]
    runtime.shutdown()
    assert proc.terminated


def test_port_busy_and_missing_binary(tmp_path):
    http = FakeHttp()
    http.gets["http://127.0.0.1:11434/api/tags"] = (200, b"not json")
    runtime = OllamaRuntime(home=tmp_path, http=http, which=lambda _name: None, gpu=lambda: True)
    assert runtime.probe().error == "port_busy"
    with pytest.raises(Exception) as caught:
        runtime.ensure_running()
    assert caught.value.code == "port_busy"

    http.gets.clear()
    quiet = OllamaRuntime(home=tmp_path, http=http, which=lambda _name: None, gpu=lambda: True)
    with pytest.raises(Exception) as missing:
        quiet.ensure_running()
    assert missing.value.code == "binary_missing"


def test_installs_archive_without_touching_a_system_binary(tmp_path):
    http = FakeHttp()
    buffer = io.BytesIO()
    name = asset_name()
    if name.endswith(".zip"):
        import zipfile

        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("ollama.exe", "binary")
    else:
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            payload = b"binary"
            info = tarfile.TarInfo("ollama")
            info.size = len(payload)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(payload))
    http.archive = buffer.getvalue()
    runtime = OllamaRuntime(home=tmp_path, http=http, gpu=lambda: True)
    runtime.install(lambda *_args: None, lambda: False)
    marker = (tmp_path / ".ulei-managed").read_text(encoding="utf-8")
    assert Path(marker).is_file()
    assert Path(marker).name.startswith("ollama")
    assert http.downloads[0].endswith(asset_name())


def test_list_delete_warmup(tmp_path):
    http = FakeHttp()
    http.gets["http://127.0.0.1:11434/api/tags"] = (
        200,
        json.dumps({"models": [{"name": "llama3.2:3b", "size": 20}]}).encode(),
    )
    runtime = OllamaRuntime(home=tmp_path, http=http, gpu=lambda: True)
    assert runtime.installed_models()[0].name == "llama3.2:3b"
    runtime.delete_model("llama3.2:3b")
    assert http.deleted == ["llama3.2:3b"]
    runtime.warmup("llama3.2:3b")
    with pytest.raises(Exception) as missing:
        runtime.warmup("missing")
    assert missing.value.code == "model_not_found"
    with pytest.raises(Exception) as memory:
        runtime.warmup("huge")
    assert memory.value.code == "out_of_memory"


def test_other_runtime_is_rejected():
    with pytest.raises(Exception) as caught:
        open_runtime("lmstudio")
    assert caught.value.code == "unsupported"
