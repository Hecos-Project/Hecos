"""
MODULE: Messenger — Discord Adapter
DESCRIPTION: Sends messages to a Discord channel via Incoming Webhook (primary)
             or Bot API (fallback). Webhooks require zero bot permission setup;
             just paste the webhook URL from Server Settings → Integrations.

WEBHOOK URL FORMAT: https://discord.com/api/webhooks/<id>/<token>
"""

from __future__ import annotations
import urllib.request
import urllib.parse
import json
from hecos.core.logging import logger


def _resolve_channel(cfg, recipient: str) -> str | None:
    """
    Return a webhook URL or channel identifer from the recipient string.
    Accepts:
      - '#general'            → uses webhook_url from config
      - 'https://discord...'  → used directly as webhook URL
    """
    r = recipient.strip()
    if r.startswith("https://discord.com/api/webhooks/"):
        return r
    # Channel name hint — use default webhook
    if cfg.webhook_url:
        return cfg.webhook_url
    return None


def send(cfg, recipient: str, text: str) -> str:
    """POST a message via Discord Incoming Webhook."""
    if not cfg.enabled:
        return "⚠️ Discord adapter is disabled. Enable it in Messenger settings."

    webhook_url = _resolve_channel(cfg, recipient)
    if not webhook_url:
        return (
            "⚠️ Discord: no webhook_url configured. "
            "Add it in Central Hub → Messenger → Discord."
        )

    payload = json.dumps({"content": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.getcode()
            if code in (200, 204):
                logger.info("MESSENGER/Discord", f"Webhook sent to {recipient or 'default channel'}")
                target = recipient.strip() or "canale predefinito"
                return f"✅ Messaggio Discord inviato su `{target}`."
            else:
                return f"❌ Discord webhook returned HTTP {code}."
    except Exception as e:
        logger.warning("MESSENGER/Discord", f"Send failed: {e}")
        return f"❌ Discord send error: {e}"


def check(cfg) -> str:
    """Verify the webhook URL with a GET request (Discord returns 200 + webhook info)."""
    if not cfg.enabled:
        return "DISABLED"
    if not cfg.webhook_url:
        return "NOT CONFIGURED (missing webhook_url)"

    try:
        req = urllib.request.Request(cfg.webhook_url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read())
                name = data.get("name", "unknown")
                return f"ONLINE (webhook: #{name})"
            return f"HTTP {resp.getcode()}"
    except Exception as e:
        return f"ERROR: {e}"
