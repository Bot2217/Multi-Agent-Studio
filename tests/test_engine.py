"""Engine v2 runs independent agents together and stops cleanly."""

import threading

from contracts.v1 import Task
from core.engine import AgentJob, SwarmEngine, jobs_from_pipeline
from core.orchestrator import load_config


def _run(execute, jobs, cancel=None, timeout_s=None, agent_timeout_s=5):
    seen = []
    engine = SwarmEngine(execute, agent_timeout_s=agent_timeout_s)
    engine.run("task_0001", "custom", jobs, seen.append, cancel or threading.Event(), timeout_s)
    return seen


def test_independent_agents_run_together():
    barrier = threading.Barrier(2)

    def execute(job, context, should_stop):
        barrier.wait(2)
        return job.id

    jobs = [AgentJob("alpha", "Alpha", 0), AgentJob("beta", "Beta", 0)]
    seen = _run(execute, jobs)
    assert [event.type for event in seen if event.type == "step"] == ["step", "step"]
    assert seen[-1].type == "done"
    assert seen[-1].outcome == "ok"
    assert "alpha" in seen[-1].result and "beta" in seen[-1].result


def test_later_wave_sees_the_previous_report():
    seen_calls = []

    def execute(job, context, should_stop):
        seen_calls.append((job.id, context))
        return f"made by {job.id}"

    jobs = [AgentJob("alpha", "Alpha", 0), AgentJob("beta", "Beta", 1)]
    seen = _run(execute, jobs)
    assert [item[0] for item in seen_calls] == ["alpha", "beta"]
    assert "made by alpha" in seen_calls[1][1]
    assert seen[0].type == "start"
    assert seen[0].agents == ["alpha", "beta"]
    assert seen[-1].outcome == "ok"


def test_timeout_skips_the_next_wave():
    def execute(job, context, should_stop):
        if job.id == "slow":
            while not should_stop():
                threading.Event().wait(0.02)
            return "late"
        return "fast"

    jobs = [
        AgentJob("fast", "Fast", 0),
        AgentJob("slow", "Slow", 0),
        AgentJob("later", "Later", 1),
    ]
    seen = _run(execute, jobs, agent_timeout_s=0.15)
    codes = [event.code for event in seen if event.type == "error"]
    assert "timeout" in codes
    assert seen[-1].outcome == "failed"
    assert "fast" in seen[-1].result
    assert "Later" not in seen[-1].result


def test_cancel_before_start():
    called = []

    def execute(job, context, should_stop):
        called.append(job.id)
        return "no"

    cancel = threading.Event()
    cancel.set()
    seen = _run(execute, [AgentJob("alpha", "Alpha", 0)], cancel=cancel)
    assert called == []
    assert any(event.type == "error" and event.code == "cancelled" for event in seen)
    assert seen[-1].outcome == "stopped"


def test_one_failure_is_a_clear_error():
    def execute(job, context, should_stop):
        if job.id == "bad":
            raise RuntimeError("disk full")
        return "ok"

    jobs = [AgentJob("bad", "Bad", 0), AgentJob("next", "Next", 1)]
    seen = _run(execute, jobs)
    error = next(event for event in seen if event.type == "error")
    assert error.code == "agent_failed"
    assert error.agent_id == "bad"
    assert "disk full" in error.message
    assert seen[-1].outcome == "failed"
    assert "Next" not in seen[-1].result


def test_waves_in_config_skip_disabled_roles():
    cfg = {
        "pipelines": {
            "review": {
                "steps": ["developer", "reviewer", "tester"],
                "waves": [["developer"], ["reviewer", "tester"]],
            }
        }
    }

    def title_of(agent_id: str):
        if agent_id == "tester":
            return None
        return agent_id

    jobs = jobs_from_pipeline(cfg, "review", title_of)
    assert [(job.id, job.wave) for job in jobs] == [("developer", 0), ("reviewer", 1)]
    sequential = jobs_from_pipeline(
        {"pipelines": {"single": {"steps": ["developer"]}}},
        "single",
        lambda agent_id: agent_id,
    )
    assert [job.wave for job in sequential] == [0]


def test_http_run_uses_the_engine(monkeypatch, tmp_path):
    names = []

    class FakeRuntime:
        def __init__(self, **kwargs):
            names.append(kwargs["role_name"])

        def run(self, task, context=""):
            return f"done:{task}"

    monkeypatch.setattr("api.runner.AgentRuntime", FakeRuntime)
    monkeypatch.setattr("api.app.load_keys_from_env", lambda: {"GOOGLE_API_KEY": "test-key"})
    from fastapi.testclient import TestClient

    from api.app import create_app

    client = TestClient(create_app(config=load_config()))
    created = client.post(
        "/api/v1/tasks",
        json={"text": "hello", "pipeline": "code_only", "workspace": str(tmp_path)},
    )
    task_id = created.json()["id"]
    assert client.post(f"/api/v1/tasks/{task_id}/run", json={}).status_code == 202
    body = client.get(f"/api/v1/tasks/{task_id}/events").text
    assert '"type": "done"' in body or '"type":"done"' in body
    assert "Разработчик" in names and "Ревьюер" in names
    Task.model_validate(created.json())
