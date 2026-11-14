"""Catalog filters, a pausable download, and Ollama startup before a local run."""

import threading
import time

from fastapi.testclient import TestClient

from api.app import create_app
from api.runner import engine_runner
from contracts.v1 import Task
from core.catalog_search import Hardware, search_models
from core.downloads import DownloadManager
from core.local_runtime import LocalRuntimeError, load_bundled_library
from core.orchestrator import load_config


def test_search_filters_quant_size_and_fit():
    models = load_bundled_library()
    roomy = Hardware(free_disk=10**15, free_ram=10**15, free_vram=10**15)
    hits = search_models(models, roomy, text="coder", quant="Q8")
    assert hits
    assert all("coder" in hit.name for hit in hits)
    assert all("Q8" in hit.quant for hit in hits)

    tight = Hardware(free_disk=1, free_ram=10**15, free_vram=10**15)
    hidden = search_models(models, tight, text="phi4", only_fit=True)
    assert hidden == []
    shown = search_models(models, tight, text="phi4")
    assert shown and not shown[0].disk_ok
    vram = search_models(
        models,
        Hardware(free_disk=10**15, free_ram=10**15, free_vram=1),
        text="phi4",
    )
    assert vram and not vram[0].vram_ok
    assert "видеокарте" in vram[0].message


def test_catalog_endpoint_uses_the_same_filters():
    models = load_bundled_library()

    def search(**kwargs):
        return search_models(
            models,
            Hardware(free_disk=10**15, free_ram=10**15, free_vram=10**15),
            **kwargs,
        )

    client = TestClient(
        create_app(config=load_config(), search=search, downloads=DownloadManager(_noop))
    )
    response = client.get("/api/v1/models/catalog", params={"q": "llama3.2", "quant": "Q4"})
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "llama3.2:3b" in names
    assert "llama3.2:1b" not in names


def test_pause_and_cancel_a_download():
    def pull(name, on_progress, cancel):
        on_progress("pulling", 1, 4)
        while not cancel():
            time.sleep(0.01)
        raise LocalRuntimeError("download_failed", "Загрузка модели отменена.")

    paused = _wait_state(DownloadManager(pull), "llama3.2:3b", "pause", "paused")
    assert paused.message
    cancelled = _wait_state(DownloadManager(pull), "qwen3:4b", "cancel", "missing")
    assert cancelled.state == "missing"


def test_ollama_failure_is_an_error_event():
    cfg = load_config()
    cfg["agents"]["developer"]["model"] = "ollama_chat/llama3.2:3b"
    calls = []

    def prepare():
        calls.append("start")
        raise LocalRuntimeError("binary_missing")

    task = Task(id="task_local", text="hi", pipeline="single", workspace="/tmp")
    seen = []
    engine_runner(
        task,
        seen.append,
        threading.Event(),
        api_keys={},
        config=cfg,
        prepare_local=prepare,
    )
    assert calls == ["start"]
    assert seen[0].type == "error"
    assert seen[0].code == "binary_missing"
    assert seen[-1].type == "done"
    assert seen[-1].outcome == "failed"


def _noop(name, on_progress, cancel):
    return None


def _wait_state(manager: DownloadManager, name: str, action: str, wanted: str):
    started = threading.Event()
    original = manager._pull

    def pull(model, on_progress, cancel):
        started.set()
        return original(model, on_progress, cancel)

    manager._pull = pull
    manager.start(name)
    assert started.wait(2)
    getattr(manager, action)(name)
    deadline = time.monotonic() + 2
    status = manager.status(name)
    while time.monotonic() < deadline:
        status = manager.status(name)
        if status and status.state == wanted:
            return status
        time.sleep(0.01)
    assert status is not None and status.state == wanted
    return status
