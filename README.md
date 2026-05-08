# auto_project — zero-cost autonomous agent framework

Run autonomous agents on a schedule with **$0 in monthly cost**, even while
your laptop is off. Phone-controllable comes in Phase 2 (Telegram + Cloud Run).

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Compute | GitHub Actions (cron) | Free; runs while laptop is off |
| LLM | Gemini → Groq → Cerebras | Free tiers, automatic fallback |
| State | Git-committed JSON files under `state/` | Free, versioned, no DB |
| Multi-agent | GitHub Actions matrix strategy | Parallel jobs out of the box |

## Layout

```
src/auto_project/
  llm.py          # multi-provider router with rate-limit fallback
  state.py        # get/set helpers backed by state/ files
  agents/         # one file per agent, exposing run()
    hello.py      # phase-1 verification agent
.github/workflows/
  agent.yml       # cron + matrix discovers and runs every agent
state/            # written by agents, committed by CI
```

## Add a new agent

1. Create `src/auto_project/agents/<name>.py` with a `run()` function.
2. Use `llm.call(prompt, system=...)` and `state.get/set("<name>", key, ...)`.
3. Push. The workflow auto-discovers the new file on next run.

Example:

```python
# src/auto_project/agents/digest.py
from auto_project import llm, state

NAME = "digest"

def run():
    last = state.get(NAME, "summary", "")
    new = llm.call(f"Continue this digest:\n{last}\n\nAdd one paragraph.")
    state.set(NAME, "summary", new)
```

## Required GitHub secrets

Add at least **one** of these in repo Settings → Secrets and variables → Actions:

- `GEMINI_API_KEY` — https://aistudio.google.com/apikey (recommended; highest free quota)
- `GROQ_API_KEY` — https://console.groq.com/keys (fast fallback)
- `CEREBRAS_API_KEY` — https://cloud.cerebras.ai (second fallback)

The router tries them in that order and skips any without a key.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export GEMINI_API_KEY=...      # or any one of the three
python -m auto_project run hello
```

For dry-run without API calls:

```bash
MOCK_LLM=1 python -m auto_project run hello
```

## Run manually on GitHub

Actions tab → **agents** → Run workflow. Set `agent` to a specific name or
leave it as `all`.

## Phase roadmap

- [x] **Phase 0**: skeleton, multi-LLM router, state, hello agent, cron + matrix
- [ ] **Phase 1**: deploy hello agent end-to-end on GitHub Actions, verify state commits work
- [ ] **Phase 2**: Telegram bidirectional control via Cloud Run webhook
- [ ] **Phase 3**: real project agents

## Cost notes

- GitHub Actions: **public repos = unlimited**, private = 2,000 min/month free.
  An hourly run that finishes in ~30s consumes ≈360 min/month.
- Gemini free tier: 10 RPM, 1500 RPD on `gemini-2.5-flash`.
- Groq free tier: 30 RPM (varies by model).
- Cerebras free tier: similar.

If one provider rate-limits, the router moves to the next automatically.
