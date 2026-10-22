"""
CLI for Multi-Agent Studio
  python cli.py "задача"
  python cli.py --pipeline code_only "задача"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core.orchestrator import Orchestrator, load_config, KEY_ENV


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Studio CLI")
    parser.add_argument("task", nargs="?", default="", help="Задача для агентов")
    parser.add_argument("--pipeline", "-p", default=None, help="Имя пайплайна (full, code_only, ...)")
    parser.add_argument("--workspace", "-w", default=str(ROOT / "workspace"))
    parser.add_argument("--max-steps", type=int, default=25)
    args = parser.parse_args()

    if not args.task.strip():
        print("Использование: python cli.py [--pipeline full] \"задача\"")
        sys.exit(1)

    cfg = load_config()
    pipe = args.pipeline or cfg.get("default_pipeline", "full")

    api_keys = {k: os.getenv(k, "") for k in KEY_ENV.values()}

    def log(msg: str):
        print(msg, flush=True)

    orch = Orchestrator(
        workspace=args.workspace,
        backup_dir=str(ROOT / "backups"),
        api_keys=api_keys,
        config=cfg,
        max_steps=args.max_steps,
        log_fn=log,
        pipeline_name=pipe,
    )
    result = orch.run(args.task.strip())
    print("\n======== RESULT ========\n")
    print(result)


if __name__ == "__main__":
    main()
