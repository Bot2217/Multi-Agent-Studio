"""
Agent runtime: LLM + tools (filesystem, shell, remote, power).
Works with litellm / OpenAI-compatible API.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Optional

from tools.filesystem import WorkspaceFS
from tools.shell import ShellRunner
from tools.remote import RemoteManager, RemoteDevice
from tools.power import PowerManager


SYSTEM_PROMPT = """Ты локальный агент-разработчик на компьютере пользователя (как Claude Code).

У тебя есть инструменты. Чтобы вызвать инструмент, выведи РОВНО один блок:

```tool
{"name": "ИМЯ_ИНСТРУМЕНТА", "args": {...}}
```

Доступные инструменты:

1. list_dir — {"path": "."}
2. read_file — {"path": "file.py"}
3. write_file — {"path": "file.py", "content": "..."}  (перед записью делается backup)
4. append_file — {"path": "file.py", "content": "..."}
5. delete_path — {"path": "file.py"}  (с backup)
6. move_path — {"src": "a", "dst": "b"}
7. copy_path — {"src": "a", "dst": "b"}
8. search_text — {"pattern": "foo", "path": "."}
9. run_shell — {"command": "ls -la", "cwd": null}
10. remote_list — {}
11. remote_add — {"name": "pi", "host": "192.168.1.10", "user": "pi", "port": 22, "key_path": null}
12. remote_run — {"name": "pi", "command": "uptime"}
13. remote_ping — {"name": "pi"}
14. power_status — {}
15. power_start — {"mode": "system"}  // system | display
16. power_stop — {}
17. finish — {"summary": "что сделано"}

Правила:
- Работай только внутри workspace, если не сказано иное.
- Перед удалением/перезаписью система сама делает backup.
- Опасные shell-команды блокируются.
- После finish задача считается завершённой.
- Отвечай на русском, кратко объясняй шаги.
- За один ответ вызывай один инструмент (или finish).
"""


class AgentRuntime:
    def __init__(
        self,
        workspace: str,
        backup_dir: str,
        model: str = "anthropic/claude-sonnet-4-5",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_steps: int = 40,
        shell_timeout: int = 120,
        log_fn: Optional[Callable[[str], None]] = None,
    ):
        self.fs = WorkspaceFS(workspace, backup_dir)
        self.shell = ShellRunner(cwd=workspace, timeout=shell_timeout)
        self.remote = RemoteManager()
        self.power = PowerManager()
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_steps = max_steps
        self.log = log_fn or (lambda s: None)
        self.history: list[dict] = []
        self._tools = {
            "list_dir": lambda a: self.fs.list_dir(a.get("path", ".")),
            "read_file": lambda a: self.fs.read_file(a["path"]),
            "write_file": lambda a: self.fs.write_file(a["path"], a["content"]),
            "append_file": lambda a: self.fs.append_file(a["path"], a["content"]),
            "delete_path": lambda a: self.fs.delete_path(a["path"]),
            "move_path": lambda a: self.fs.move_path(a["src"], a["dst"]),
            "copy_path": lambda a: self.fs.copy_path(a["src"], a["dst"]),
            "search_text": lambda a: self.fs.search_text(a["pattern"], a.get("path", ".")),
            "run_shell": lambda a: self.shell.run(a["command"], a.get("cwd")),
            "remote_list": lambda a: self.remote.list_devices(),
            "remote_add": lambda a: self.remote.add_device(
                RemoteDevice(
                    name=a["name"],
                    host=a["host"],
                    user=a.get("user", "root"),
                    port=int(a.get("port", 22)),
                    key_path=a.get("key_path"),
                    password=a.get("password"),
                )
            ),
            "remote_run": lambda a: self.remote.run_ssh(a["name"], a["command"]),
            "remote_ping": lambda a: self.remote.ping(a["name"]),
            "power_status": lambda a: self.power.status,
            "power_start": lambda a: self.power.start(a.get("mode", "system")),
            "power_stop": lambda a: self.power.stop(),
            "finish": lambda a: a.get("summary", "Done"),
        }

    def _llm(self, messages: list[dict]) -> str:
        try:
            from litellm import completion
        except ImportError:
            raise RuntimeError("pip install litellm")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url

        resp = completion(**kwargs)
        return resp.choices[0].message.content or ""

    def _parse_tool(self, text: str) -> Optional[dict]:
        # ```tool ... ```
        m = re.search(r"```tool\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # bare json with name
        m = re.search(r"\{[^{}]*\"name\"\s*:\s*\"[^\"]+\"[^{}]*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def run(self, task: str) -> str:
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Задача:\n{task}\n\n"
                    f"Workspace: {self.fs.root}\n"
                    f"Начни работу. Сначала при необходимости осмотри файлы."
                ),
            },
        ]
        final_parts = []

        for step in range(1, self.max_steps + 1):
            self.log(f"--- шаг {step}/{self.max_steps} ---")
            reply = self._llm(self.history)
            self.history.append({"role": "assistant", "content": reply})
            final_parts.append(reply)
            self.log(reply[:500])

            tool_call = self._parse_tool(reply)
            if not tool_call:
                # no tool — ask to continue or finish
                self.history.append(
                    {
                        "role": "user",
                        "content": (
                            "Если задача не завершена — вызови следующий инструмент. "
                            "Если всё сделано — вызови finish."
                        ),
                    }
                )
                continue

            name = tool_call.get("name", "")
            args = tool_call.get("args") or tool_call.get("arguments") or {}
            self.log(f"TOOL: {name} {args}")

            if name == "finish":
                summary = self._tools["finish"](args)
                self.log(f"FINISH: {summary}")
                return "\n\n".join(final_parts) + f"\n\n=== ИТОГ ===\n{summary}"

            if name not in self._tools:
                result = f"Unknown tool: {name}. Available: {list(self._tools.keys())}"
            else:
                try:
                    result = self._tools[name](args)
                except Exception as e:
                    result = f"Tool error: {e}"

            self.log(f"RESULT: {str(result)[:800]}")
            self.history.append(
                {
                    "role": "user",
                    "content": f"Результат инструмента {name}:\n{result}",
                }
            )

        return "\n\n".join(final_parts) + "\n\n[Достигнут лимит шагов]"
