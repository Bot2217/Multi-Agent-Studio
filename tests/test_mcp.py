"""MCP stdio and HTTP clients speak JSON-RPC without a live server."""

import json
import textwrap
from pathlib import Path

from core.mcp_client import McpServer, http_request, load_mcp_config, open_client, tool_callables

STDIO_SERVER = textwrap.dedent(
    """
    import json, sys

    def read_message():
        headers = {}
        while True:
            line = sys.stdin.buffer.readline()
            if line in (b"\\r\\n", b"\\n", b""):
                break
            key, _, value = line.decode().partition(":")
            headers[key.strip().lower()] = value.strip()
        length = int(headers.get("content-length") or 0)
        return json.loads(sys.stdin.buffer.read(length).decode())

    def write_message(payload):
        body = json.dumps(payload).encode()
        sys.stdout.buffer.write(f"Content-Length: {len(body)}\\r\\n\\r\\n".encode() + body)
        sys.stdout.buffer.flush()

    while True:
        try:
            message = read_message()
        except Exception:
            break
        method = message.get("method")
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "fake", "version": "0"}}
        elif method == "tools/list":
            result = {"tools": [{"name": "echo", "description": "Echo"}]}
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": message["params"]["arguments"].get("text", "")}]}
        else:
            result = {}
        write_message({"jsonrpc": "2.0", "id": message.get("id"), "result": result})
    """
)


def test_stdio_lists_and_calls(tmp_path):
    script = tmp_path / "server.py"
    script.write_text(STDIO_SERVER, encoding="utf-8")
    server = McpServer("local", "stdio", command="python3", args=(str(script),))
    client = open_client(server)
    try:
        tools = tool_callables("local", client)
        assert list(tools) == ["mcp_local_echo"]
        assert tools["mcp_local_echo"]({"text": "привет"}) == "привет"
    finally:
        client.process.kill()
        client.process.wait(timeout=5)


def test_http_client_uses_the_injected_post():
    seen = []

    def post(url, message):
        seen.append((url, message["method"]))
        if message["method"] == "initialize":
            body = {"jsonrpc": "2.0", "id": message["id"], "result": {"capabilities": {}}}
        elif message["method"] == "tools/list":
            body = {"jsonrpc": "2.0", "id": message["id"], "result": {"tools": [{"name": "ping"}]}}
        else:
            body = {
                "jsonrpc": "2.0",
                "id": message.get("id", 1),
                "result": {"content": [{"type": "text", "text": "pong"}]},
            }
        return 200, json.dumps(body).encode()

    from core.mcp_client import McpClient

    client = McpClient(http_request("http://127.0.0.1:9/mcp", post))
    assert client.call("ping", {}) == "pong"
    assert [item[1] for item in seen] == ["initialize", "notifications/initialized", "tools/call"]


def test_agent_keeps_mcp_tools_beside_its_allow_list():
    from core.agent_runtime import AgentRuntime

    runtime = AgentRuntime(
        workspace=".",
        backup_dir=".",
        allowed_tools=["read_file"],
        extra_tools={"mcp_local_echo": lambda args: args.get("text", "")},
    )
    assert "mcp_local_echo" in runtime._tools
    assert "read_file" in runtime._tools
    assert "run_shell" not in runtime._tools


def test_load_config_and_reject_unknown_transport(tmp_path: Path):
    path = tmp_path / "mcp.yaml"
    path.write_text(
        "servers:\n  docs:\n    transport: http\n    url: http://127.0.0.1:9/mcp\n",
        encoding="utf-8",
    )
    loaded = load_mcp_config(path)
    assert loaded["docs"].url.endswith("/mcp")
    assert load_mcp_config(tmp_path / "missing.yaml") == {}
    try:
        open_client(McpServer("x", "carrier-pigeon"))
    except Exception as exc:
        assert "unknown transport" in str(exc)
    else:
        raise AssertionError("expected a transport error")
