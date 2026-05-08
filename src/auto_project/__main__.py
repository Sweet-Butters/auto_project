"""Entry point: `python -m auto_project run <agent_name>`."""

import importlib
import sys


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "run":
        agent_name = sys.argv[2]
        try:
            mod = importlib.import_module(f"auto_project.agents.{agent_name}")
        except ModuleNotFoundError:
            print(f"unknown agent: {agent_name}", file=sys.stderr)
            return 2
        if not hasattr(mod, "run"):
            print(f"agent {agent_name} has no run() function", file=sys.stderr)
            return 2
        mod.run()
        return 0

    print("usage: python -m auto_project run <agent_name>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
