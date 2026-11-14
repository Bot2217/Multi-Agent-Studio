"""HTTP engine: contract entities and a start/step/log/error/done stream."""

import json
import threading
import time

from fastapi.testclient import TestClient

from api.app import create_app
from api.runner import orchestrator_runner
from contracts.v1 import DoneEvent, LogEvent, StartEvent, StepEvent, parse_event
from core.orchestrator import RunStopped, load_config


def _client(runner=None, models=None) -> TestClient:
    app = create_app(config=load_config(), runner=runner, models=models)
    return TestClient(app)


def _task(client: TestClient, pipeline: str = "single") -> str:
    response = client.post(
        "/api/v1/tasks",
        json={"text": "напиши hello", "pipeline": pipeline, "workspace": "/tmp/ulei-test"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _frames(client: TestClient, task_id: str) -> list[dict]:
    response = client.get(f"/api/v1/tasks/{task_id}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            frames.append(json.loads(line[len("data: ") :]))
    return frames


def test_health_agents_and_swarms():
    client = _client()
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": "1", "service": "ulei"}

    agents = client.get("/api/v1/agents").json()
    developer = next(item for item in agents if item["id"] == "developer")
    assert developer["name"] == "Разработчик"
    assert developer["model"]
    assert client.get("/api/v1/agents/missing").status_code == 404

    swarms = client.get("/api/v1/swarms").json()
    code_only = next(item for item in swarms if item["id"] == "code_only")
    assert code_only["steps"] == ["developer", "reviewer"]
    assert client.get("/api/v1/swarms/missing").status_code == 404


def test_unknown_pipeline_is_rejected():
    client = _client()
    response = client.post(
        "/api/v1/tasks",
        json={"text": "x", "pipeline": "nope", "workspace": "/tmp"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "unknown_pipeline"


def test_sse_and_websocket_replay_contract_events():
    def runner(task, publish, cancel, timeout_s):
        publish(StartEvent(task_id=task.id, pipeline=task.pipeline, agents=["developer"]))
        publish(
            StepEvent(
                task_id=task.id,
                index=1,
                total=1,
                agent_id="developer",
                title="Разработчик",
            )
        )
        publish(LogEvent(task_id=task.id, agent_id="developer", text="пишу файл"))
        publish(DoneEvent(task_id=task.id, outcome="ok", result="готово"))

    client = _client(runner)
    task_id = _task(client)
    started = client.post(f"/api/v1/tasks/{task_id}/run", json={})
    assert started.status_code == 202
    assert started.json()["events"].endswith("/events")

    frames = _frames(client, task_id)
    assert [parse_event(frame).type for frame in frames] == ["start", "step", "log", "done"]
    assert frames[-1]["outcome"] == "ok"
    assert frames[-1]["version"] == "1"

    with client.websocket_connect(f"/api/v1/tasks/{task_id}/stream") as socket:
        kinds = []
        while True:
            frame = socket.receive_json()
            kinds.append(parse_event(frame).type)
            if frame["type"] == "done":
                break
    assert kinds == ["start", "step", "log", "done"]


def test_cancel_stops_the_run():
    entered = threading.Event()

    def runner(task, publish, cancel, timeout_s):
        publish(StartEvent(task_id=task.id, pipeline=task.pipeline, agents=["developer"]))
        entered.set()
        while not cancel.wait(0.02):
            pass
        publish(DoneEvent(task_id=task.id, outcome="stopped", result=""))

    client = _client(runner)
    task_id = _task(client)
    assert client.post(f"/api/v1/tasks/{task_id}/cancel").status_code == 409
    assert client.post(f"/api/v1/tasks/{task_id}/run").status_code == 202
    assert entered.wait(2)
    assert client.post(f"/api/v1/tasks/{task_id}/run").status_code == 409
    cancelled = client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancelled.status_code == 202
    frames = _frames(client, task_id)
    assert frames[-1]["type"] == "done"
    assert frames[-1]["outcome"] == "stopped"


def test_orchestrator_runner_emits_failure(tmp_path, monkeypatch):
    class Boom:
        def __init__(self, **_kwargs):
            pass

        def run(self, task, context=""):
            raise RuntimeError("model exploded")

    monkeypatch.setattr("core.orchestrator.AgentRuntime", Boom)
    from contracts.v1 import Task

    task = Task(id="task_0001", text="hello", pipeline="single", workspace=str(tmp_path))
    seen = []
    orchestrator_runner(
        task,
        seen.append,
        threading.Event(),
        api_keys={"GOOGLE_API_KEY": "test"},
        config=load_config(),
    )
    kinds = [event.type for event in seen]
    assert kinds[0] == "start"
    assert "step" in kinds
    assert "error" in kinds
    assert kinds[-1] == "done"
    assert seen[-1].outcome == "failed"
    assert seen[-2].code == "agent_failed"


def test_orchestrator_runner_timeout(tmp_path, monkeypatch):
    class Slow:
        def __init__(self, **kwargs):
            self.should_stop = kwargs["should_stop"]

        def run(self, task, context=""):
            while not self.should_stop():
                time.sleep(0.01)
            raise RunStopped()

    monkeypatch.setattr("core.orchestrator.AgentRuntime", Slow)
    from contracts.v1 import Task

    task = Task(id="task_0002", text="hello", pipeline="single", workspace=str(tmp_path))
    seen = []
    orchestrator_runner(
        task,
        seen.append,
        threading.Event(),
        timeout_s=0.05,
        api_keys={"GOOGLE_API_KEY": "test"},
        config=load_config(),
    )
    assert seen[-2].type == "error"
    assert seen[-2].code == "timeout"
    assert seen[-1].outcome == "failed"


def test_local_model_status_endpoint():
    from contracts.v1 import LocalModelStatus

    def models():
        return [
            LocalModelStatus(
                name="llama3.2:3b",
                state="downloading",
                progress=0.4,
                completed=4,
                total=10,
                message="pulling",
            )
        ]

    client = _client(models=models)
    payload = client.get("/api/v1/models/local").json()
    assert payload[0]["name"] == "llama3.2:3b"
    assert payload[0]["state"] == "downloading"
    LocalModelStatus.model_validate(payload[0])


def test_missing_task_stream_is_404():
    client = _client()
    assert client.get("/api/v1/tasks/task_9999").status_code == 404
    assert client.get("/api/v1/tasks/task_9999/events").status_code == 404
    with client.websocket_connect("/api/v1/tasks/task_9999/stream") as socket:
        message = socket.receive()
    assert message["type"] == "websocket.close"
    assert message["code"] == 4404
