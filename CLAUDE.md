# auto_project — Claude context

Public framework repo. Library + workflow templates for zero-cost autonomous
agents. Each project that uses it lives in **its own private repo** and pins
to a tag in `requirements.txt`.

## Architecture

```
src/auto_project/        # the library
  llm.py                 # multi-LLM router (Gemini → Groq → Cerebras fallback)
  state.py               # JSON state under <cwd>/state/, isolated per project
  notify.py              # Telegram alerts (silent no-op without env vars)
  __main__.py            # `python -m auto_project run <agent>` runner
examples/                # templates projects copy
  workflow.yml.example
  requirements.txt.example
bot/                     # standalone Cloud Run service (FastAPI)
  app.py                 # phone → bot → workflow_dispatch
.github/workflows/agent.yml  # framework CI (mock-LLM smoke test, not cron)
```

## Stable API contract (don't break in minor versions)

```python
from auto_project import llm, state, notify

llm.call(prompt: str, system: str | None = None, timeout: int = 60) -> str
state.get(agent: str, key: str, default=None) -> Any
state.set(agent: str, key: str, value: Any) -> None
notify.telegram(message: str, parse_mode: str = "HTML") -> bool
notify.escape(text: str) -> str
```

Adding parameters with defaults is fine. Renaming/removing requires a major bump.

## Versioning rules

- Tag every release on this repo (`v0.X.Y`).
- Projects pin via `pip install git+https://...@vX.Y.Z` in requirements.txt.
- Patches that break the API → major bump.
- Patches that add features without breaking existing callers → minor bump.
- Pure bug fixes / docs → patch bump.

## What goes in this repo vs. project repos

**Here (public)**: anything generic and reusable. Library code, workflow
templates, the `bot/` service code (deployment-agnostic), framework tests.

**Project repos (private)**: agents, prompts, project state, project-specific
data, deployment configuration with secrets.

## Running framework tests locally

```bash
pip install -e .
pytest tests/
```

The CI runs the same on every push to main.

## Cloud Run bot deployment

`bot/` is a standalone FastAPI service. Deploy from any project that wants
to expose phone control. See `bot/README.md` for the deploy command.

## Hooks / blockers seen in this repo's sessions

- Pushing to main of this **public** repo requires explicit user authorization in a chat message (the runtime hook checks for it).
- Co-Authored-By trailers in commit messages are blocked — omit them.
- Files matching `*credentials*`, `*secret*`, `keys.txt`, `*.key`, `*.pem` are gitignored to prevent accidental commits.
