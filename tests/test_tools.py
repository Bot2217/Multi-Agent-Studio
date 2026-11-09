from core.agent_runtime import AgentRuntime
from tools.filesystem import WorkspaceFS
from tools.shell import ShellRunner


def test_tool_block_parser(tmp_path):
    runtime = AgentRuntime(str(tmp_path), str(tmp_path / "backups"), api_key="x")
    parsed = runtime._parse_tool(
        'Сначала мысль.\n```tool\n{"name": "finish", "args": {"summary": "ok"}}\n```'
    )
    assert parsed["name"] == "finish"
    assert parsed["args"]["summary"] == "ok"
    assert runtime._parse_tool("без инструмента") is None
    assert runtime._parse_tool("```tool\n{broken}\n```") is None


def test_finish_only_role_stops_after_one_reply(tmp_path, monkeypatch):
    runtime = AgentRuntime(
        str(tmp_path),
        str(tmp_path / "backups"),
        api_key="x",
        allowed_tools=[],
        role_name="менеджер",
    )
    calls = {"n": 0}

    def fake_llm(_messages):
        calls["n"] += 1
        return "План готов, инструментов нет."

    monkeypatch.setattr(runtime, "_llm", fake_llm)
    result = runtime.run("разбей задачу")
    assert "План готов" in result
    assert calls["n"] == 1


def test_workspace_roundtrip_and_backup(tmp_path):
    root = tmp_path / "workspace"
    backups = tmp_path / "backups"
    fs = WorkspaceFS(root, backups)
    assert "Written" in fs.write_file("notes/a.txt", "one")
    assert fs.read_file("notes/a.txt") == "one"
    assert "Backup" in fs.write_file("notes/a.txt", "two")
    assert fs.read_file("notes/a.txt") == "two"
    assert any(backups.iterdir())
    assert "a.txt" in fs.list_dir("notes")
    assert "No matches" not in fs.search_text("two")


def test_workspace_rejects_sibling_prefix(tmp_path):
    root = tmp_path / "workspace"
    sibling = tmp_path / "workspace_evil"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("nope", encoding="utf-8")
    fs = WorkspaceFS(root, tmp_path / "backups")
    try:
        fs.read_file(str(sibling / "secret.txt"))
    except PermissionError:
        return
    raise AssertionError("sibling directory with a shared prefix must stay outside the workspace")


def test_shell_blocks_dangerous_pattern_and_runs_echo(tmp_path):
    runner = ShellRunner(tmp_path, timeout=10)
    blocked = runner.run("echo ok && rm -rf /")
    assert blocked.startswith("Blocked")
    output = runner.run("echo studio")
    assert "studio" in output
    assert "exit code: 0" in output
