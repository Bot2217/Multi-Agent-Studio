"""Run one task on the existing orchestrator and emit contract v1 frames.

Streamlit keeps calling Orchestrator itself. This module is the HTTP path.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from contracts.v1 import DoneEvent, ErrorEvent, LogEvent, StartEvent, StepEvent, Task
from core.agent_runtime import AgentRuntime
from core.catalog import api_base_for, provider_of
from core.engine import AgentJob, AgentProblem, SwarmEngine, jobs_from_pipeline
from core.i18n import t
from core.local_runtime import LocalRuntimeError
from core.orchestrator import Orchestrator, resolve_model

Publish = Callable[[StartEvent | StepEvent | LogEvent | ErrorEvent | DoneEvent], None]


def orchestrator_runner(
    task: Task,
    publish: Publish,
    cancel: threading.Event,
    timeout_s: float | None = None,
    *,
    api_keys: dict[str, str] | None = None,
    config: dict | None = None,
) -> None:
    reason = {"why": ""}
    deadline = None if timeout_s is None else time.monotonic() + timeout_s

    def should_stop() -> bool:
        if cancel.is_set():
            reason["why"] = "cancelled"
            return True
        if deadline is not None and time.monotonic() >= deadline:
            reason["why"] = "timeout"
            return True
        return False

    def log(text: str) -> None:
        publish(LogEvent(task_id=task.id, text=str(text)))

    titles: dict[str, str] = {}

    def step(index: int, total: int, title: str) -> None:
        agent_id = steps[index - 1] if 0 < index <= len(steps) else ""
        titles[agent_id] = title
        publish(
            StepEvent(
                task_id=task.id,
                index=index,
                total=total,
                agent_id=agent_id,
                title=title,
            )
        )

    hive = Orchestrator(
        workspace=task.workspace,
        backup_dir=task.workspace,
        api_keys=api_keys or {},
        config=config,
        pipeline_name=task.pipeline,
        log_fn=log,
        step_fn=step,
        should_stop=should_stop,
    )
    steps = hive.list_pipeline_steps()
    publish(StartEvent(task_id=task.id, pipeline=task.pipeline, agents=steps))
    try:
        result = hive.run(task.text)
    except Exception as exc:
        publish(
            ErrorEvent(
                task_id=task.id,
                code="run_failed",
                message=f"{type(exc).__name__}: {exc}",
            )
        )
        publish(DoneEvent(task_id=task.id, outcome="failed"))
        return

    outcome = hive.outcome if hive.outcome in {"ok", "stopped", "failed"} else "failed"
    if reason["why"] == "timeout":
        publish(ErrorEvent(task_id=task.id, code="timeout", message=t("api.timeout")))
        outcome = "failed"
    elif outcome == "failed":
        publish(
            ErrorEvent(
                task_id=task.id,
                code="agent_failed",
                message=t("api.agent_failed"),
            )
        )
    publish(DoneEvent(task_id=task.id, outcome=outcome, result=result or ""))


def engine_runner(
    task: Task,
    publish: Publish,
    cancel: threading.Event,
    timeout_s: float | None = None,
    *,
    api_keys: dict[str, str] | None = None,
    config: dict | None = None,
    prepare_local=None,
    mcp_clients=None,
) -> None:
    """HTTP path. Independent roles in one wave run at the same time."""
    hive = Orchestrator(
        workspace=task.workspace,
        backup_dir=task.workspace,
        api_keys=api_keys or {},
        config=config,
        pipeline_name=task.pipeline,
        log_fn=lambda _text: None,
        should_stop=cancel.is_set,
    )

    def agent_title(agent_id: str) -> str | None:
        raw = hive._agent_cfg(agent_id)
        if not raw.get("enabled", True):
            return None
        return str(raw.get("name") or agent_id)

    jobs = jobs_from_pipeline(hive.cfg, task.pipeline, agent_title)
    if _needs_ollama(hive, jobs):
        start = prepare_local or _ensure_ollama
        try:
            start()
        except LocalRuntimeError as exc:
            publish(ErrorEvent(task_id=task.id, code=exc.code, message=exc.message))
            publish(DoneEvent(task_id=task.id, outcome="failed", result=""))
            return

    def execute(job: AgentJob, context: str, should_stop: Callable[[], bool]) -> str:
        raw = hive._agent_cfg(job.id)
        model_key = str(raw.get("model") or "")
        model_id = resolve_model(hive.cfg, model_key, hive.catalog) if model_key else ""
        api_key = hive._api_key_for_model(model_id)
        if not api_key:
            raise AgentProblem(
                "missing_api_key",
                t("orch.skip_key", name=job.title, model=model_id),
            )

        def log(text: str) -> None:
            publish(LogEvent(task_id=task.id, agent_id=job.id, text=str(text)))

        tools = raw.get("tools")
        extra_tools = _mcp_tools(raw, mcp_clients)
        runtime = AgentRuntime(
            workspace=task.workspace,
            backup_dir=task.workspace,
            model=model_id,
            api_key=api_key,
            base_url=api_base_for(model_id, hive.catalog.get(model_key) or {}),
            temperature=float(raw.get("temperature", 0.2)),
            max_steps=hive.max_steps,
            shell_timeout=hive.shell_timeout,
            log_fn=log,
            system_prompt=raw.get("system") or "",
            allowed_tools=None if tools is None else list(tools),
            role_name=job.title,
            should_stop=should_stop,
            extra_tools=extra_tools or None,
        )
        return runtime.run(task.text, context=context)

    SwarmEngine(execute).run(
        task.id,
        task.pipeline,
        jobs,
        publish,
        cancel,
        timeout_s,
    )


def _resolved(hive: Orchestrator, job: AgentJob) -> str:
    raw = hive._agent_cfg(job.id)
    model_key = str(raw.get("model") or "")
    if not model_key:
        return ""
    return resolve_model(hive.cfg, model_key, hive.catalog)


def _needs_ollama(hive: Orchestrator, jobs: list[AgentJob]) -> bool:
    return any(provider_of(_resolved(hive, job)) == "ollama" for job in jobs)


def _mcp_tools(raw: dict, clients) -> dict:
    if not clients:
        return {}
    from core.mcp_client import tool_callables

    tools = {}
    for name in raw.get("mcp") or []:
        client = clients[str(name)]
        tools.update(tool_callables(str(name), client))
    return tools


def _ensure_ollama() -> None:
    from core.ollama_runtime import OllamaRuntime

    OllamaRuntime().ensure_running()
