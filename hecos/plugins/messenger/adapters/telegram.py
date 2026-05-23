"""
MODULE: Messenger — Telegram Adapter
DESCRIPTION: Sends messages via the Telegram Bot API using python-telegram-bot v20+.
             Falls back gracefully if the library is not installed.
             Runs async coroutines via asyncio.run() for compatibility with
             Hecos's synchronous tool executor.
"""

from __future__ import annotations
import asyncio
from hecos.core.logging import logger

_MISSING = "❌ Telegram: 'python-telegram-bot' is not installed. Run: pip install python-telegram-bot"


def _get_bot(cfg):
    """Return a Bot instance or raise ImportError with a friendly message."""
    try:
        from telegram import Bot  # python-telegram-bot v20+
        return Bot(token=cfg.bot_token)
    except ImportError:
        raise RuntimeError(_MISSING)


def _resolve_chat(cfg, recipient: str) -> str:
    """
    Resolve final chat_id.
    - If recipient is numeric or starts with @   → use as-is.
    - If recipient is empty                       → use default_chat_id from config.
    """
    r = recipient.strip()
    if r:
        return r
    if cfg.default_chat_id:
        return cfg.default_chat_id
    raise ValueError("Telegram: no recipient and no default_chat_id configured.")


def send(cfg, recipient: str, text: str) -> str:
    """Synchronous entry point called by the dispatcher."""
    if not cfg.enabled:
        return "⚠️ Telegram adapter is disabled. Enable it in Messenger settings."
    if not cfg.bot_token:
        return "⚠️ Telegram: bot_token is not configured. Add it in Central Hub → Messenger → Telegram."

    try:
        chat_id = _resolve_chat(cfg, recipient)
        bot = _get_bot(cfg)

        async def _send():
            async with bot:
                await bot.send_message(chat_id=chat_id, text=text)

        asyncio.run(_send())
        logger.info("MESSENGER/Telegram", f"Message sent to {chat_id}")
        return f"✅ Messaggio Telegram inviato a `{chat_id}`."

    except RuntimeError as e:
        return str(e)
    except Exception as e:
        logger.warning("MESSENGER/Telegram", f"Send failed: {e}")
        return f"❌ Telegram send error: {e}"


def check(cfg) -> str:
    """
    Test the Telegram connection by calling getMe.
    Returns a status string.
    """
    if not cfg.enabled:
        return "DISABLED"
    if not cfg.bot_token:
        return "NOT CONFIGURED (missing bot_token)"

    try:
        bot = _get_bot(cfg)

        async def _check():
            async with bot:
                me = await bot.get_me()
                return me.username

        username = asyncio.run(_check())
        logger.info("MESSENGER/Telegram", f"Connection OK — bot: @{username}")
        return f"ONLINE (@{username})"

    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"ERROR: {e}"
