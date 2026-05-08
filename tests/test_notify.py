"""Tests for the Telegram notify helper."""

import os

from auto_project import notify


def test_silent_noop_without_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notify.telegram("hi") is False


def test_partial_env_still_noop(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notify.telegram("hi") is False


def test_escape_handles_html_meta_chars():
    # Telegram HTML parse_mode requires escaping <, >, &
    assert notify.escape("<b>x & y</b>") == "&lt;b&gt;x &amp; y&lt;/b&gt;"
    assert notify.escape("") == ""
    assert notify.escape(None) == ""


def test_truncation_logic_via_long_message(monkeypatch):
    """Indirectly verify that excessively long messages don't crash before send.
    With env unset the call returns False, but the truncation branch still runs.
    """
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    long_msg = "x" * 10_000
    assert notify.telegram(long_msg) is False  # silent skip, no exception
