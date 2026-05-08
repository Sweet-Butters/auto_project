"""One-way Telegram notifications for agents.

Silent no-op when TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set, so
agents can call `notify.telegram(...)` unconditionally. The framework
itself never raises on a notify failure — observability shouldn't break
the agent it's reporting on.

Stable API:
    notify.telegram(message: str, parse_mode: str = "HTML") -> bool
    notify.escape(text: str) -> str
"""

from __future__ import annotations

import html as _html
import logging
import os

import requests

log = logging.getLogger(__name__)

_API = "https://api.telegram.org"
_MAX_MESSAGE = 4000  # Telegram caps at 4096; leave headroom for the suffix


def escape(text: str) -> str:
    """Escape text for Telegram's HTML parse_mode."""
    return _html.escape(text or "")


def telegram(message: str, parse_mode: str = "HTML", timeout: int = 10) -> bool:
    """Send `message` to the configured chat. Returns True on success.

    Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from env. Returns
    False (without raising) if either is unset or the request fails.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("notify.telegram: TELEGRAM_BOT_TOKEN/CHAT_ID not set, skipping")
        return False

    if len(message) > _MAX_MESSAGE:
        message = message[: _MAX_MESSAGE - 20] + "\n[truncated]"

    try:
        r = requests.post(
            f"{_API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": parse_mode},
            timeout=timeout,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.warning("notify.telegram failed: %s", e)
        return False
