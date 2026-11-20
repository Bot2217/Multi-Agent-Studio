"""MCP client for stdio and HTTP servers.

The framing follows the Model Context Protocol: JSON-RPC 2.0, and for stdio
a Content-Length header like the language server protocol.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml


@dataclass
class McpServer:
    name: str
    transport: str
    command: str = ""
    args: tuple[str, ...] = ()
    url: str = ""


@dataclass
class McpTool:
    name: str
    description: str = ""


class McpError(RuntimeError):
    pass


def load_mcp_config(path: Path | None) -> dict[str, McpServer]:
    if path is None or not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    servers: dict[str, McpServer] = {}
    raw = data.get("servers") or {}
    if not isinstance(raw, dict):
        return {}
    for name, item in raw.items():
        if not isinstance(item, dict):
            continue
        transport = str(item.get("transport") or "stdio")
        servers[str(name)] = McpServer(
            name=str(name),
            transport=transport,
            command=str(item.get("command") or ""),
            args=tuple(str(part) for part in (item.get("args") or [])),
            url=str(item.get("url") or ""),
        )
    return servers


class McpClient:
    def __init__(self, request: Callable[[dict], dict]):
        self._request = request
        self._next = 1
        self._open = False

    def _rpc(self, method: str, params: dict | None = None, *, notify: bool = False) -> dict:
        message: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notify:
            message["id"] = self._next
            self._next += 1
        response = self._request(message)
        if notify:
            return {}
        if not isinstance(response, dict):
            raise McpError("mcp response is not an object")
        if response.get("error"):
            raise McpError(str(response["error"]))
        result = response.get("result")
        return result if isinstance(result, dict) else {}

    def start(self) -> None:
        if self._open:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ulei", "version": "0.2.0"},
            },
        )
        self._rpc("notifications/initialized", notify=True)
        self._open = True

    def list_tools(self) -> list[McpTool]:
        self.start()
        result = self._rpc("tools/list", {})
        tools = []
        for item in result.get("tools") or []:
            if isinstance(item, dict) and item.get("name"):
                tools.append(McpTool(str(item["name"]), str(item.get("description") or "")))
        return tools

    def call(self, name: str, arguments: dict) -> str:
        self.start()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        parts = []
        for block in result.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        if parts:
            return "\n".join(parts)
        return json.dumps(result, ensure_ascii=False)


def stdio_request(process: subprocess.Popen):
    def request(message: dict) -> dict:
        if process.stdin is None or process.stdout is None:
            raise McpError("stdio pipes are closed")
        body = json.dumps(message).encode("utf-8")
        process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
        process.stdin.flush()
        if message.get("id") is None:
            return {}
        return _read_frame(process.stdout)

    return request


def _read_frame(stream) -> dict:
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            raise McpError("stdio closed")
        if line in {b"\r\n", b"\n"}:
            break
        key, _, value = line.decode("ascii", errors="replace").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length") or 0)
    payload = stream.read(length) if length else b""
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise McpError("stdio frame is not an object")
    return data


def http_request(url: str, post: Callable[[str, dict], tuple[int, bytes]]):
    def request(message: dict) -> dict:
        if message.get("id") is None:
            post(url, message)
            return {}
        status, payload = post(url, message)
        if status >= 400:
            raise McpError(f"mcp http {status}")
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            raise McpError("mcp http body is not an object")
        return data

    return request


def open_client(server: McpServer, *, popen=None, post=None) -> McpClient:
    if server.transport == "stdio":
        if not server.command:
            raise McpError(f"{server.name}: stdio server has no command")
        spawn = popen or subprocess.Popen
        process = spawn(
            [server.command, *server.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        client = McpClient(stdio_request(process))
        client.process = process
        return client
    if server.transport == "http":
        if not server.url:
            raise McpError(f"{server.name}: http server has no url")
        if post is None:
            post = _urllib_post
        return McpClient(http_request(server.url, post))
    raise McpError(f"{server.name}: unknown transport {server.transport}")


def _urllib_post(url: str, message: dict) -> tuple[int, bytes]:
    from urllib.request import Request, urlopen

    body = json.dumps(message).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return response.status, response.read()


def tool_callables(server_name: str, client: McpClient) -> dict[str, Callable[[dict], str]]:
    tools = {}
    for tool in client.list_tools():
        tool_name = tool.name

        def call(args: dict, _name=tool_name, _client=client) -> str:
            return _client.call(_name, args if isinstance(args, dict) else {})

        tools[f"mcp_{server_name}_{tool.name}"] = call
    return tools
