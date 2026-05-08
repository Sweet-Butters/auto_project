"""Git-backed state for agents.

Each agent gets its own subdirectory under `state/` at the repo root.
Reads return defaults if the file doesn't exist; writes overwrite.
The CI workflow is responsible for committing changes after a run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# repo root = three levels above this file: state.py -> auto_project -> src -> repo
_STATE_DIR = Path(__file__).resolve().parents[2] / "state"


def _path(agent: str, key: str) -> Path:
    return _STATE_DIR / agent / f"{key}.json"


def get(agent: str, key: str, default: Any = None) -> Any:
    p = _path(agent, key)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def set(agent: str, key: str, value: Any) -> None:
    p = _path(agent, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
