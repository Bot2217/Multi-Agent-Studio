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
