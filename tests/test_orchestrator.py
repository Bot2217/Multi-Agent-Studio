from core.orchestrator import Orchestrator, load_config, resolve_model


def test_pipeline_respects_disabled_roles(tmp_path):
    cfg = load_config()
    orch = Orchestrator(
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={},
        config=cfg,
        pipeline_name="code_only",
        overrides={"reviewer": {"enabled": False}},
    )
    assert orch.list_pipeline_steps() == ["developer"]


def test_run_skips_hosted_model_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.orchestrator.AgentRuntime",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("no")),
    )
    cfg = load_config()
    orch = Orchestrator(
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={},
        config=cfg,
        pipeline_name="single",
    )
    result = orch.run("сделай hello.py")
    assert "нет API-ключа" in result
    assert "gemini/gemini-3.8-flash" in result


def test_run_passes_resolved_model(tmp_path, monkeypatch):
    captured = {}

    class FakeRuntime:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.power = None

        def run(self, task, context=""):
            assert "hello" in task
            return "готово"

    monkeypatch.setattr("core.orchestrator.AgentRuntime", FakeRuntime)
    cfg = load_config()
    orch = Orchestrator(
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={"GOOGLE_API_KEY": "test-key"},
        config=cfg,
        pipeline_name="single",
    )
    result = orch.run("hello")
    assert "готово" in result
    assert captured["model"] == "gemini/gemini-3.8-flash"
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] is None


def test_local_model_does_not_need_a_key(tmp_path, monkeypatch):
    captured = {}

    class FakeRuntime:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.power = None

        def run(self, task, context=""):
            return "local"

    monkeypatch.setattr("core.orchestrator.AgentRuntime", FakeRuntime)
    cfg = load_config()
    orch = Orchestrator(
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={},
        config=cfg,
        pipeline_name="single",
        overrides={"developer": {"enabled": True, "model": "ollama_gemma4"}},
    )
    result = orch.run("hi")
    assert "local" in result
    assert captured["model"] == "ollama_chat/gemma4"
    assert captured["base_url"] == "http://localhost:11434"


def test_recommendations_resolve_to_litellm_ids():
    cfg = load_config()
    orch = Orchestrator(
        workspace=".",
        backup_dir="backups",
        api_keys={},
        config=cfg,
        pipeline_name="single",
    )
    ids = orch.recommendations("developer")
    assert "gemini/gemini-3.8-flash" in ids
    assert resolve_model(cfg, "grok_47") == "xai/grok-4.7"


def _fake_runtime(behaviour):
    class FakeRuntime:
        def __init__(self, **kwargs):
            self.name = kwargs["role_name"]

        def run(self, task, context=""):
            return behaviour(self.name, context)

    return FakeRuntime


def test_failing_role_keeps_earlier_reports(tmp_path, monkeypatch):
    def behaviour(name, context):
        if name == "Ревьюер":
            raise RuntimeError("квота кончилась")
        return "код написан"

    monkeypatch.setattr("core.orchestrator.AgentRuntime", _fake_runtime(behaviour))
    orch = Orchestrator(
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={"GOOGLE_API_KEY": "k"},
        config=load_config(),
        pipeline_name="code_only",
    )
    result = orch.run("hello")
    assert orch.outcome == "failed"
    assert "код написан" in result
    assert "квота кончилась" in result


def test_stop_between_roles(tmp_path, monkeypatch):
    flag = {"stop": False}

    def behaviour(name, context):
        flag["stop"] = True
        return "первый шаг"

    monkeypatch.setattr("core.orchestrator.AgentRuntime", _fake_runtime(behaviour))
    orch = Orchestrator(
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={"GOOGLE_API_KEY": "k"},
        config=load_config(),
        pipeline_name="code_only",
        should_stop=lambda: flag["stop"],
    )
    result = orch.run("hello")
    assert orch.outcome == "stopped"
    assert "первый шаг" in result
    assert "Ревьюер" not in result.split("Steps:")[1].split("\n", 1)[1]


def test_handoff_prefers_the_role_summary():
    from core.orchestrator import handoff

    long_summary = "=== ИТОГ (Разработчик) ===\n" + "сделано " * 60
    assert handoff("шум " * 5000 + long_summary).startswith("=== ИТОГ")
    assert len(handoff("x" * 20000)) == 6000


def test_run_job_writes_report_and_finishes(tmp_path, monkeypatch):
    from core.runner import RunJob

    monkeypatch.setattr("core.orchestrator.AgentRuntime", _fake_runtime(lambda n, c: "готово"))
    job = RunJob(
        task="hello",
        results_dir=tmp_path / "results",
        workspace=str(tmp_path),
        backup_dir=str(tmp_path / "backups"),
        api_keys={"GOOGLE_API_KEY": "k"},
        config=load_config(),
        pipeline_name="single",
    ).start()
    job.join(10)
    assert job.outcome == "ok"
    assert not job.running
    assert job.step == (1, 1, "Разработчик")
    assert "готово" in job.report_path.read_text(encoding="utf-8")


def test_stop_does_not_wait_for_the_model(tmp_path, monkeypatch):
    import threading
    import time

    import pytest

    from core.agent_runtime import AgentRuntime, RunStopped

    notes: list[str] = []
    started = threading.Event()
    runtime = AgentRuntime(
        str(tmp_path),
        str(tmp_path / "b"),
        api_key="x",
        log_fn=notes.append,
        should_stop=started.is_set,
    )

    def hang(**_kwargs):
        started.set()
        time.sleep(30)

    import sys
    import types

    fake = types.ModuleType("litellm")
    fake.completion = hang
    monkeypatch.setitem(sys.modules, "litellm", fake)
    began = time.monotonic()
    with pytest.raises(RunStopped):
        runtime._llm([{"role": "user", "content": "hi"}])
    assert time.monotonic() - began < 3
    assert any("уже отправлен" in line for line in notes)


def test_agent_stops_when_asked(tmp_path):
    import pytest

    from core.agent_runtime import AgentRuntime, RunStopped

    runtime = AgentRuntime(
        str(tmp_path), str(tmp_path / "b"), api_key="x", should_stop=lambda: True
    )
    with pytest.raises(RunStopped):
        runtime.run("задача")
