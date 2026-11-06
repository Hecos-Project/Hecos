"""
Hecos Presenter - Commentary Generation Engine
Handles LLM prompt merging, persona/soul directives, playbook knowledge injection,
tool extraction/execution, and feed entry persistence.
"""

import copy
import time
import threading
import traceback
from typing import Optional

from hecos.core.logging import logger
from hecos.modules.web_ui.extensions.presenter.feed import add_feed_entry
from hecos.core.global_presets.manager import get_soul
from hecos.core.global_presets.merger import merge_soul_into_config
from hecos.core.llm.brain import generate_response, load_config


def generate_presenter_commentary(cfg, event_type: str, system_prompt: str, user_prompt: str, session_id: Optional[str] = None):
    """
    Generates presenter commentary using the designated model and configuration.
    Runs asynchronously in a background daemon thread.
    """
    logger.info(f"[Presenter] generate_presenter_commentary called for event_type='{event_type}'")

    base_cfg = copy.deepcopy(load_config() or {})
    merged_cfg = base_cfg

    # Merge the Presenter's specific Global Preset if selected
    logger.info(f"[Presenter] Config: preset_id='{cfg.voice.preset_id}', enabled={cfg.enabled}")

    if cfg.voice.preset_id:
        soul = get_soul(cfg.voice.preset_id)
        if soul:
            merged_cfg = merge_soul_into_config(base_cfg, soul)
            logger.info(f"[Presenter] Merged Global Preset '{cfg.voice.preset_id}' into config")
        else:
            logger.warning(f"[Presenter] Global Preset '{cfg.voice.preset_id}' not found!")

    if 'ai' not in merged_cfg:
        merged_cfg['ai'] = {}

    # 1. Merge instructions from the selected Global Preset (if any)
    preset_instructions = merged_cfg['ai'].get('custom_instructions', '').strip()
    if preset_instructions:
        system_prompt += f"\n\n[GLOBAL PRESET DIRECTIVES]:\n{preset_instructions}"

    # 2. Merge Presenter-specific custom instructions (from module config)
    custom_instructions = getattr(cfg, "custom_instructions", "").strip()
    if custom_instructions:
        system_prompt += f"\n\n[PRESENTER MODULE CUSTOM INSTRUCTIONS]:\n{custom_instructions}"

    # 3. Handle tools/commands permission
    allow_commands = getattr(cfg, "allow_commands", False)
    if allow_commands:
        system_prompt += (
            "\n\n[COMMANDS ENABLED]: You CAN use direct slash commands (e.g., /img <description>) "
            "or other available tools if you feel it's necessary to show something to the user directly."
        )
    else:
        system_prompt += (
            "\n\n[COMMANDS DISABLED]: You are an observer. Do NOT use slash commands (like /img) "
            "or attempt to execute tools. Provide ONLY text commentary."
        )

    # 4. Inject Playbook context (if Playbooks module is installed)
    try:
        try:
            from hecos.modules.playbooks.playbooks.storage import get_presenter_playbook_context
        except ImportError:
            from hecos.modules.playbooks.playbooks.storage import get_active_playbook_context as get_presenter_playbook_context
        playbook_ctx = get_presenter_playbook_context(max_tokens=1500, chat_id=session_id or "default")
        if playbook_ctx:
            system_prompt += f"\n\n[PLAYBOOK KNOWLEDGE BASE]:\n{playbook_ctx}"
    except Exception:
        pass  # Playbooks module not installed or error - silently skip

    merged_cfg['ai']['special_instructions'] = system_prompt
    merged_cfg['ai']['skip_chat_playbook'] = True
    merged_cfg['is_presenter'] = True

    # Override tokens if configured
    btype = merged_cfg.get('backend', {}).get('type', 'ollama')
    if btype in merged_cfg.get('backend', {}):
        merged_cfg['backend'][btype]['max_tokens'] = cfg.voice.max_tokens

    logger.info(f"[Presenter] Final sys_prompt length: {len(system_prompt)}. Preview: {system_prompt[:200]}...")
    logger.info(f"[Presenter] Final user_prompt length: {len(user_prompt)}. Preview: {user_prompt[:200]}...")

    def _task():
        try:
            # If local backend and event is triggered by user message, stagger slightly
            if btype in ['ollama', 'llamacpp', 'local'] and event_type in ["user_message_sent", "coach_advice", "user_comment"]:
                time.sleep(1.5)

            logger.info(f"[Presenter] _task started: calling generate_response for '{event_type}'")
            response = generate_response(
                user_text=user_prompt,
                external_config=merged_cfg,
                save_history=False,
                tag="PRESENTER"
            )
            logger.info(f"[Presenter] _task got response: type={type(response).__name__}, len={len(response) if response else 0}, preview='{(response or '')[:100]}'")

            if response:
                if response.startswith("Error"):
                    logger.error(f"[Presenter] generate_response returned error: {response}")
                else:
                    if allow_commands:
                        try:
                            from hecos.core.processing import processore
                            from hecos.modules.web_ui.server import get_state_manager
                            sm = get_state_manager()

                            tools_called, tool_results, extracted_text, think_block = processore.extract_and_execute_tools(
                                response,
                                current_config=merged_cfg,
                                sm=sm
                            )

                            if tools_called:
                                from hecos.core.agent.media_interceptor import MediaInterceptor
                                response = MediaInterceptor.append_ui_media_to_text(extracted_text, tool_results)
                        except Exception as tool_e:
                            logger.error(f"[Presenter] Error executing presenter tools: {tool_e}")

                    logger.info(f"[Presenter] Writing feed entry for '{event_type}'")
                    add_feed_entry(event_type, response, session_id=session_id, persist=cfg.feed.persist)
                    logger.info(f"[Presenter] Feed entry written successfully")
            else:
                logger.warning(f"[Presenter] generate_response returned None/empty for '{event_type}'")
        except Exception as e:
            logger.error(f"[Presenter] _task exception: {e}\n{traceback.format_exc()}")

    threading.Thread(target=_task, daemon=True, name="PresenterLLM").start()
    logger.info(f"[Presenter] LLM thread launched for '{event_type}'")

