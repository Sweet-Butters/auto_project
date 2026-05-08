"""Tests for the multi-provider LLM router."""

import os
from unittest.mock import patch

import pytest

from auto_project import llm


def test_mock_mode_short_circuits():
    with patch.dict(os.environ, {"MOCK_LLM": "1"}, clear=False):
        assert llm.call("hello world").startswith("[mock]")


def test_no_keys_raises_with_clear_message(monkeypatch):
    for k in ("MOCK_LLM", "GEMINI_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError) as exc:
        llm.call("anything")
    msg = str(exc.value)
    assert "all LLM providers failed" in msg
    assert "no key" in msg


def test_falls_through_to_second_provider_on_rate_limit(monkeypatch):
    """If the first provider with a key raises RateLimitError, the next one runs."""
    monkeypatch.delenv("MOCK_LLM", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    calls = []

    def fake_gemini(prompt, system, timeout):
        calls.append("gemini")
        raise llm.RateLimitError("simulated")

    def fake_groq(prompt, system, timeout):
        calls.append("groq")
        return "groq-response"

    monkeypatch.setattr(llm, "PROVIDERS", [fake_gemini, fake_groq])
    assert llm.call("x") == "groq-response"
    assert calls == ["gemini", "groq"]


def test_skips_provider_without_key(monkeypatch):
    """A provider that raises NoKeyError should be skipped without aborting."""
    monkeypatch.delenv("MOCK_LLM", raising=False)
    calls = []

    def no_key(prompt, system, timeout):
        calls.append("no_key")
        raise llm.NoKeyError("missing")

    def has_key(prompt, system, timeout):
        calls.append("has_key")
        return "ok"

    monkeypatch.setattr(llm, "PROVIDERS", [no_key, has_key])
    assert llm.call("x") == "ok"
    assert calls == ["no_key", "has_key"]
