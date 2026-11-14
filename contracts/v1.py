"""Hive contract version 1.

Field names are stable. A breaking change bumps CONTRACT_VERSION.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

CONTRACT_VERSION: Literal["1"] = "1"


class Agent(BaseModel):
    """One role in the hive."""

    id: str
    name: str
    description: str = ""
    enabled: bool = True
    model: str
    temperature: float = 0.2


class Swarm(BaseModel):
    """An ordered team. `steps` are agent ids, first to last."""

    id: str
    name: str
    steps: list[str]


class Task(BaseModel):
    """What the user asked the swarm to do."""

    id: str
    text: str
    pipeline: str
    workspace: str


class Message(BaseModel):
    """One turn inside a run. Not a stream frame by itself."""

    role: Literal["user", "agent", "tool", "system"]
    author: str
    text: str
    created_at: str | None = None


class StartEvent(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["start"] = "start"
    task_id: str
    pipeline: str
    agents: list[str]


class StepEvent(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["step"] = "step"
    task_id: str
    index: int
    total: int
    agent_id: str
    title: str


class LogEvent(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["log"] = "log"
    task_id: str
    agent_id: str | None = None
    text: str


class ErrorEvent(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["error"] = "error"
    task_id: str
    agent_id: str | None = None
    code: str
    message: str


class DoneEvent(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["done"] = "done"
    task_id: str
    outcome: Literal["ok", "stopped", "failed"]
    result: str = ""


StreamEvent = Annotated[
    Union[StartEvent, StepEvent, LogEvent, ErrorEvent, DoneEvent],
    Field(discriminator="type"),
]


class LocalModelStatus(BaseModel):
    """Download or runtime state of one local model."""

    version: Literal["1"] = "1"
    name: str
    state: Literal["missing", "downloading", "installed", "starting", "running", "error"]
    progress: float | None = Field(default=None, ge=0, le=1)
    completed: int | None = None
    total: int | None = None
    size_bytes: int | None = None
    message: str = ""


EVENT_MODELS = {
    "start": StartEvent,
    "step": StepEvent,
    "log": LogEvent,
    "error": ErrorEvent,
    "done": DoneEvent,
}


def parse_event(payload: dict) -> StartEvent | StepEvent | LogEvent | ErrorEvent | DoneEvent:
    kind = payload.get("type")
    model = EVENT_MODELS.get(str(kind))
    if model is None:
        raise ValueError(f"unknown event type: {kind}")
    return model.model_validate(payload)
