"""Pause, resume and cancel one model download without talking to the network."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from contracts.v1 import LocalModelStatus
from core.i18n import t
from core.local_runtime import LocalRuntimeError


@dataclass
class _Slot:
    pause: threading.Event
    cancel: threading.Event
    status: LocalModelStatus
    thread: threading.Thread | None = None


class DownloadManager:
    def __init__(self, pull) -> None:
        self._pull = pull
        self._slots: dict[str, _Slot] = {}
        self._lock = threading.Lock()

    def statuses(self) -> list[LocalModelStatus]:
        with self._lock:
            return [slot.status for slot in self._slots.values()]

    def status(self, name: str) -> LocalModelStatus | None:
        with self._lock:
            slot = self._slots.get(name)
            return None if slot is None else slot.status

    def start(self, name: str) -> LocalModelStatus:
        with self._lock:
            slot = self._slots.get(name)
            if slot and slot.thread and slot.thread.is_alive():
                return slot.status
            slot = _Slot(
                pause=threading.Event(),
                cancel=threading.Event(),
                status=LocalModelStatus(name=name, state="downloading", progress=0, message=""),
            )
            self._slots[name] = slot

            def worker() -> None:
                def cancel() -> bool:
                    return slot.pause.is_set() or slot.cancel.is_set()

                def on_progress(text: str, done: int, total: int) -> None:
                    progress = (done / total) if total else None
                    self._write(
                        name,
                        state="downloading",
                        progress=progress,
                        completed=done,
                        total=total or None,
                        message=text,
                    )

                try:
                    self._pull(name, on_progress, cancel)
                except LocalRuntimeError as exc:
                    if slot.cancel.is_set():
                        self._write(name, state="missing", message=t("ollama.model_cancelled"))
                    elif slot.pause.is_set():
                        self._write(name, state="paused", message=t("api.paused"))
                    else:
                        self._write(name, state="error", message=exc.message)
                    return
                self._write(name, state="installed", progress=1, message="")

            slot.thread = threading.Thread(target=worker, name=f"pull-{name}", daemon=True)
            slot.thread.start()
            return slot.status

    def pause(self, name: str) -> LocalModelStatus | None:
        with self._lock:
            slot = self._slots.get(name)
            if slot is None:
                return None
            slot.pause.set()
        return self.status(name)

    def resume(self, name: str) -> LocalModelStatus | None:
        with self._lock:
            slot = self._slots.get(name)
            if slot is None:
                return None
            slot.pause.clear()
            slot.cancel.clear()
        return self.start(name)

    def cancel(self, name: str) -> LocalModelStatus | None:
        with self._lock:
            slot = self._slots.get(name)
            if slot is None:
                return None
            slot.cancel.set()
            slot.pause.clear()
        return self.status(name)

    def _write(self, name: str, **fields) -> None:
        with self._lock:
            slot = self._slots[name]
            data = slot.status.model_dump()
            data.update(fields)
            slot.status = LocalModelStatus.model_validate(data)
