# auto_project — zero-cost autonomous agent framework

A small library + a workflow template that let any project run autonomous
agents on a schedule for **$0/month**, even while your laptop is off.

This repo is **the framework**. It does not run any project agents itself.
Each project that wants to use it lives in **its own repo** and depends on
this package via a pinned git tag.

## What's in here

```
src/auto_project/
  llm.py              # multi-provider LLM router (Gemini -> Groq -> Cerebras)
  state.py            # JSON state under <cwd>/state/, isolated per project
  __main__.py         # `python -m auto_project run <agent>` runner
examples/
  workflow.yml.example       # copy to <project>/.github/workflows/agents.yml
  requirements.txt.example   # copy to <project>/requirements.txt
```

## Stable API (the contract for projects)

```python
from auto_project import llm, state

llm.call(prompt: str, system: str | None = None, timeout: int = 60) -> str
state.get(agent: str, key: str, default=None) -> Any
state.set(agent: str, key: str, value: Any) -> None
```

The runner expects each agent file at `<cwd>/agents/<name>.py` to expose
a `run()` function. Agents may import sibling modules from `<cwd>/`.

**Compatibility promise**: signatures above will not change between minor
versions. New parameters will default to backward-compatible behavior.

## Using it in a new project

```bash
mkdir my-project && cd my-project
git init -b main

mkdir -p agents .github/workflows
curl -fsSL https://raw.githubusercontent.com/Sweet-Butters/auto_project/main/examples/workflow.yml.example \
  -o .github/workflows/agents.yml
curl -fsSL https://raw.githubusercontent.com/Sweet-Butters/auto_project/main/examples/requirements.txt.example \
  -o requirements.txt

# write your first agent
cat > agents/__init__.py <<'PY'
PY
cat > agents/digest.py <<'PY'
from auto_project import llm, state

def run():
    last = state.get("digest", "summary", "")
    new = llm.call(f"Continue this digest:\n{last}\n\nAdd one paragraph.")
    state.set("digest", "summary", new)
PY

# private repo + secrets
gh repo create my-project --private --source=. --push
gh secret set GEMINI_API_KEY -R <user>/my-project --body "..."
```

The workflow runs hourly on cron, discovers every `agents/*.py`, runs each
in parallel, and commits state changes back.

## Required GitHub secrets (per project repo)

- `GEMINI_API_KEY` — https://aistudio.google.com/apikey (highest free quota)
- `GROQ_API_KEY` — https://console.groq.com/keys (fallback, optional)
- `CEREBRAS_API_KEY` — https://cloud.cerebras.ai (fallback, optional)

The router tries them in that order and skips any without a key.

## Local dev

```bash
pip install -e .
export GEMINI_API_KEY=...
cd <your-project>
python -m auto_project run digest
```

For a dry run without API calls: `MOCK_LLM=1 python -m auto_project run digest`.

## Versioning

Releases are tagged on this repo. Projects pin to a specific tag
(`@v0.1.0` in their `requirements.txt`) so framework changes never
break a running project — they upgrade on their own schedule.

## Cost notes

- GitHub Actions: public repo unlimited; private repo 2,000 min/month free.
  Hourly run that finishes in ~30s ≈ 360 min/month.
- Free LLM tiers: Gemini 10 RPM / 1500 RPD, Groq ~30 RPM, Cerebras similar.
  The router falls through to the next provider on 429s.
