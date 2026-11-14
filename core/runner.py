"""Runs a pipeline in a background thread so the UI can show progress and stop it."""

from __future__ import annotations

import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.i18n import t
from core.orchestrator import Orchestrator
from tools.power import PowerManager


class RunJob:
    """One pipeline run. Fields are written by the worker thread and read by the UI."""

    def __init__(
        self,
        task: str,
        results_dir: str | Path,
        keep_awake: bool = False,
        keep_display: bool = False,
        **orchestrator_kwargs,
    ):
        self.task = task.strip()
        self.results_dir = Path(results_dir)
        self.keep_awake = keep_awake
        self.keep_display = keep_display
        self.logs: list[str] = []
        self.started = datetime.now()
        self.finished: Optional[datetime] = None
        self.step = (0, 0, "")
        self.result = ""
        self.error = ""
        self.traceback = ""
        self.outcome = "running"
        self.report_path: Optional[Path] = None
        self._stop = threading.Event()
        self._kwargs = orchestrator_kwargs
        self._thread = threading.Thread(target=self._work, daemon=True)

    def start(self) -> "RunJob":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: Optional[float] = None) -> None:
        self._thread.join(timeout)

    @property
    def running(self) -> bool:
        return self.outcome == "running"

    @property
    def stopping(self) -> bool:
        return self.running and self._stop.is_set()

    def log(self, message: str) -> None:
        self.logs.append(str(message))

    def report(self) -> str:
        return (
            f"# {t('report.task')}\n\n{self.task}\n\n# {t('report.log')}\n\n"
            + "\n".join(self.logs)
            + f"\n\n# {t('report.result')}\n\n{self.result}"
        )

    def _on_step(self, index: int, total: int, name: str) -> None:
        self.step = (index, total, name)

    def _work(self) -> None:
        power = PowerManager() if self.keep_awake else None
        outcome = "ok"
        try:
            if power:
                self.log(power.start("display" if self.keep_display else "system"))
            orchestrator = Orchestrator(
                log_fn=self.log,
                should_stop=self._stop.is_set,
                step_fn=self._on_step,
                **self._kwargs,
            )
            self.result = orchestrator.run(self.task)
            outcome = orchestrator.outcome
        except Exception as exc:
            outcome = "failed"
            self.error = f"{type(exc).__name__}: {exc}"
            self.traceback = traceback.format_exc()
        finally:
            if power:
                self.log(power.stop())
            self.finished = datetime.now()
            try:
                self.results_dir.mkdir(parents=True, exist_ok=True)
                path = self.results_dir / f"run_{self.started:%Y%m%d_%H%M%S}.md"
                path.write_text(self.report(), encoding="utf-8")
                self.report_path = path
            except OSError as exc:
                self.log(t("report.save_failed", error=exc))
            self.outcome = outcome
