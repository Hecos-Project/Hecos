"""
MODULE: Messenger Plugin — Main Entry Point
DESCRIPTION: Exposes MessengerTools to the Hecos agent loop.
             Tools: send_message, list_accounts, check_connection, force_send.
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

from .messenger_config.config_manager import get_config_obj
from . import dispatcher


class MessengerTools:
    """
    Hecos Messenger Plugin — send messages via Telegram, WhatsApp, and Discord.
    """

    def __init__(self):
        self.tag    = "MESSENGER"
        self.desc   = "Send messages via Telegram, WhatsApp, and Discord."
        self.status = "ONLINE"
        self._cfg   = None

    def _require_config(self):
        if self._cfg is None:
            self._cfg = get_config_obj()
        return self._cfg

    def send_message(self, to: str, text: str, platform: str = None, skip_default_template: bool = False, is_app_open: bool = False) -> str:
        """
        Send a message to a contact or channel.
        """
        cfg = self._require_config()
        try:
            plat, recipient = dispatcher.parse_target(to, platform)
        except ValueError as e:
            return f"❌ {e}"

        # Check explicit template via config
        explicit_template_id = ""
        if plat == "whatsapp" and getattr(cfg.whatsapp, "use_template", False):
            explicit_template_id = getattr(cfg.whatsapp, "template_id", "")

        # Try to apply template wrapper if not skipped
        if not skip_default_template:
            try:
                from hecos.plugins.templates.store import list_templates, get_template
                
                template_to_apply = None
                if explicit_template_id:
                    template_to_apply = get_template(explicit_template_id)
                else:
                    for t in list_templates(channel=plat):
                        if t.get("is_default"):
                            template_to_apply = t
                            break

                if template_to_apply:
                    h = template_to_apply.get("header", "").strip()
                    f = template_to_apply.get("footer", "").strip()
                    parts = []
                    if h: parts.append(h)
                    parts.append(text)
                    if f: parts.append(f)
                    text = "\n\n".join(parts)
            except Exception as e:
                logger.warning("MESSENGER", f"Error applying template: {e}")

        return dispatcher.dispatch_send(plat, recipient, text, cfg, is_app_open)

    def msg_command(self, args: str) -> str:
        """
        Direct command invoked via /msg <target> <text>
        """
        if not args or " " not in args:
            return "❌ Errore: Sintassi '/msg <piattaforma:destinatario> <testo>'. Esempio: '/msg telegram:@utente ciao'"
        
        target, text = args.split(" ", 1)
        return self.send_message(to=target, text=text)

    def list_accounts(self) -> str:
        cfg = self._require_config()
        lines = [translator.t("ext_messenger_accounts_title") + "\n"]

        # Telegram
        tg_status = "✅ Abilitato" if getattr(cfg.telegram, 'enabled', False) else "⛔ Disabilitato"
        tg_tk = getattr(cfg.telegram, 'bot_token', "")
        tg_id = f"(Token: {'***' + tg_tk[-6:] if tg_tk else 'non impostato'})"
        lines.append(f"📨 **Telegram**: {tg_status} {tg_id}")

        # WhatsApp
        wa_status = "✅ Abilitato [BETA]" if getattr(cfg.whatsapp, 'enabled', False) else "⛔ Disabilitato"
        lines.append(f"💬 **WhatsApp**: {wa_status}")

        # Discord
        dc_status = "✅ Abilitato" if getattr(cfg.discord, 'enabled', False) else "⛔ Disabilitato"
        dc_w = getattr(cfg.discord, 'webhook_url', "")
        dc_wh = "(webhook configurato)" if dc_w else "(nessun webhook)"
        lines.append(f"🔵 **Discord**: {dc_status} {dc_wh}")

        return "\n".join(lines)

    def check_connection(self, platform: str = None) -> str:
        cfg = self._require_config()
        results = dispatcher.dispatch_check(platform, cfg)

        if platform:
            status = results.get(platform.lower(), "UNKNOWN")
            icon = "✅" if "ONLINE" in status or "BETA" in status else "❌"
            return f"{icon} **{platform.capitalize()}**: {status}"

        lines = [translator.t("ext_messenger_check_title") + "\n"]
        icons = {"ONLINE": "✅", "BETA": "🟡", "DISABLED": "⛔", "NOT": "⚠️", "ERROR": "❌"}
        for pname, st in results.items():
            icon = next((v for k, v in icons.items() if k in st.upper()), "❓")
            lines.append(f"{icon} **{pname.capitalize()}**: {st}")

        return "\n".join(lines)

    def force_send(self) -> str:
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
    tools._cfg = get_config_obj()
    cfg = tools._cfg
    enabled_providers = [
        p for p in ("telegram", "whatsapp", "discord")
        if getattr(getattr(cfg, p, None), "enabled", False)
    ]

    if enabled_providers:
        logger.info("MESSENGER", f"Plugin loaded — active providers: {', '.join(enabled_providers)}")
        tools.status = "ONLINE"
    else:
        logger.info("MESSENGER", "Plugin loaded — no providers configured (disabled mode).")
        tools.status = "DEGRADED"
