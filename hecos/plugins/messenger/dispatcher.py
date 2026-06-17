"""
MODULE: Messenger Plugin — Dispatcher
DESCRIPTION: Routes a send_message or check_connection call to the correct
             provider adapter based on the 'to' address or the 'platform' arg.
             Address format: 'platform:recipient'  (e.g. 'telegram:@hecos')
"""

from __future__ import annotations
from hecos.core.logging import logger

PLATFORM_PREFIXES = ("telegram", "whatsapp", "discord")


def parse_target(to: str, platform: str = None) -> tuple[str, str]:
    """
    Parse the target string and return (platform, recipient).

    Accepts:
        - 'telegram:@username'  → ('telegram', '@username')
        - 'discord:#general'    → ('discord', '#general')
        - '+393331234567'       → if platform='whatsapp' → ('whatsapp', '+393331234567')
        - 'just a name'         → (platform, 'just a name')  if platform is given
    """
    if ":" in to:
        prefix, _, recipient = to.partition(":")
        prefix = prefix.strip().lower()
        if prefix in PLATFORM_PREFIXES:
            return prefix, recipient.strip()

    # No prefix — use explicit platform or raise
    if platform and platform.lower() in PLATFORM_PREFIXES:
        return platform.lower(), to.strip()

    raise ValueError(
        f"Cannot determine platform from '{to}'. "
        f"Use a prefix like 'telegram:@username' or pass platform= argument."
    )


def dispatch_send(platform: str, recipient: str, text: str, config,
                  is_app_open: bool = False,
                  template_id: str = "",
                  template_vars: dict = None) -> str:
    """
    Send a message via the appropriate adapter.

    If *template_id* is provided, the template is rendered first and its
    body_text is used as the message content (messenger platforms are plain-text).

    :returns: Result string from the adapter.
    """
    # ── Template rendering (optional) ─────────────────────────────────────────
    if template_id:
        try:
            from hecos.plugins.templates import store as tpl_store
            rendered = tpl_store.render_template(template_id, template_vars or {})
            # Messenger channels use plain text; fall back to body_html stripped if needed
            text = rendered.get("body_text") or rendered.get("body_html") or text
        except KeyError:
            return f"❌ Template '{template_id}' not found."
        except Exception as e:
            logger.warning("MESSENGER", f"Template render error: {e}")

    logger.info("MESSENGER", f"Dispatching send → [{platform}] {recipient}")

    if platform == "telegram":
        from hecos.plugins.messenger.adapters import telegram as tg
        return tg.send(config.telegram, recipient, text)

    if platform == "whatsapp":
        from hecos.plugins.messenger.adapters import whatsapp as wa
        return wa.send(config.whatsapp, recipient, text, is_app_open)

    if platform == "discord":
        from hecos.plugins.messenger.adapters import discord as dc
        return dc.send(config.discord, recipient, text)

    return f"❌ Platform '{platform}' is not supported."



def dispatch_check(platform: str | None, config) -> dict[str, str]:
    """
    Check one or all providers.
    Returns a dict: { platform_name: status_string }
    """
    results = {}

    targets = [platform] if platform else list(PLATFORM_PREFIXES)

    for p in targets:
        try:
            if p == "telegram":
                from hecos.plugins.messenger.adapters import telegram as tg
                results["telegram"] = tg.check(config.telegram)

            elif p == "whatsapp":
                from hecos.plugins.messenger.adapters import whatsapp as wa
                results["whatsapp"] = wa.check(config.whatsapp)

            elif p == "discord":
                from hecos.plugins.messenger.adapters import discord as dc
                results["discord"] = dc.check(config.discord)

        except Exception as exc:
            results[p] = f"ERROR: {exc}"

    return results
