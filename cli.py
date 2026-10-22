#!/usr/bin/env python3
"""CLI entry: python cli.py "your task" """

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core.agent_runtime import AgentRuntime


def main():
    parser = argparse.ArgumentParser(description="Agent Studio CLI")
    parser.add_argument("task", nargs="?", help="Task text")
    parser.add_argument("--model", default=os.getenv("AGENT_MODEL", "anthropic/claude-sonnet-4-5"))
    parser.add_argument("--workspace", default=str(ROOT / "workspace"))
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--keep-awake", action="store_true", default=True)
    parser.add_argument("--no-keep-awake", action="store_true")
    parser.add_argument("--display", action="store_true", help="Also keep display on")
    args = parser.parse_args()

    task = args.task
    if not task:
        task = input("Задача: ").strip()
    if not task:
        print("Empty task")
        sys.exit(1)

    # pick key from model prefix
    key = None
    if args.model.startswith("anthropic"):
        key = os.getenv("ANTHROPIC_API_KEY")
    elif args.model.startswith("openai"):
        key = os.getenv("OPENAI_API_KEY")
    elif args.model.startswith("gemini"):
        key = os.getenv("GOOGLE_API_KEY")
    elif args.model.startswith("xai"):
        key = os.getenv("XAI_API_KEY")
    elif args.model.startswith("deepseek"):
        key = os.getenv("DEEPSEEK_API_KEY")

    runtime = AgentRuntime(
        workspace=args.workspace,
        backup_dir=str(ROOT / "backups"),
        model=args.model,
        api_key=key,
        max_steps=args.max_steps,
        log_fn=lambda s: print(s, flush=True),
    )

    if args.keep_awake and not args.no_keep_awake:
        print(runtime.power.start("display" if args.display else "system"))

    try:
        result = runtime.run(task)
        print("\n======== RESULT ========\n")
        print(result)
    finally:
        if args.keep_awake and not args.no_keep_awake:
            print(runtime.power.stop())


if __name__ == "__main__":
    main()
