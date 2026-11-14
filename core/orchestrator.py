"""
Multi-agent orchestrator: loads config/agents.yaml and runs pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import yaml

from core.agent_runtime import AgentRuntime, RunStopped
from core.catalog import KEY_ENV, api_base_for, load_models_catalog, provider_of
from core.catalog import resolve_model as resolve_catalog_model
from core.i18n import t

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "agents.yaml"


def load_config(path: Optional[str | Path] = None) -> dict:
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_model(cfg: dict, model_key: str, catalog: Optional[dict] = None) -> str:
    if catalog is None:
        catalog = load_models_catalog()
    return resolve_catalog_model(model_key, cfg, catalog)


HANDOFF_LIMIT = 6000


def handoff(result: str) -> str:
    """What the next role sees: the role's own summary when it wrote one, else the tail."""
    marker = "=== ИТОГ"
    if marker in result:
        summary = result[result.rindex(marker) :]
        if len(summary) > 200:
            return summary[:HANDOFF_LIMIT]
    return result[-HANDOFF_LIMIT:]


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
        should_stop: Optional[Callable[[], bool]] = None,
        step_fn: Optional[Callable[[int, int, str], None]] = None,
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
        self.should_stop = should_stop or (lambda: False)
        self.step_fn = step_fn or (lambda index, total, name: None)
        # "ok", "failed" (a role raised) or "stopped" (the user asked to stop)
        self.outcome = "ok"
        self.catalog = load_models_catalog()

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
        if prov == "ollama":
            return self.api_keys.get("OLLAMA_API_KEY") or "ollama"
        env_key = KEY_ENV.get(prov)
        if not env_key:
            return None
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
        return [resolve_model(self.cfg, r, self.catalog) for r in rec]

    def run(self, task: str) -> str:
        steps = self.list_pipeline_steps()
        self.log(f"=== Pipeline '{self.pipeline_name}': {' → '.join(steps)} ===")

        context_parts: list[str] = []
        reports: list[str] = []
        self.outcome = "ok"

        for index, aid in enumerate(steps, 1):
            ac = self._agent_cfg(aid)
            name = ac.get("name", aid)
            if self.should_stop():
                self.outcome = "stopped"
                break
            self.step_fn(index, len(steps), name)
            model_key = ac.get("model", "claude_sonnet_55")
            model_id = resolve_model(self.cfg, model_key, self.catalog)
            meta = self.catalog.get(model_key) or {}
            temp = float(ac.get("temperature", 0.2))
            tools = ac.get("tools")
            allowed = None if tools is None else list(tools)
            system = ac.get("system") or ""

            api_key = self._api_key_for_model(model_id)
            if not api_key:
                msg = t("orch.skip_key", name=name, model=model_id)
                self.log(msg)
                context_parts.append(msg)
                reports.append(f"## {name}\n\n{msg}")
                continue

            self.log(f"\n>>> {name} ({aid}) | model={model_id} | tools={allowed}")
            try:
                runtime = AgentRuntime(
                    workspace=self.workspace,
                    backup_dir=self.backup_dir,
                    model=model_id,
                    api_key=api_key,
                    base_url=api_base_for(model_id, meta),
                    temperature=temp,
                    max_steps=self.max_steps,
                    shell_timeout=self.shell_timeout,
                    log_fn=self.log,
                    system_prompt=system,
                    allowed_tools=allowed,
                    role_name=name,
                    should_stop=self.should_stop,
                )
                ctx = "\n\n".join(context_parts) if context_parts else ""
                result = runtime.run(task, context=ctx)
            except RunStopped:
                self.outcome = "stopped"
                self.log(t("orch.stopped_log", name=name))
                reports.append(f"## {name}\n\n{t('orch.stopped_report')}")
                break
            except Exception as exc:
                # One failing role must not throw away what earlier roles produced.
                self.outcome = "failed"
                msg = t("orch.error", name=name, kind=type(exc).__name__, error=exc)
                self.log(msg)
                reports.append(f"## {name}\n\n{msg}")
                break
            reports.append(f"## {name}\n\n{result}")
            context_parts.append(t("orch.handoff", name=name, text=handoff(result)))

        header = f"# Pipeline: {self.pipeline_name}\n# Steps: {' → '.join(steps)}\n\n"
        return header + "\n\n---\n\n".join(reports)
