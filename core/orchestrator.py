"""
Multi-agent orchestrator: loads config/agents.yaml and runs pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from core.agent_runtime import AgentRuntime

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "agents.yaml"


def load_config(path: Optional[str | Path] = None) -> dict:
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_model(cfg: dict, model_key: str) -> str:
    models = cfg.get("models") or {}
    if model_key in models:
        return models[model_key]
    if "/" in str(model_key):
        return str(model_key)
    return str(model_key)


def provider_of(model_id: str) -> str:
    if model_id.startswith("anthropic"):
        return "anthropic"
    if model_id.startswith("openai"):
        return "openai"
    if model_id.startswith("gemini"):
        return "gemini"
    if model_id.startswith("xai"):
        return "xai"
    if model_id.startswith("deepseek"):
        return "deepseek"
    return "openai"


KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


class Orchestrator:
    """Runs a pipeline of role-agents sequentially, passing context forward."""

    def __init__(
        self,
        workspace: str,
        backup_dir: str,
        api_keys: dict[str, str],
        config: Optional[dict] = None,
        config_path: Optional[str] = None,
        max_steps: int = 30,
        shell_timeout: int = 120,
        log_fn: Optional[Callable[[str], None]] = None,
        overrides: Optional[dict[str, dict]] = None,
        pipeline_name: str = "full",
    ):
        self.cfg = config or load_config(config_path)
        self.workspace = workspace
        self.backup_dir = backup_dir
        self.api_keys = api_keys or {}
        self.max_steps = max_steps
        self.shell_timeout = shell_timeout
        self.log = log_fn or (lambda s: None)
        self.overrides = overrides or {}
        self.pipeline_name = pipeline_name
        self.power = None

    def _agent_cfg(self, agent_id: str) -> dict:
        base = dict((self.cfg.get("agents") or {}).get(agent_id) or {})
        ov = self.overrides.get(agent_id) or {}
        if "enabled" in ov:
            base["enabled"] = ov["enabled"]
        if "model" in ov and ov["model"]:
            base["model"] = ov["model"]
        if "temperature" in ov:
            base["temperature"] = ov["temperature"]
        return base

    def _api_key_for_model(self, model_id: str) -> Optional[str]:
        prov = provider_of(model_id)
        env_key = KEY_ENV.get(prov, "OPENAI_API_KEY")
        return self.api_keys.get(env_key) or None

    def list_pipeline_steps(self) -> list[str]:
        pipelines = self.cfg.get("pipelines") or {}
        pipe = pipelines.get(self.pipeline_name) or pipelines.get("full") or {}
        steps = list(pipe.get("steps") or ["developer"])
        out = []
        for aid in steps:
            ac = self._agent_cfg(aid)
            if ac.get("enabled", True):
                out.append(aid)
        return out or ["developer"]

    def recommendations(self, agent_id: str) -> list[str]:
        rec = (self.cfg.get("recommendations") or {}).get(agent_id) or []
        models = self.cfg.get("models") or {}
        return [models.get(r, r) for r in rec]

    def run(self, task: str) -> str:
        steps = self.list_pipeline_steps()
        self.log(f"=== Pipeline '{self.pipeline_name}': {' → '.join(steps)} ===")

        context_parts: list[str] = []
        reports: list[str] = []
        last_runtime: Optional[AgentRuntime] = None

        for aid in steps:
            ac = self._agent_cfg(aid)
            name = ac.get("name", aid)
            model_key = ac.get("model", "claude_sonnet")
            model_id = resolve_model(self.cfg, model_key)
            temp = float(ac.get("temperature", 0.2))
            tools = ac.get("tools")
            if tools is not None and len(tools) == 0:
                allowed = []
            elif tools is None:
                allowed = None
            else:
                allowed = list(tools)
            system = ac.get("system") or ""

            api_key = self._api_key_for_model(model_id)
            if not api_key:
                msg = f"[SKIP {name}] нет API-ключа для модели {model_id}"
                self.log(msg)
                context_parts.append(msg)
                continue

            self.log(f"\n>>> {name} ({aid}) | model={model_id} | tools={allowed}")
            runtime = AgentRuntime(
                workspace=self.workspace,
                backup_dir=self.backup_dir,
                model=model_id,
                api_key=api_key,
                temperature=temp,
                max_steps=self.max_steps,
                shell_timeout=self.shell_timeout,
                log_fn=self.log,
                system_prompt=system,
                allowed_tools=allowed,
                role_name=name,
            )
            last_runtime = runtime
            ctx = "\n\n".join(context_parts) if context_parts else ""
            result = runtime.run(task, context=ctx)
            reports.append(f"## {name}\n\n{result}")
            summary = result[-3000:] if len(result) > 3000 else result
            context_parts.append(f"Отчёт агента «{name}»:\n{summary}")

        if last_runtime:
            self.power = last_runtime.power

        header = f"# Pipeline: {self.pipeline_name}\n# Steps: {' → '.join(steps)}\n\n"
        return header + "\n\n---\n\n".join(reports)
