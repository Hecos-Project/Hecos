import threading
import traceback
from typing import Dict, Any
from hecos.core.logging import logger
from hecos.core.events import bus
from hecos.modules.web_ui.extensions.presenter.config.store import load_presenter_config
from hecos.modules.web_ui.extensions.presenter.feed import add_feed_entry
from hecos.core.global_presets.manager import get_soul
from hecos.core.global_presets.merger import merge_soul_into_config
from hecos.core.llm.brain import generate_response, load_config

class PresenterEngine:
    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        
    @property
    def cfg(self):
        return load_presenter_config()

    def start(self):
        with self._lock:
            if self._running: return
            self._running = True
            
            # Subscribe to events
            bus.subscribe("persona_switched", self._on_persona_switched)
            bus.subscribe("new_chat", self._on_new_chat)
            bus.subscribe("message_exchange", self._on_message_exchange)
            bus.subscribe("hpm:package_installed", self._on_package_event)
            bus.subscribe("hpm:package_uninstalled", self._on_package_event)
            logger.info("[Presenter] Engine started. Subscribed to events.")

    def _generate_commentary(self, event_type: str, system_prompt: str, user_prompt: str):
        """Generates commentary using the designated Global Preset model."""
        import copy
        
        logger.info(f"[Presenter] _generate_commentary called for event_type='{event_type}'")
        
        base_cfg = copy.deepcopy(load_config() or {})
        merged_cfg = base_cfg
        
        # Merge the Presenter's specific Global Preset if selected
        cfg = self.cfg
        logger.info(f"[Presenter] Config: preset_id='{cfg.voice.preset_id}', enabled={cfg.enabled}")
        
        if cfg.voice.preset_id:
            soul = get_soul(cfg.voice.preset_id)
            if soul:
                merged_cfg = merge_soul_into_config(base_cfg, soul)
                logger.info(f"[Presenter] Merged Global Preset '{cfg.voice.preset_id}' into config")
            else:
                logger.warning(f"[Presenter] Global Preset '{cfg.voice.preset_id}' not found!")
                
        # We temporarily overwrite the system prompt in the config to force the persona
        if 'ai' not in merged_cfg:
            merged_cfg['ai'] = {}
        merged_cfg['ai']['special_instructions'] = system_prompt
        
        # Override tokens if configured
        btype = merged_cfg.get('backend', {}).get('type', 'ollama')
        if btype in merged_cfg.get('backend', {}):
            merged_cfg['backend'][btype]['max_tokens'] = cfg.voice.max_tokens

        def _task():
            try:
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
                        logger.info(f"[Presenter] Writing feed entry for '{event_type}'")
                        add_feed_entry(event_type, response, persist=cfg.feed.persist)
                        logger.info(f"[Presenter] Feed entry written successfully")
                else:
                    logger.warning(f"[Presenter] generate_response returned None/empty for '{event_type}'")
            except Exception as e:
                logger.error(f"[Presenter] _task exception: {e}\n{traceback.format_exc()}")
        
        threading.Thread(target=_task, daemon=True, name="PresenterLLM").start()
        logger.info(f"[Presenter] LLM thread launched for '{event_type}'")

    def _on_persona_switched(self, event: Dict[str, Any]):
        logger.info(f"[Presenter] _on_persona_switched RECEIVED: {event}")
        
        cfg = self.cfg
        if not cfg.enabled:
            logger.info("[Presenter] Skipped: module disabled")
            return
        if not cfg.live_commentary:
            logger.info("[Presenter] Skipped: live_commentary disabled")
            return
        
        payload = event.get("payload", {})
        persona_name = payload.get("new_persona", "Unknown")
        
        sys_prompt = "You are the Hecos System Presenter. Provide a brief, punchy, 1-sentence introduction or commentary about the newly activated AI persona. Use the language of the system."
        user_prompt = f"The user has just switched the AI persona to '{persona_name}'. Introduce them briefly."
        
        self._generate_commentary("persona_switched", sys_prompt, user_prompt)

    def _on_new_chat(self, event: Dict[str, Any]):
        logger.info(f"[Presenter] _on_new_chat RECEIVED: {event}")
        
        cfg = self.cfg
        if not cfg.enabled or not cfg.briefing_on_new_chat:
            logger.info("[Presenter] Skipped: disabled or briefing_on_new_chat=False")
            return
        
        sys_prompt = "You are the Hecos System Presenter. Greet the user in 1 short sentence indicating that a new session has started."
        user_prompt = "A new chat session was just started. Acknowledge it."
        
        self._generate_commentary("new_chat", sys_prompt, user_prompt)

    def _on_package_event(self, event: Dict[str, Any]):
        """Direct feed entry for package events — no LLM needed."""
        if not self.cfg.enabled: return
        
        event_type = event.get("type", "")
        payload = event.get("payload", {})
        pkg_id = payload.get("id", "Unknown")
        
        if "installed" in event_type:
            text = f"Package '{pkg_id}' installed successfully."
        elif "uninstalled" in event_type:
            text = f"Package '{pkg_id}' uninstalled."
        else:
            text = f"Package event: {pkg_id}"
        
        add_feed_entry("package_event", text, persist=self.cfg.feed.persist)

    def _on_message_exchange(self, event: Dict[str, Any]):
        """Generates commentary on the user-AI exchange if enabled."""
        if not self._running: return
        
        cfg = self.cfg
        if not cfg.enabled or not getattr(cfg, 'commentary_on_messages', False):
            return
            
        payload = event.get("payload", {})
        user_msg = payload.get("user_message", "")
        ai_msg = payload.get("assistant_message", "")
        
        sys_prompt = (
            "You are the Hecos System Presenter, a witty and sharp sports commentator for this AI system. "
            "You are observing a chat between the Admin (user) and the AI (assistant). "
            "Write a brief, punchy 1-2 sentence commentary about this specific exchange. "
            "Be sarcastic, funny, or impressed depending on the context. If an image was generated (e.g. markdown image tags), comment on the visual! "
            "Do not act as the assistant, act as the 3rd party observer. Keep it under 25 words."
        )
        
        user_prompt = f"Exchange to comment on:\nAdmin: {user_msg}\nAI: {ai_msg}"
        self._generate_commentary("message_exchange", sys_prompt, user_prompt)

_engine_instance = None

def get_engine() -> PresenterEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PresenterEngine()
    return _engine_instance

