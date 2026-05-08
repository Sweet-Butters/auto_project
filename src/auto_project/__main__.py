"""Run an agent from the current working directory.

Usage:
    cd <project_repo>
    python -m auto_project run <agent_name>

Looks for `<cwd>/agents/<agent_name>.py` and calls its `run()` function.
The agent can `from auto_project import llm, state` and use sibling
modules under `<cwd>/agents/` or `<cwd>/lib/`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print("usage: python -m auto_project run <agent_name>", file=sys.stderr)
        return 2

    agent = sys.argv[2]
    agent_path = Path.cwd() / "agents" / f"{agent}.py"
    if not agent_path.exists():
        print(f"agent file not found: {agent_path}", file=sys.stderr)
        return 2

    # Make cwd importable so the agent can `from lib.x import y` etc.
    sys.path.insert(0, str(Path.cwd().resolve()))

    spec = importlib.util.spec_from_file_location(f"agents.{agent}", agent_path)
    if spec is None or spec.loader is None:
        print(f"could not load {agent_path}", file=sys.stderr)
        return 2
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "run"):
        print(f"agent {agent} has no run() function", file=sys.stderr)
        return 2
    mod.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
