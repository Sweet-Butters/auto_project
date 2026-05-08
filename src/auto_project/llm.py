"""Multi-provider LLM router with free-tier fallback.

Order: Gemini -> Groq -> Cerebras. First one with a valid key and no
rate-limit error wins. Add a provider by writing one function and
appending it to PROVIDERS.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import requests


class RateLimitError(Exception):
    pass


class NoKeyError(Exception):
    pass


def _gemini(prompt: str, system: Optional[str], timeout: int) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise NoKeyError("GEMINI_API_KEY not set")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = requests.post(url, json=body, timeout=timeout)
    if r.status_code == 429:
        raise RateLimitError("gemini 429")
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _openai_compatible(base_url: str, env_key: str, default_model: str, env_model: str):
    """Build a provider for an OpenAI-compatible endpoint (Groq, Cerebras, etc)."""

    def call(prompt: str, system: Optional[str], timeout: int) -> str:
        key = os.environ.get(env_key)
        if not key:
            raise NoKeyError(f"{env_key} not set")
        model = os.environ.get(env_model, default_model)
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        r = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": msgs},
            timeout=timeout,
        )
        if r.status_code == 429:
            raise RateLimitError(f"{env_key} 429")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    call.__name__ = env_key.lower().replace("_api_key", "")
    return call


_groq = _openai_compatible(
    "https://api.groq.com/openai/v1",
    "GROQ_API_KEY",
    "llama-3.3-70b-versatile",
    "GROQ_MODEL",
)

_cerebras = _openai_compatible(
    "https://api.cerebras.ai/v1",
    "CEREBRAS_API_KEY",
    "llama3.1-8b",
    "CEREBRAS_MODEL",
)


PROVIDERS = [_gemini, _groq, _cerebras]


def call(prompt: str, system: Optional[str] = None, timeout: int = 60) -> str:
    """Try each provider until one succeeds. Raises RuntimeError if all fail."""
    if os.environ.get("MOCK_LLM") == "1":
        return f"[mock] {prompt[:80]}"

    errors = []
    for provider in PROVIDERS:
        try:
            return provider(prompt, system, timeout)
        except NoKeyError as e:
            errors.append(f"{provider.__name__}: no key")
            continue
        except RateLimitError as e:
            errors.append(f"{provider.__name__}: rate limited")
            continue
        except Exception as e:
            errors.append(f"{provider.__name__}: {type(e).__name__}: {str(e)[:120]}")
            continue
    raise RuntimeError("all LLM providers failed:\n  " + "\n  ".join(errors))
