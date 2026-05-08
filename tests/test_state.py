"""Tests for cwd-isolated state."""

import json
import os
from pathlib import Path

import pytest

from auto_project import state


@pytest.fixture
def in_tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_get_returns_default_when_missing(in_tmp_cwd):
    assert state.get("agent", "key") is None
    assert state.get("agent", "key", default=42) == 42


def test_set_then_get_round_trip(in_tmp_cwd):
    state.set("alpha", "config", {"x": 1, "y": "hi"})
    assert state.get("alpha", "config") == {"x": 1, "y": "hi"}


def test_state_writes_to_cwd(in_tmp_cwd):
    state.set("beta", "k", [1, 2, 3])
    expected = in_tmp_cwd / "state" / "beta" / "k.json"
    assert expected.exists()
    assert json.loads(expected.read_text()) == [1, 2, 3]


def test_isolation_between_cwds(tmp_path, monkeypatch):
    a = tmp_path / "proj_a"
    b = tmp_path / "proj_b"
    a.mkdir()
    b.mkdir()

    monkeypatch.chdir(a)
    state.set("agent", "k", "from_a")

    monkeypatch.chdir(b)
    assert state.get("agent", "k") is None  # b cannot see a's state
    state.set("agent", "k", "from_b")

    monkeypatch.chdir(a)
    assert state.get("agent", "k") == "from_a"  # a's state untouched


def test_unicode_round_trip(in_tmp_cwd):
    state.set("agent", "kr", {"text": "안녕하세요 🌏"})
    assert state.get("agent", "kr") == {"text": "안녕하세요 🌏"}


def test_set_creates_nested_directories(in_tmp_cwd):
    # state/<agent>/<key>.json — both dirs may not exist yet
    state.set("new_agent", "fresh_key", "value")
    assert (in_tmp_cwd / "state" / "new_agent" / "fresh_key.json").exists()
