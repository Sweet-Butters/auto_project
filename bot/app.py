"""Telegram → GitHub Actions dispatcher (Cloud Run service).

The bot lets you trigger workflows in any allowed repo from your phone.
Deployed once per user; configured by env vars to know which repos and
which Telegram chat are authorized.

Endpoints:
- GET  /                       health check
- POST /telegram/{secret}      Telegram webhook receiver

Commands (sent to the bot in Telegram):
- /help
- /agents [<repo>]
- /run [<repo>] <agent>
- /add [<repo>] <youtube-url>
- /status [<repo>]

Non-command URL routing:
- Any non-command message is scanned for a URL. If the URL matches a
  pattern in URL_ROUTES, the configured workflow is dispatched on the
  configured repo with the URL passed as `input_key`. Lets you share a
  link to the bot and have the right workflow run with no prefix typing.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
DEFAULT_REPO = os.environ.get("DEFAULT_REPO", "").strip()
ALLOWED_REPOS = set(
    r.strip()
    for r in os.environ.get("ALLOWED_REPOS", DEFAULT_REPO).split(",")
    if r.strip()
)
WORKFLOW_FILE = os.environ.get("WORKFLOW_FILE", "agents.yml")
ADD_VIDEO_WORKFLOW = os.environ.get("ADD_VIDEO_WORKFLOW", "add_video.yml")

# URL_ROUTES: JSON array of {pattern, repo, workflow, input_key, extra_inputs?}.
# - pattern: regex matched against the extracted URL (re.search semantics).
# - repo: target full "owner/repo"; must also be present in ALLOWED_REPOS.
# - workflow: workflow filename (e.g. "summarize-video.yml").
# - input_key: name of the workflow input that receives the URL.
# - extra_inputs (optional): dict of additional workflow inputs.
URL_ROUTES = json.loads(os.environ.get("URL_ROUTES", "[]"))


def _tg_send(text: str, parse_mode: str = "HTML") -> None:
    if len(text) > 4000:
        text = text[:3980] + "\n[truncated]"
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
    except Exception:
        # never crash the webhook on a reply failure
        pass


def _gh(method: str, path: str, body: Optional[dict] = None) -> requests.Response:
    return requests.request(
        method,
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=body,
        timeout=15,
    )


def resolve_repo(arg: Optional[str]) -> Optional[str]:
    """Map an argument to a full 'owner/repo' from ALLOWED_REPOS, or None."""
    if not arg:
        return DEFAULT_REPO or None
    if "/" in arg:
        return arg if arg in ALLOWED_REPOS else None
    matches = [r for r in ALLOWED_REPOS if r.split("/", 1)[1] == arg]
    return matches[0] if len(matches) == 1 else None


def cmd_help() -> str:
    routes_summary = (
        "\n".join(
            f"• <code>{r['pattern']}</code> → <code>{r['repo']}/{r['workflow']}</code>"
            for r in URL_ROUTES
        )
        or "(none)"
    )
    return (
        "<b>Available commands</b>\n"
        "<code>/help</code>\n"
        "<code>/agents [&lt;repo&gt;]</code>\n"
        "<code>/run [&lt;repo&gt;] &lt;agent&gt;</code>\n"
        "<code>/add [&lt;repo&gt;] &lt;youtube-url&gt;</code>\n"
        "<code>/status [&lt;repo&gt;]</code>\n\n"
        "Non-command messages with a URL are auto-routed if a pattern matches.\n\n"
        f"Default repo: <code>{DEFAULT_REPO or '(none)'}</code>\n"
        f"Allowed repos: {', '.join(sorted(ALLOWED_REPOS)) or '(none)'}\n"
        f"URL routes:\n{routes_summary}"
    )


def cmd_agents(repo_arg: Optional[str]) -> str:
    if not ALLOWED_REPOS:
        return "no repos configured (set ALLOWED_REPOS env)"
    if repo_arg is None and not DEFAULT_REPO:
        body = "\n".join(f"• <code>{r}</code>" for r in sorted(ALLOWED_REPOS))
        return f"<b>Allowed repos</b>\n{body}\n\nUsage: <code>/agents &lt;repo&gt;</code>"
    full = resolve_repo(repo_arg)
    if not full:
        return f"unknown or disallowed repo: <code>{repo_arg}</code>"
    r = _gh("GET", f"/repos/{full}/contents/agents")
    if r.status_code == 404:
        return f"no <code>agents/</code> directory in <code>{full}</code>"
    if not r.ok:
        return f"GitHub API error {r.status_code}: {r.text[:200]}"
    items = r.json() if isinstance(r.json(), list) else []
    names = sorted(
        i["name"][:-3] for i in items
        if i.get("type") == "file"
        and i.get("name", "").endswith(".py")
        and not i["name"].startswith("__")
    )
    if not names:
        return f"<i>no agents in {full}</i>"
    body = "\n".join(f"• <code>{n}</code>" for n in names)
    return f"<b>Agents in {full}</b>\n{body}"


def cmd_run(repo_arg: Optional[str], agent: str) -> str:
    full = resolve_repo(repo_arg)
    if not full:
        return f"unknown or disallowed repo: <code>{repo_arg}</code>"
    r = _gh(
        "POST",
        f"/repos/{full}/actions/workflows/{WORKFLOW_FILE}/dispatches",
        {"ref": "main", "inputs": {"agent": agent}},
    )
    if r.status_code in (200, 201, 204):
        return f"✅ dispatched <code>{agent}</code> on <code>{full}</code>\n→ check with /status"
    return f"dispatch failed {r.status_code}: {r.text[:200]}"


def cmd_add(repo_arg: Optional[str], url: str) -> str:
    full = resolve_repo(repo_arg)
    if not full:
        return f"unknown or disallowed repo: <code>{repo_arg}</code>"
    r = _gh(
        "POST",
        f"/repos/{full}/actions/workflows/{ADD_VIDEO_WORKFLOW}/dispatches",
        {"ref": "main", "inputs": {"url": url}},
    )
    if r.status_code in (200, 201, 204):
        return (
            f"✅ queued <code>add_video</code> on <code>{full}</code>\n"
            f"url: <code>{url[:80]}</code>\n→ check with /status"
        )
    return f"dispatch failed {r.status_code}: {r.text[:200]}"


def cmd_status(repo_arg: Optional[str]) -> str:
    full = resolve_repo(repo_arg)
    if not full:
        return f"unknown or disallowed repo: <code>{repo_arg}</code>"
    r = _gh("GET", f"/repos/{full}/actions/runs?per_page=5")
    if not r.ok:
        return f"GitHub API error {r.status_code}"
    runs = r.json().get("workflow_runs", [])
    if not runs:
        return "(no runs yet)"
    lines = []
    for run in runs:
        icon = {
            "success": "✅",
            "failure": "❌",
            "in_progress": "⏳",
            "queued": "⌛",
            "cancelled": "✋",
        }.get(run.get("conclusion") or run.get("status"), "•")
        ts = (run.get("run_started_at") or run.get("created_at") or "?")[:19]
        name = run.get("display_title") or run.get("name") or ""
        lines.append(f"{icon} {ts}Z <code>{name[:60]}</code>")
    return f"<b>Recent runs ({full})</b>\n" + "\n".join(lines)


_URL_RE = re.compile(r"https?://\S+")


def _extract_url(text: str) -> Optional[str]:
    """First URL in `text`, trimmed of trailing punctuation Telegram often appends."""
    m = _URL_RE.search(text)
    if not m:
        return None
    return m.group(0).rstrip(".,;:!?)]>}'\"")


def cmd_route_url(url: str, route: dict) -> str:
    repo = route["repo"]
    workflow = route["workflow"]
    input_key = route.get("input_key", "url")
    if repo not in ALLOWED_REPOS:
        return f"⚠️ route repo not in ALLOWED_REPOS: <code>{repo}</code>"
    inputs = {input_key: url}
    inputs.update(route.get("extra_inputs", {}))
    r = _gh(
        "POST",
        f"/repos/{repo}/actions/workflows/{workflow}/dispatches",
        {"ref": "main", "inputs": inputs},
    )
    if r.status_code in (200, 201, 204):
        return (
            f"✅ dispatched <code>{workflow}</code> on <code>{repo}</code>\n"
            f"→ <code>{url[:80]}</code>"
        )
    return f"dispatch failed {r.status_code}: {r.text[:200]}"


def handle_url(text: str) -> Optional[str]:
    """Match a URL in `text` against URL_ROUTES; return reply if dispatched."""
    url = _extract_url(text)
    if not url:
        return None
    for route in URL_ROUTES:
        if re.search(route["pattern"], url):
            return cmd_route_url(url, route)
    return None


def handle(text: str) -> Optional[str]:
    text = (text or "").strip()
    if not text:
        return None
    if not text.startswith("/"):
        return handle_url(text)
    parts = text.split()
    cmd = parts[0].lstrip("/").split("@", 1)[0].lower()  # strip @botname suffix
    args = parts[1:]

    if cmd in ("help", "start"):
        return cmd_help()
    if cmd == "agents":
        return cmd_agents(args[0] if args else None)
    if cmd == "run":
        if len(args) == 1:
            return cmd_run(None, args[0])
        if len(args) >= 2:
            return cmd_run(args[0], args[1])
        return "usage: <code>/run [&lt;repo&gt;] &lt;agent&gt;</code>"
    if cmd == "add":
        if len(args) == 1:
            return cmd_add(None, args[0])
        if len(args) >= 2:
            # First arg is a repo only if it doesn't look like a URL/video id.
            looks_like_url = args[0].startswith(("http://", "https://"))
            if looks_like_url:
                return cmd_add(None, args[0])
            return cmd_add(args[0], args[1])
        return "usage: <code>/add [&lt;repo&gt;] &lt;youtube-url&gt;</code>"
    if cmd == "status":
        return cmd_status(args[0] if args else None)
    return f"unknown command: <code>/{cmd}</code> — try /help"


@app.get("/")
def health():
    return {
        "status": "ok",
        "default_repo": DEFAULT_REPO,
        "allowed_repos": sorted(ALLOWED_REPOS),
        "url_routes": [
            {"pattern": r["pattern"], "repo": r["repo"], "workflow": r["workflow"]}
            for r in URL_ROUTES
        ],
    }


@app.post("/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(403, "invalid secret")
    update = await request.json()
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"ok": True}
    chat_id = msg.get("chat", {}).get("id")
    if chat_id != TELEGRAM_CHAT_ID:
        # silently ignore strangers — don't reveal we exist
        return {"ok": True}

    text = msg.get("text") or ""
    try:
        reply = handle(text)
    except Exception as e:
        reply = f"⚠️ <code>{type(e).__name__}: {str(e)[:200]}</code>"

    if reply:
        _tg_send(reply)
    return {"ok": True}
