"""
MODULE: Messenger Plugin — Main Entry Point
DESCRIPTION: Exposes MessengerTools to the Hecos agent loop.
             Tools: send_message, list_accounts, check_connection.
             Providers (Telegram, WhatsApp, Discord) are loaded lazily
             from the dispatcher on first use.
"""

from __future__ import annotations
from hecos.core.logging import logger

try:
    from hecos.core.i18n import translator
except ImportError:
    class _DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = _DummyTranslator()

from hecos.plugins.messenger.config import parse_config, MessengerConfig
from hecos.plugins.messenger import dispatcher


class MessengerTools:
    """
    Hecos Messenger Plugin — send messages via Telegram, WhatsApp, and Discord.
    Platform is chosen automatically from the 'to' address prefix.
    """

    def __init__(self):
        self.tag    = "MESSENGER"
        self.desc   = "Send messages via Telegram, WhatsApp, and Discord."
        self.status = "ONLINE"
        self._cfg: MessengerConfig | None = None

        # ── Config schema (drives the Central Hub UI) ──────────────────────
        self.config_schema = {
            # ── Telegram ───────────────────────────────────────────────────
            "telegram_enabled": {
                "type": "bool",
                "default": False,
                "description": "Enable Telegram messaging via Bot API."
            },
            "telegram_bot_token": {
                "type": "str",
                "default": "",
                "description": "Telegram Bot token from @BotFather (e.g. '1234567890:ABC...'). Keep this private."
            },
            "telegram_default_chat_id": {
                "type": "str",
                "default": "",
                "description": "Default Telegram chat/channel ID. Used when recipient is omitted."
            },
            # ── WhatsApp ───────────────────────────────────────────────────
            "whatsapp_enabled": {
                "type": "bool",
                "default": False,
                "description": "[BETA] Enable WhatsApp messaging via pywhatkit (browser-based)."
            },
            "whatsapp_phone_country_code": {
                "type": "str",
                "default": "+39",
                "description": "Default country code prepended to bare phone numbers (e.g. '+39' for Italy)."
            },
            "whatsapp_send_as_single_block": {
                "type": "bool",
                "default": True,
                "description": "Send multiline text and templates as a single message block instead of multiple separate messages."
            },
            # ── Discord ────────────────────────────────────────────────────
            "discord_enabled": {
                "type": "bool",
                "default": False,
                "description": "Enable Discord messaging via Incoming Webhook."
            },
            "discord_webhook_url": {
                "type": "str",
                "default": "",
                "description": "Discord Incoming Webhook URL from Server Settings → Integrations → Webhooks."
            },
            "discord_default_channel": {
                "type": "str",
                "default": "",
                "description": "Optional: default channel name shown in confirmation messages."
            },
        }

    # ── Internal helpers ───────────────────────────────────────────────────

    def _require_config(self) -> MessengerConfig:
        if self._cfg is None:
            raise RuntimeError("MESSENGER plugin not loaded. Call on_load() first.")
        return self._cfg

    # ── Public Tools ───────────────────────────────────────────────────────

    def send_message(self, to: str, text: str, platform: str = None, skip_default_template: bool = False, is_app_open: bool = False) -> str:
        """
        Send a message to a contact or channel.
        :param to: Recipient with optional platform prefix.
                   Examples: 'telegram:@hecos_bot', 'whatsapp:+393331234567',
                             'discord:#general', '+393331234567' (with platform=whatsapp).
        :param text: Message body.
        :param platform: Optional platform override if 'to' has no prefix.
        :param skip_default_template: Set to True if you already rendered a template manually via TemplateTools.
        """
        cfg = self._require_config()
        try:
            plat, recipient = dispatcher.parse_target(to, platform)
        except ValueError as e:
            return f"❌ {e}"

        # Try to apply default template wrapper if not skipped
        if not skip_default_template:
            try:
                from hecos.plugins.templates.store import list_templates
                for t in list_templates(channel=plat):
                    if t.get("is_default"):
                        h = t.get("header", "").strip()
                        f = t.get("footer", "").strip()
                        parts = []
                        if h: parts.append(h)
                        parts.append(text)
                        if f: parts.append(f)
                        text = "\n\n".join(parts)
                        break
            except Exception:
                pass

        return dispatcher.dispatch_send(plat, recipient, text, cfg, is_app_open)

    def list_accounts(self) -> str:
        """
        List all configured messaging providers and their status.
        """
        cfg = self._require_config()

        lines = [translator.t("ext_messenger_accounts_title") + "\n"]

        # Telegram
        tg_status = "✅ Abilitato" if cfg.telegram.enabled else "⛔ Disabilitato"
        tg_id = f"(Token: {'***' + cfg.telegram.bot_token[-6:] if cfg.telegram.bot_token else 'non impostato'})"
        lines.append(f"📨 **Telegram**: {tg_status} {tg_id}")

        # WhatsApp
        wa_status = "✅ Abilitato [BETA]" if cfg.whatsapp.enabled else "⛔ Disabilitato"
        lines.append(f"💬 **WhatsApp**: {wa_status}")

        # Discord
        dc_status = "✅ Abilitato" if cfg.discord.enabled else "⛔ Disabilitato"
        dc_wh = "(webhook configurato)" if cfg.discord.webhook_url else "(nessun webhook)"
        lines.append(f"🔵 **Discord**: {dc_status} {dc_wh}")

        return "\n".join(lines)

    def check_connection(self, platform: str = None) -> str:
        """
        Test the connection to one or all messaging providers.
        :param platform: Optional. 'telegram', 'whatsapp', or 'discord'. If omitted, tests all.
        """
        cfg = self._require_config()
        results = dispatcher.dispatch_check(platform, cfg)

        if platform:
            status = results.get(platform, "UNKNOWN")
            icon = "✅" if "ONLINE" in status or "BETA" in status else "❌"
            return f"{icon} **{platform.capitalize()}**: {status}"

        lines = [translator.t("ext_messenger_check_title") + "\n"]
        icons = {"ONLINE": "✅", "BETA": "🟡", "DISABLED": "⛔",
                 "NOT": "⚠️", "ERROR": "❌"}
        for pname, st in results.items():
            icon = next((v for k, v in icons.items() if k in st.upper()), "❓")
            lines.append(f"{icon} **{pname.capitalize()}**: {st}")

        return "\n".join(lines)

    def force_send(self) -> str:
        """
        Force-send by simulating an 'Enter' keystroke. Useful if WhatsApp Web gets stuck.
        """
        try:
            import pyautogui  # type: ignore
            pyautogui.press('enter')
            return "✅ Ho simulato la pressione del tasto Invio (Forzatura invio)."
        except ImportError:
            return "❌ Impossibile forzare l'invio: pyautogui non è installato."
        except Exception as e:
            return f"❌ Errore durante force_send: {e}"


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = MessengerTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status


def on_load(config: dict = None):
    """Called by the plugin loader when Hecos starts."""
    raw = config or {}
    # The scanner passes the FULL system config. Extract our own slice.
    plugin_cfg = raw.get("plugins", {}).get("MESSENGER", raw)
    nested = {
        "telegram": {
            "enabled":         plugin_cfg.get("telegram_enabled", False),
            "bot_token":       plugin_cfg.get("telegram_bot_token", ""),
            "default_chat_id": plugin_cfg.get("telegram_default_chat_id", ""),
        },
        "whatsapp": {
            "enabled":              plugin_cfg.get("whatsapp_enabled", False),
            "phone_country_code":   plugin_cfg.get("whatsapp_phone_country_code", "+39"),
            "send_as_single_block": plugin_cfg.get("whatsapp_send_as_single_block", True),
        },
        "discord": {
            "enabled":          plugin_cfg.get("discord_enabled", False),
            "webhook_url":      plugin_cfg.get("discord_webhook_url", ""),
            "default_channel":  plugin_cfg.get("discord_default_channel", ""),
        },
    }

    tools._cfg = parse_config(nested)
    enabled_providers = [
        p for p in ("telegram", "whatsapp", "discord")
        if getattr(tools._cfg, p).enabled
    ]

    if enabled_providers:
        logger.info("MESSENGER", f"Plugin loaded — active providers: {', '.join(enabled_providers)}")
        tools.status = "ONLINE"
    else:
        logger.info("MESSENGER", "Plugin loaded — no providers configured (disabled mode).")
        tools.status = "DEGRADED"
