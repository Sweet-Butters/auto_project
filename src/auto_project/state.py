"""Project-isolated state, backed by JSON files under `<cwd>/state/`.

When a project installs `auto_project` as a dependency and runs an agent
from its own repo root, `Path.cwd() / "state"` resolves to that project's
state directory. Two projects on the same machine never share files.

Stable API — additions OK, signatures must stay compatible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _path(agent: str, key: str) -> Path:
    return Path.cwd() / "state" / agent / f"{key}.json"


def get(agent: str, key: str, default: Any = None) -> Any:
    p = _path(agent, key)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def set(agent: str, key: str, value: Any) -> None:
    p = _path(agent, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
