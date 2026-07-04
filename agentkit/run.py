"""
CLI entry point.

    python3 -m agentkit.run <agent> [--data path] [--task "..."] [--model ...]

Agents: data-analyst | data-scientist | ai-engineer | ml-engineer

With no --data, the agent runs on its bundled sample dataset. Each run gets
a fresh working directory under runs/<agent>-<timestamp>/ containing the
data, everything the agent wrote, and its outputs/ folder.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from agentkit.definitions import AGENTS
from agentkit.loop import run_agent, DEFAULT_MODEL


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local AI data agent.")
    parser.add_argument("agent", choices=sorted(AGENTS))
    parser.add_argument("--data", help="path to your CSV/markdown (default: bundled sample)")
    parser.add_argument("--task", help="override the default task prompt")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--allow-git", action="store_true",
                        help="allow git push / repo creation, each gated by an "
                             "interactive y/n approval prompt")
    parser.add_argument("--max-turns", type=int, default=60,
                        help="max agent turns (default 60; more turns = more cost)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set.\n"
            "Get a key at https://platform.claude.com/settings/keys and run:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "(To verify the framework without a key: python3 -m pytest tests/ -q)"
        )
    from anthropic import Anthropic
    client = Anthropic()

    if args.allow_git:
        import agentkit.tools as tools

        def interactive_approval(command: str):
            print(f"\n  >>> APPROVAL REQUIRED for: {command}")
            answer = input("  approve? [y/N] ").strip().lower()
            return True if answer == "y" else "DENIED: human rejected this command."

        tools.APPROVAL_HOOK = interactive_approval

    spec = AGENTS[args.agent]

    # Resolve the dataset (bundled sample generated on demand)
    if args.data:
        data_path = Path(args.data).resolve()
        if not data_path.exists():
            sys.exit(f"data file not found: {data_path}")
    else:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from data.make_samples import ensure
        data_path = ensure(spec["sample_data"])

    # Fresh working directory per run
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    workdir = Path("runs") / f"{args.agent}-{stamp}"
    workdir.mkdir(parents=True)
    local_data = workdir / data_path.name
    shutil.copy(data_path, local_data)

    task = (args.task or spec["default_task"]).format(data=data_path.name)

    print(f"=== {args.agent} | model={args.model} | workdir={workdir} ===")
    final = run_agent(client, spec["system"], task, workdir, model=args.model,
                      max_turns=args.max_turns)
    print(f"\n=== Agent finished ===\n{final}\n")
    print(f"Outputs: {workdir}/outputs/")


if __name__ == "__main__":
    main()
