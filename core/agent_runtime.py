"""
Agent runtime: LLM + tools (filesystem, shell, remote, power).
Supports role-specific system prompts and tool allow-lists.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from tools.filesystem import WorkspaceFS
from tools.shell import ShellRunner
from tools.remote import RemoteManager, RemoteDevice
from tools.power import PowerManager


DEFAULT_SYSTEM = """Ты локальный агент-разработчик на компьютере пользователя (как Claude Code).

У тебя есть инструменты. Чтобы вызвать инструмент, выведи РОВНО один блок:

```tool
{\"name\": \"ИМЯ_ИНСТРУМЕНТА\", \"args\": {...}}
```

Доступные инструменты перечислены ниже. После finish задача считается завершённой.
Отвечай на русском, кратко объясняй шаги. За один ответ — один инструмент (или finish).
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
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        role_name: str = "agent",
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
        self.role_name = role_name
        self.history: list[dict] = []

        all_tools: dict[str, Callable] = {
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

        if allowed_tools is None:
            self._tools = all_tools
        else:
            names = set(allowed_tools) | {"finish"}
            self._tools = {k: v for k, v in all_tools.items() if k in names}

        tool_list = "\n".join(f"- {n}" for n in self._tools if n != "finish")
        tool_list += "\n- finish — {\"summary\": \"...\"}"

        base = system_prompt or DEFAULT_SYSTEM
        self.system_prompt = (
            base.strip()
            + "\n\nФормат вызова инструмента:\n```tool\n{\"name\": \"...\", \"args\": {...}}\n```\n"
            + f"\nДоступные инструменты:\n{tool_list}\n"
        )

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
        m = re.search(r"```tool\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        m = re.search(r"\{[^{}]*\"name\"\s*:\s*\"[^\"]+\"[^{}]*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def run(self, task: str, context: str = "") -> str:
        user_content = f"Задача:\n{task}\n\nWorkspace: {self.fs.root}\n"
        if context:
            user_content += f"\n--- Контекст от предыдущих агентов ---\n{context}\n"
        user_content += "\nНачни работу. Если инструментов нет — сразу finish с итогом."

        self.history = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        final_parts: list[str] = []

        only_finish = set(self._tools.keys()) <= {"finish"}
        max_steps = 1 if only_finish else self.max_steps

        for step in range(1, max_steps + 1):
            self.log(f"[{self.role_name}] шаг {step}/{max_steps}")
            reply = self._llm(self.history)
            self.history.append({"role": "assistant", "content": reply})
            final_parts.append(reply)
            self.log(reply[:500])

            tool_call = self._parse_tool(reply)
            if not tool_call:
                if only_finish:
                    return "\n\n".join(final_parts)
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
            self.log(f"[{self.role_name}] TOOL: {name} {args}")

            if name == "finish":
                summary = self._tools["finish"](args)
                self.log(f"[{self.role_name}] FINISH: {summary}")
                return "\n\n".join(final_parts) + f"\n\n=== ИТОГ ({self.role_name}) ===\n{summary}"

            if name not in self._tools:
                result = f"Unknown tool: {name}. Available: {list(self._tools.keys())}"
            else:
                try:
                    result = self._tools[name](args)
                except Exception as e:
                    result = f"Tool error: {e}"

            self.log(f"[{self.role_name}] RESULT: {str(result)[:800]}")
            self.history.append(
                {
                    "role": "user",
                    "content": f"Результат инструмента {name}:\n{result}",
                }
            )

        return "\n\n".join(final_parts) + f"\n\n[{self.role_name}: лимит шагов]"
