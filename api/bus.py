"""Fan-out for contract v1 frames. Late subscribers receive the whole run."""

from __future__ import annotations

import threading
from collections.abc import Iterator

from contracts.v1 import DoneEvent, ErrorEvent, LogEvent, StartEvent, StepEvent

Event = StartEvent | StepEvent | LogEvent | ErrorEvent | DoneEvent


class EventBus:
    def __init__(self) -> None:
        self._history: dict[str, list[dict]] = {}
        self._cond = threading.Condition()

    def publish(self, event: Event) -> dict:
        payload = event.model_dump()
        task_id = str(payload["task_id"])
        with self._cond:
            self._history.setdefault(task_id, []).append(payload)
            self._cond.notify_all()
        return payload

    def history(self, task_id: str) -> list[dict]:
        with self._cond:
            return list(self._history.get(task_id, []))

    def listen(self, task_id: str) -> Iterator[dict]:
        """Yield frames until `done`. Blocks when the run has not finished."""
        cursor = 0
        while True:
            with self._cond:
                batch = self._history.get(task_id, [])
                while cursor >= len(batch):
                    self._cond.wait(timeout=0.5)
                    batch = self._history.get(task_id, [])
                fresh = batch[cursor:]
                cursor = len(batch)
            for item in fresh:
                yield item
                if item.get("type") == "done":
                    return
