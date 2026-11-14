"""REST, server-sent events and a WebSocket for hive contract v1."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.bus import EventBus
from api.hive import TaskBook, list_agents, list_swarms, load_hive_config
from api.runner import engine_runner
from contracts.v1 import CONTRACT_VERSION, DoneEvent, ErrorEvent, LocalModelStatus, Task
from core.ui_helpers import load_keys_from_env

ModelSource = Callable[[], list[LocalModelStatus]]


class TaskBody(BaseModel):
    text: str = Field(min_length=1)
    pipeline: str = Field(min_length=1)
    workspace: str = Field(min_length=1)


class RunBody(BaseModel):
    timeout_s: float | None = Field(default=None, gt=0, le=24 * 60 * 60)


class RunHandle:
    def __init__(self) -> None:
        self.cancel = threading.Event()
        self.thread: threading.Thread | None = None

    def alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


class Engine:
    def __init__(
        self,
        cfg: dict,
        runner: Callable | None = None,
        models: ModelSource | None = None,
    ):
        self.cfg = cfg
        self.book = TaskBook(cfg)
        self.bus = EventBus()
        self.runner = runner or _default_runner
        self.models = models or (lambda: [])
        self._runs: dict[str, RunHandle] = {}
        self._lock = threading.Lock()

    def start(self, task: Task, timeout_s: float | None) -> None:
        with self._lock:
            handle = self._runs.get(task.id)
            if handle and handle.alive():
                raise HTTPException(status_code=409, detail="already_running")
            handle = RunHandle()
            self._runs[task.id] = handle

            def target() -> None:
                try:
                    self.runner(task, self.bus.publish, handle.cancel, timeout_s)
                except Exception as exc:
                    self.bus.publish(
                        ErrorEvent(
                            task_id=task.id,
                            code="run_failed",
                            message=f"{type(exc).__name__}: {exc}",
                        )
                    )
                    self.bus.publish(DoneEvent(task_id=task.id, outcome="failed"))

            handle.thread = threading.Thread(target=target, name=f"ulei-{task.id}", daemon=True)
            handle.thread.start()

    def cancel(self, task_id: str) -> None:
        with self._lock:
            handle = self._runs.get(task_id)
            if handle is None or not handle.alive():
                raise HTTPException(status_code=409, detail="not_running")
            handle.cancel.set()


def _default_runner(task, publish, cancel, timeout_s) -> None:
    engine_runner(
        task,
        publish,
        cancel,
        timeout_s,
        api_keys=load_keys_from_env(),
        config=None,
    )


def create_app(
    config_path: str | Path | None = None,
    config: dict | None = None,
    runner: Callable | None = None,
    models: ModelSource | None = None,
) -> FastAPI:
    cfg = config if config is not None else load_hive_config(config_path)
    engine = Engine(cfg, runner=runner, models=models)
    app = FastAPI(title="Улей", version=CONTRACT_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.engine = engine

    @app.get("/api/v1/health")
    def health() -> dict:
        return {"status": "ok", "version": CONTRACT_VERSION, "service": "ulei"}

    @app.get("/api/v1/agents")
    def agents():
        return [item.model_dump() for item in list_agents(engine.cfg)]

    @app.get("/api/v1/agents/{agent_id}")
    def agent(agent_id: str):
        for item in list_agents(engine.cfg):
            if item.id == agent_id:
                return item.model_dump()
        raise HTTPException(status_code=404, detail="agent_not_found")

    @app.get("/api/v1/swarms")
    def swarms():
        return [item.model_dump() for item in list_swarms(engine.cfg)]

    @app.get("/api/v1/swarms/{swarm_id}")
    def swarm(swarm_id: str):
        for item in list_swarms(engine.cfg):
            if item.id == swarm_id:
                return item.model_dump()
        raise HTTPException(status_code=404, detail="swarm_not_found")

    @app.get("/api/v1/tasks")
    def tasks():
        return [item.model_dump() for item in engine.book.tasks.values()]

    @app.post("/api/v1/tasks", status_code=201)
    def create_task(body: TaskBody):
        try:
            task = engine.book.create(body.text, body.pipeline, body.workspace)
        except KeyError:
            raise HTTPException(status_code=400, detail="unknown_pipeline") from None
        return task.model_dump()

    @app.get("/api/v1/tasks/{task_id}")
    def task(task_id: str):
        found = engine.book.get(task_id)
        if found is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        return found.model_dump()

    @app.post("/api/v1/tasks/{task_id}/run", status_code=202)
    def run_task(task_id: str, body: RunBody | None = None):
        found = engine.book.get(task_id)
        if found is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        engine.start(found, None if body is None else body.timeout_s)
        return {
            "task_id": task_id,
            "events": f"/api/v1/tasks/{task_id}/events",
            "stream": f"/api/v1/tasks/{task_id}/stream",
        }

    @app.post("/api/v1/tasks/{task_id}/cancel", status_code=202)
    def cancel_task(task_id: str):
        if engine.book.get(task_id) is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        engine.cancel(task_id)
        return {"task_id": task_id, "cancelling": True}

    @app.get("/api/v1/tasks/{task_id}/events")
    def events(task_id: str):
        if engine.book.get(task_id) is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        return StreamingResponse(
            _sse(engine.bus.listen(task_id)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.websocket("/api/v1/tasks/{task_id}/stream")
    async def stream(websocket: WebSocket, task_id: str):
        await websocket.accept()
        if engine.book.get(task_id) is None:
            await websocket.close(code=4404)
            return
        try:
            for event in engine.bus.listen(task_id):
                await websocket.send_json(event)
        except WebSocketDisconnect:
            return
        await websocket.close()

    @app.get("/api/v1/models/local")
    def local_models():
        return [item.model_dump() for item in engine.models()]

    return app


def _sse(frames: Iterator[dict]) -> Iterator[str]:
    for frame in frames:
        yield f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"
