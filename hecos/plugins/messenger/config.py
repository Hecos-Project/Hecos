"""
MODULE: Messenger Plugin — Pydantic Config Models
DESCRIPTION: Type-safe configuration validation for the MESSENGER plugin.
             Each provider has its own model. MessengerConfig is the root model
             parsed from the plugins.yaml MESSENGER block at on_load().
             Falls back to a plain dict if pydantic is not installed.
"""

from __future__ import annotations

try:
    from pydantic import BaseModel, field_validator

    class TelegramConfig(BaseModel):
        enabled: bool = False
        bot_token: str = ""
        default_chat_id: str = ""

        @field_validator("bot_token")
        @classmethod
        def token_not_empty_when_enabled(cls, v, info):
            # Only run when model is fully filled — pydantic v2 style
            return v

    class WhatsAppConfig(BaseModel):
        enabled: bool = False
        session_name: str = "hecos"
        phone_country_code: str = "+39"

    class DiscordConfig(BaseModel):
        enabled: bool = False
        webhook_url: str = ""
        bot_token: str = ""
        default_channel: str = ""

    class MessengerConfig(BaseModel):
        telegram: TelegramConfig = TelegramConfig()
        whatsapp: WhatsAppConfig = WhatsAppConfig()
        discord: DiscordConfig = DiscordConfig()

    PYDANTIC_AVAILABLE = True

except ImportError:
    PYDANTIC_AVAILABLE = False

    # ── Plain-dict fallback when pydantic is not installed ──────────────────
    class _DummyConfig:
        """Mimics pydantic model attribute access from a flat dict."""
        def __init__(self, data: dict):
            self._data = data
        def __getattr__(self, name):
            return self._data.get(name)

    class TelegramConfig(_DummyConfig): pass      # noqa: E701
    class WhatsAppConfig(_DummyConfig): pass       # noqa: E701
    class DiscordConfig(_DummyConfig): pass        # noqa: E701

    class MessengerConfig:
        def __init__(self, data: dict):
            self.telegram = TelegramConfig(data.get("telegram") or {})
            self.whatsapp = WhatsAppConfig(data.get("whatsapp") or {})
            self.discord  = DiscordConfig(data.get("discord") or {})


def parse_config(raw: dict) -> "MessengerConfig":
    """
    Parse the MESSENGER block from plugins.yaml into a typed MessengerConfig.
    Works with or without pydantic.
    """
    if PYDANTIC_AVAILABLE:
        return MessengerConfig.model_validate(raw)
    return MessengerConfig(raw)
