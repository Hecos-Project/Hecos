"""
MODULE: zentra_bridge/webui/prompting.py
DESCRIPTION: Builds the full system prompt sent to the LLM on every request.
             Combines personality, memory context, capabilities and safety rules.
"""

import os
import logging

bridge_logger = logging.getLogger("WebUI_Bridge")


def build_system_prompt(config: dict, bridge_dir: str) -> str:
    """
    Composes and returns the complete system prompt.

    Args:
        config:     The full Zentra config dict (result of ConfigManager.config).
        bridge_dir: Absolute path to the Zentra-Core root directory.

    Returns:
        A single multi-line string ready to be inserted as the ``system`` role message.
    """
    try:
        from core.llm import brain
        from memory import brain_interface
        from core.i18n import translator
    except ImportError as exc:
        bridge_logger.error(f"[PROMPT] Failed to import core modules: {exc}")
        return "You are Zentra, an AI assistant."

    # --- Personality file ---
    personality_file = config.get("ai", {}).get("active_personality", "zentra.txt")
    path_personality = os.path.join(bridge_dir, "personality", personality_file)
    personality_text = ""
    if os.path.exists(path_personality):
        try:
            with open(path_personality, "r", encoding="utf-8") as fh:
                personality_text = fh.read()
        except Exception as exc:
            bridge_logger.warning(f"[PROMPT] Cannot read personality file: {exc}")

    # --- Long-term memory context ---
    try:
        memory_identity = brain_interface.get_memory_context()
    except Exception as exc:
        bridge_logger.warning(f"[PROMPT] Memory context unavailable: {exc}")
        memory_identity = ""

    # --- Plugin capabilities ---
    try:
        capabilities = brain.load_capabilities()
    except Exception as exc:
        bridge_logger.warning(f"[PROMPT] Capabilities unavailable: {exc}")
        capabilities = ""

    # --- Safety / identity rules ---
    try:
        rules = (
            f"{translator.t('identity_protocol')}\n"
            f"- {translator.t('rule_who_am_i')}\n"
            f"{translator.t('file_management_rules')}\n"
            f"- {translator.t('rule_list_files')}\n"
            f"- {translator.t('rule_read_file')}\n"
            f"\n{translator.t('root_security_instruction')}\n"
            f"{translator.t('root_security_desc')}\n"
        )
    except Exception as exc:
        bridge_logger.warning(f"[PROMPT] Translator unavailable: {exc}")
        rules = ""

    try:
        special_instructions = config.get("ai", {}).get("special_instructions", "").strip()
        special_instructions_block = f"\n### SPECIAL INSTRUCTIONS ###\n{special_instructions}\n" if special_instructions else ""
    except Exception as exc:
        bridge_logger.warning(f"[PROMPT] Failed to load special instructions: {exc}")
        special_instructions_block = ""

    return (
        f"{personality_text}\n\n"
        f"{memory_identity}\n\n"
        f"{capabilities}\n\n"
        f"{rules}\n"
        f"{special_instructions_block}\n"
        "--- END OF SYSTEM INSTRUCTIONS ---"
    )
