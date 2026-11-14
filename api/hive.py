"""Agents, swarms and tasks loaded from the existing hive config."""

from __future__ import annotations

import threading
from pathlib import Path

from contracts.v1 import Agent, Swarm, Task
from core.catalog import load_models_catalog
from core.orchestrator import load_config, resolve_model

DEFAULT_PIPELINE = "code_only"


def load_hive_config(path: str | Path | None = None) -> dict:
    return load_config(path)


def list_agents(cfg: dict, catalog: dict | None = None) -> list[Agent]:
    catalog = load_models_catalog() if catalog is None else catalog
    agents: list[Agent] = []
    for agent_id, raw in (cfg.get("agents") or {}).items():
        if not isinstance(raw, dict):
            continue
        model_key = str(raw.get("model") or "")
        agents.append(
            Agent(
                id=str(agent_id),
                name=str(raw.get("name") or agent_id),
                description=str(raw.get("description") or ""),
                enabled=bool(raw.get("enabled", True)),
                model=resolve_model(cfg, model_key, catalog) if model_key else "",
                temperature=float(raw.get("temperature", 0.2)),
            )
        )
    return agents


def list_swarms(cfg: dict) -> list[Swarm]:
    swarms: list[Swarm] = []
    for swarm_id, raw in (cfg.get("pipelines") or {}).items():
        if not isinstance(raw, dict):
            continue
        steps = [str(step) for step in (raw.get("steps") or [])]
        swarms.append(
            Swarm(
                id=str(swarm_id),
                name=str(raw.get("description") or swarm_id),
                steps=steps,
            )
        )
    return swarms


class TaskBook:
    """Tasks created through the API. They live for one process."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._n = 0

    def swarm_ids(self) -> set[str]:
        return {swarm.id for swarm in list_swarms(self.cfg)}

    def create(self, text: str, pipeline: str, workspace: str) -> Task:
        if pipeline not in self.swarm_ids():
            raise KeyError(pipeline)
        with self._lock:
            self._n += 1
            task_id = f"task_{self._n:04d}"
            task = Task(id=task_id, text=text, pipeline=pipeline, workspace=workspace)
            self.tasks[task_id] = task
            return task

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)
