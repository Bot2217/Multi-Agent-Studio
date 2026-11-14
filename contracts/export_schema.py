"""Write JSON Schema for contract v1.

TypeScript can be generated from that file, without adding a Node dependency
to this repository:

    npx --yes json-schema-to-typescript docs/contracts/ulei-contract-v1.schema.json -o ulei-contract-v1.d.ts
"""

from __future__ import annotations

import json
from pathlib import Path

from contracts.v1 import (
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
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "docs" / "contracts" / "ulei-contract-v1.schema.json"

MODELS = (
    Agent,
    Swarm,
    Task,
    Message,
    StartEvent,
    StepEvent,
    LogEvent,
    ErrorEvent,
    DoneEvent,
    LocalModelStatus,
)


def schema_document() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/Bot2217/Multi-Agent-Studio/contracts/v1",
        "title": "Ulei contract v1",
        "$defs": {model.__name__: model.model_json_schema() for model in MODELS},
    }


def main() -> None:
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(
        json.dumps(schema_document(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(SCHEMA_PATH)


if __name__ == "__main__":
    main()
