"""Swarm engine v2.

Independent agents in one wave run together. The next wave starts only after
the current one finishes. Streamlit still uses Orchestrator.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from contracts.v1 import DoneEvent, ErrorEvent, StartEvent, StepEvent
from core.agent_runtime import RunStopped
from core.i18n import t
from core.orchestrator import handoff

Publish = Callable[[StartEvent | StepEvent | ErrorEvent | DoneEvent], None]
Execute = Callable[[object, str, Callable[[], bool]], str]


class AgentProblem(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AgentTimeout(Exception):
    pass


@dataclass(frozen=True)
class AgentJob:
    id: str
    title: str
    wave: int


class SwarmEngine:
    def __init__(self, execute: Execute, agent_timeout_s: float = 120):
        self.execute = execute
        self.agent_timeout_s = agent_timeout_s

    def run(
        self,
        task_id: str,
        pipeline: str,
        jobs: list[AgentJob],
        publish: Publish,
        cancel: threading.Event,
        timeout_s: float | None = None,
    ) -> str:
        publish(
            StartEvent(
                task_id=task_id,
                pipeline=pipeline,
                agents=[job.id for job in jobs],
            )
        )
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        context = ""
        reports: list[str] = []
        outcome = "ok"
        total = len(jobs)
        index = 0
        for wave in _waves(jobs):
            if cancel.is_set():
                publish(
                    ErrorEvent(
                        task_id=task_id,
                        code="cancelled",
                        message=t("api.cancelled"),
                    )
                )
                outcome = "stopped"
                break
            if _expired(deadline):
                publish(ErrorEvent(task_id=task_id, code="timeout", message=t("api.timeout")))
                outcome = "failed"
                break
            wave_reports: list[tuple[str, str]] = []
            with ThreadPoolExecutor(max_workers=max(1, len(wave))) as pool:
                futures = []
                for job in wave:
                    index += 1
                    publish(
                        StepEvent(
                            task_id=task_id,
                            index=index,
                            total=total,
                            agent_id=job.id,
                            title=job.title,
                        )
                    )
                    futures.append(
                        (
                            job,
                            pool.submit(
                                self._one,
                                job,
                                context,
                                cancel,
                                publish,
                                task_id,
                                deadline,
                            ),
                        )
                    )
                for job, future in futures:
                    try:
                        text = future.result()
                    except AgentTimeout:
                        outcome = "failed"
                        continue
                    except AgentProblem as exc:
                        publish(
                            ErrorEvent(
                                task_id=task_id,
                                agent_id=job.id,
                                code=exc.code,
                                message=exc.message,
                            )
                        )
                        outcome = "stopped" if exc.code == "cancelled" else "failed"
                        continue
                    wave_reports.append((job.title, text))
            for title, text in wave_reports:
                reports.append(f"## {title}\n\n{text}")
            if outcome != "ok":
                break
            context = "\n\n".join(
                t("orch.handoff", name=title, text=handoff(text)) for title, text in wave_reports
            )
        result = "\n\n---\n\n".join(reports)
        publish(DoneEvent(task_id=task_id, outcome=outcome, result=result))
        return result

    def _one(
        self,
        job: AgentJob,
        context: str,
        cancel: threading.Event,
        publish: Publish,
        task_id: str,
        deadline: float | None,
    ) -> str:
        if cancel.is_set():
            raise AgentProblem("cancelled", t("api.cancelled"))
        if _expired(deadline):
            publish(
                ErrorEvent(
                    task_id=task_id, agent_id=job.id, code="timeout", message=t("api.timeout")
                )
            )
            raise AgentTimeout()
        limit = self.agent_timeout_s
        if deadline is not None:
            limit = min(limit, max(0.01, deadline - time.monotonic()))
        stop = threading.Event()

        def should_stop() -> bool:
            return cancel.is_set() or stop.is_set()

        box: dict = {}

        def target() -> None:
            try:
                box["value"] = self.execute(job, context, should_stop)
            except Exception as exc:
                box["error"] = exc

        thread = threading.Thread(target=target, name=f"ulei-{job.id}", daemon=True)
        thread.start()
        thread.join(limit)
        if thread.is_alive():
            stop.set()
            publish(
                ErrorEvent(
                    task_id=task_id,
                    agent_id=job.id,
                    code="timeout",
                    message=t("api.agent_timeout", name=job.title, seconds=int(limit)),
                )
            )
            raise AgentTimeout()
        if "error" in box:
            err = box["error"]
            if isinstance(err, RunStopped) or cancel.is_set():
                raise AgentProblem("cancelled", t("api.cancelled"))
            if isinstance(err, AgentProblem):
                raise err
            raise AgentProblem(
                "agent_failed",
                t("orch.error", name=job.title, kind=type(err).__name__, error=err),
            )
        return str(box.get("value") or "")


def _expired(deadline: float | None) -> bool:
    return deadline is not None and time.monotonic() >= deadline


def jobs_from_pipeline(
    cfg: dict,
    pipeline: str,
    title_of: Callable[[str], str | None],
) -> list[AgentJob]:
    """`title_of` returns None when that agent is turned off."""
    pipe = (cfg.get("pipelines") or {}).get(pipeline) or {}
    raw_waves = pipe.get("waves")
    if isinstance(raw_waves, list) and raw_waves:
        jobs: list[AgentJob] = []
        for number, wave in enumerate(raw_waves):
            for agent_id in wave or []:
                title = title_of(str(agent_id))
                if title is None:
                    continue
                jobs.append(AgentJob(str(agent_id), title, number))
        return jobs
    steps = [str(step) for step in (pipe.get("steps") or ["developer"])]
    jobs = []
    number = 0
    for agent_id in steps:
        title = title_of(agent_id)
        if title is None:
            continue
        jobs.append(AgentJob(agent_id, title, number))
        number += 1
    return jobs


def _waves(jobs: list[AgentJob]) -> list[list[AgentJob]]:
    grouped: dict[int, list[AgentJob]] = {}
    for job in jobs:
        grouped.setdefault(job.wave, []).append(job)
    return [grouped[key] for key in sorted(grouped)]
