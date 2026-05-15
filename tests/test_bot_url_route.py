"""Tests for the bot's URL extraction + routing dispatcher.

The bot module reads env vars at import time. We set fake values via the
`bot_app` fixture before importing, and use importlib.util to load `app.py`
directly (the file isn't a package and has no __init__.py).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

BOT_PATH = Path(__file__).resolve().parents[1] / "bot" / "app.py"


@pytest.fixture
def bot_app(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "test_secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("GITHUB_TOKEN", "test_gh")
    monkeypatch.setenv("DEFAULT_REPO", "owner/notes_project")
    monkeypatch.setenv("ALLOWED_REPOS", "owner/notes_project")
    monkeypatch.setenv(
        "URL_ROUTES",
        '[{"pattern":"(?:youtube\\\\.com/watch|youtu\\\\.be/)",'
        '"repo":"owner/notes_project",'
        '"workflow":"summarize-video.yml",'
        '"input_key":"url",'
        '"extra_inputs":{"display_lang":"ko"}}]',
    )
    spec = importlib.util.spec_from_file_location("bot_app_under_test", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot_app_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("bot_app_under_test", None)


def test_extract_url_simple(bot_app):
    assert bot_app._extract_url("https://youtu.be/abc123") == "https://youtu.be/abc123"


def test_extract_url_with_trailing_punct(bot_app):
    assert (
        bot_app._extract_url("check this: https://youtu.be/abc123.")
        == "https://youtu.be/abc123"
    )


def test_extract_url_with_query(bot_app):
    url = "https://www.youtube.com/watch?v=-mer0_qTj2A&t=233s"
    assert bot_app._extract_url(f"link: {url}") == url


def test_extract_url_none(bot_app):
    assert bot_app._extract_url("no urls here") is None


def test_handle_url_no_match_returns_none(bot_app):
    assert bot_app.handle_url("https://example.com/something") is None


def test_handle_url_matches_youtube(bot_app, monkeypatch):
    calls = {}

    class FakeResp:
        status_code = 204
        text = ""

    def fake_gh(method, path, body=None):
        calls["method"] = method
        calls["path"] = path
        calls["body"] = body
        return FakeResp()

    monkeypatch.setattr(bot_app, "_gh", fake_gh)
    reply = bot_app.handle_url(
        "https://www.youtube.com/watch?v=-mer0_qTj2A&t=233s"
    )
    assert reply is not None
    assert "summarize-video.yml" in reply
    assert calls["path"] == (
        "/repos/owner/notes_project/actions/workflows/summarize-video.yml/dispatches"
    )
    assert calls["body"]["inputs"]["url"].startswith("https://www.youtube.com/")
    assert calls["body"]["inputs"]["display_lang"] == "ko"


def test_handle_dispatches_url_message(bot_app, monkeypatch):
    class FakeResp:
        status_code = 204
        text = ""

    monkeypatch.setattr(bot_app, "_gh", lambda *a, **k: FakeResp())
    assert bot_app.handle("https://www.youtube.com/watch?v=abc123XYZ45") is not None


def test_handle_command_still_works(bot_app):
    out = bot_app.handle("/help")
    assert "Available commands" in out


# ----------------------------------------------------------------------------
# Hybrid routing — fallback workflow when no self-hosted runner is online
# ----------------------------------------------------------------------------

@pytest.fixture
def hybrid_bot_app(monkeypatch):
    """Like bot_app but URL_ROUTES has a fallback_workflow configured."""
    monkeypatch.setenv("WEBHOOK_SECRET", "test_secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("GITHUB_TOKEN", "test_gh")
    monkeypatch.setenv("DEFAULT_REPO", "owner/notes_project")
    monkeypatch.setenv("ALLOWED_REPOS", "owner/notes_project")
    monkeypatch.setenv(
        "URL_ROUTES",
        '[{"pattern":"youtu",'  # matches both youtube.com and youtu.be
        '"repo":"owner/notes_project",'
        '"workflow":"summarize-video.yml",'
        '"fallback_workflow":"summarize-video-fallback.yml",'
        '"input_key":"url",'
        '"extra_inputs":{"display_lang":"ko"}}]',
    )
    spec = importlib.util.spec_from_file_location("bot_app_hybrid_under_test", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot_app_hybrid_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("bot_app_hybrid_under_test", None)


def _fake_gh_factory(runner_status: str | None, dispatch_calls: list):
    """Build a fake _gh that returns runner-list for GET and 204 for POST.

    runner_status: 'online', 'offline', or None (empty list)
    dispatch_calls: list that records every POST call's body for assertion.
    """
    runners = []
    if runner_status:
        runners = [{"id": 1, "name": "r", "status": runner_status, "labels": []}]

    class Resp:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self.text = ""
            self.ok = 200 <= status_code < 300
            self._payload = payload

        def json(self):
            return self._payload

    def fake_gh(method, path, body=None):
        if method == "GET" and "/runners" in path:
            return Resp(200, {"total_count": len(runners), "runners": runners})
        if method == "POST" and "/dispatches" in path:
            dispatch_calls.append({"path": path, "body": body})
            return Resp(204)
        return Resp(404)

    return fake_gh


def test_hybrid_uses_primary_when_runner_online(hybrid_bot_app, monkeypatch):
    calls = []
    monkeypatch.setattr(hybrid_bot_app, "_gh", _fake_gh_factory("online", calls))
    reply = hybrid_bot_app.handle_url("https://youtu.be/abc123XYZ45")
    assert reply is not None
    assert len(calls) == 1
    assert "summarize-video.yml" in calls[0]["path"]
    assert "fallback" not in calls[0]["path"]


def test_hybrid_uses_fallback_when_no_runner_online(hybrid_bot_app, monkeypatch):
    calls = []
    monkeypatch.setattr(hybrid_bot_app, "_gh", _fake_gh_factory(None, calls))
    reply = hybrid_bot_app.handle_url("https://youtu.be/abc123XYZ45")
    assert reply is not None
    assert "summarize-video-fallback.yml" in calls[0]["path"]
    assert "fallback" in reply.lower()  # reply mentions fallback usage


def test_hybrid_uses_fallback_when_runner_offline(hybrid_bot_app, monkeypatch):
    calls = []
    monkeypatch.setattr(hybrid_bot_app, "_gh", _fake_gh_factory("offline", calls))
    reply = hybrid_bot_app.handle_url("https://youtu.be/abc123XYZ45")
    assert reply is not None
    assert "summarize-video-fallback.yml" in calls[0]["path"]


def test_hybrid_assumes_online_on_network_error(hybrid_bot_app, monkeypatch):
    """If the runner-status API call raises, assume online (don't fall back)."""
    calls = []

    def raise_then_ok(method, path, body=None):
        if method == "GET":
            raise RuntimeError("network error")
        calls.append({"path": path, "body": body})

        class Resp:
            status_code = 204
            text = ""
            ok = True
        return Resp()

    monkeypatch.setattr(hybrid_bot_app, "_gh", raise_then_ok)
    reply = hybrid_bot_app.handle_url("https://youtu.be/abc123XYZ45")
    assert reply is not None
    # network error → assume online → use primary
    assert "summarize-video.yml" in calls[0]["path"]
    assert "summarize-video-fallback.yml" not in calls[0]["path"]


def test_non_hybrid_route_still_works(bot_app, monkeypatch):
    """Routes without fallback_workflow never call the runner-status API."""
    calls = []

    def fake_gh(method, path, body=None):
        calls.append({"method": method, "path": path})

        class Resp:
            status_code = 204
            text = ""
            ok = True
        return Resp()

    monkeypatch.setattr(bot_app, "_gh", fake_gh)
    bot_app.handle_url("https://www.youtube.com/watch?v=abc123XYZ45")
    # Only the dispatch POST call — no GET to /runners
    assert all(c["method"] == "POST" for c in calls)
    assert all("/runners" not in c["path"] for c in calls)
