# auto_project bot — Cloud Run Telegram dispatcher

A small FastAPI service that lets you trigger GitHub Actions workflows in
allowed repos from a Telegram chat. Deployed once per user.

## Architecture

```
[your phone]
    │ Telegram message
    ▼
[Telegram cloud]
    │ webhook POST
    ▼
[Cloud Run: this service]
    │ workflow_dispatch
    ▼
[GitHub Actions: <repo>/.github/workflows/agents.yml]
```

## Required env vars

| Variable | Purpose |
|---|---|
| `WEBHOOK_SECRET` | Random path segment, prevents anyone hitting the webhook |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID (only this chat may use the bot) |
| `GITHUB_TOKEN` | PAT with `repo` scope (for `workflow_dispatch`) |
| `DEFAULT_REPO` | e.g. `Sweet-Butters/Yorg_project` (optional) |
| `ALLOWED_REPOS` | comma-separated; defaults to `DEFAULT_REPO` |
| `WORKFLOW_FILE` | name of workflow file to dispatch (default `agents.yml`) |
| `ADD_VIDEO_WORKFLOW` | workflow dispatched by `/add` (default `add_video.yml`) |
| `URL_ROUTES` | JSON array of URL-pattern → workflow routes. Optional (see below) |

### URL routing (since v0.4.0)

Any non-command message that contains a URL is matched against `URL_ROUTES`.
The first matching route fires `workflow_dispatch` on the configured repo,
with the URL passed as the named workflow input.

This complements `/add`: `/add` is an explicit command, `URL_ROUTES` is
automatic and supports multiple destinations (e.g. YouTube → summarizer,
arXiv → paper-reader, etc.).

Example — forward YouTube links to a summarizer in another repo:

```yaml
URL_ROUTES: |
  [
    {
      "pattern": "(?:youtube\\.com/watch|youtu\\.be/)",
      "repo": "Sweet-Butters/Notes_project",
      "workflow": "summarize-video.yml",
      "input_key": "url",
      "extra_inputs": {"display_lang": "ko"}
    }
  ]
```

Fields per route:
- `pattern` — regex matched against the extracted URL (`re.search` semantics).
- `repo` — target `owner/repo`; must also be present in `ALLOWED_REPOS`.
- `workflow` — workflow filename (e.g. `summarize-video.yml`).
- `input_key` — workflow input name that receives the URL.
- `extra_inputs` (optional) — extra inputs merged into the dispatch payload.

## Deploy (one-shot)

From the repo root:

```bash
WEBHOOK_SECRET=$(openssl rand -hex 32)
GITHUB_TOKEN=$(gh auth token)

cat > /tmp/bot_env.yaml <<EOF
WEBHOOK_SECRET: "${WEBHOOK_SECRET}"
TELEGRAM_BOT_TOKEN: "..."
TELEGRAM_CHAT_ID: "..."
GITHUB_TOKEN: "${GITHUB_TOKEN}"
DEFAULT_REPO: "Sweet-Butters/Yorg_project"
ALLOWED_REPOS: "Sweet-Butters/Yorg_project"
EOF

cd bot/
gcloud run deploy auto-bot \
  --source=. \
  --region=asia-northeast3 \
  --allow-unauthenticated \
  --env-vars-file=/tmp/bot_env.yaml \
  --quiet

URL=$(gcloud run services describe auto-bot --region=asia-northeast3 --format='value(status.url)')
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=${URL}/telegram/${WEBHOOK_SECRET}"
rm /tmp/bot_env.yaml
```

After deploy, send `/help` to your bot in Telegram.

## Adding a new repo

1. Edit Cloud Run env: append to `ALLOWED_REPOS` (comma-separated).
2. The new repo's workflow must accept the same `agent` input field.
3. The bot's `GITHUB_TOKEN` must have access to the new repo.

```bash
gcloud run services update auto-bot --region=asia-northeast3 \
  --update-env-vars ALLOWED_REPOS="repo1,repo2"
```

## Security notes

- `WEBHOOK_SECRET` in the URL path is the only auth — keep it secret.
- The bot ignores any chat that isn't `TELEGRAM_CHAT_ID`.
- `GITHUB_TOKEN` env var is encrypted at rest by Cloud Run; readable only
  by accounts with `roles/run.developer` or higher on the project.
- Best practice: replace the broad-scope `gh auth token` with a
  fine-grained PAT scoped to just `actions:write` on allowed repos.
