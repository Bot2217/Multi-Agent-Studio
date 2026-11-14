"""Contract v1 examples stay valid and the schema file matches the models."""

import json
from pathlib import Path

from contracts.export_schema import SCHEMA_PATH, schema_document
from contracts.v1 import (
    CONTRACT_VERSION,
    Agent,
    DoneEvent,
    ErrorEvent,
    LocalModelStatus,
    LogEvent,
    Message,
    StartEvent,
    StepEvent,
    Swarm,
    Task,
    parse_event,
)

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "docs" / "contracts" / "README.md"


def _blocks():
    text = README.read_text(encoding="utf-8")
    chunks = []
    current = []
    inside = False
    for line in text.splitlines():
        if line.startswith("```"):
            if inside:
                chunks.append("\n".join(current))
                current = []
            inside = not inside
            continue
        if inside:
            current.append(line)
    return chunks


def test_version_and_examples_roundtrip():
    assert CONTRACT_VERSION == "1"
    payloads = []
    for block in _blocks():
        if not block.strip().startswith("{"):
            continue
        payloads.append(json.loads(block))
    assert len(payloads) == 10
    Agent.model_validate(payloads[0])
    Swarm.model_validate(payloads[1])
    Task.model_validate(payloads[2])
    Message.model_validate(payloads[3])
    LocalModelStatus.model_validate(payloads[4])
    events = [parse_event(item) for item in payloads[5:]]
    assert [event.type for event in events] == ["start", "step", "log", "error", "done"]
    assert isinstance(events[0], StartEvent)
    assert isinstance(events[1], StepEvent)
    assert isinstance(events[2], LogEvent)
    assert isinstance(events[3], ErrorEvent)
    assert isinstance(events[4], DoneEvent)
    assert events[4].outcome == "ok"


def test_schema_file_matches_models():
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert on_disk == schema_document()
    assert set(on_disk["$defs"]) == {
        "Agent",
        "Swarm",
        "Task",
        "Message",
        "StartEvent",
        "StepEvent",
        "LogEvent",
        "ErrorEvent",
        "DoneEvent",
        "LocalModelStatus",
    }
