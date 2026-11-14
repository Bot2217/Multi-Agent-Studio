"""Run one task on the existing orchestrator and emit contract v1 frames.

Streamlit keeps calling Orchestrator itself. This module is the HTTP path.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from contracts.v1 import DoneEvent, ErrorEvent, LogEvent, StartEvent, StepEvent, Task
from core.i18n import t
from core.orchestrator import Orchestrator

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
