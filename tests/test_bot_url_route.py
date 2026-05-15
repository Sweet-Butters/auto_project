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
