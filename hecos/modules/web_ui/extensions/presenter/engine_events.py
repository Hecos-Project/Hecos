"""
Hecos Presenter - Event Handlers
Dispatches system, search, simulation, and conversational events into presenter feed and commentary.
"""

import traceback
from typing import Dict, Any

from hecos.core.logging import logger
from hecos.modules.web_ui.extensions.presenter.feed import add_feed_entry
from hecos.modules.web_ui.extensions.presenter.engine_commentary import generate_presenter_commentary


class PresenterEventHandler:
    """Handles bus events and translates them into presenter feed entries and commentary."""

    def __init__(self, engine):
        self._engine = engine
        self._progress_seen = {}

    @property
    def cfg(self):
        return self._engine.cfg

    def on_persona_switched(self, event: Dict[str, Any]):
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
        session_id = payload.get("session_id")

        sys_prompt = (
            "You are the Hecos System Presenter. Provide a brief, punchy, 1-sentence introduction "
            "or commentary about the newly activated AI soul. Use the language of the system."
        )
        user_prompt = f"The user has just switched the AI soul to '{persona_name}'. Introduce them briefly."
        generate_presenter_commentary(cfg, "persona_switched", sys_prompt, user_prompt, session_id=session_id)

    def on_new_chat(self, event: Dict[str, Any]):
        logger.info(f"[Presenter] _on_new_chat RECEIVED: {event}")
        cfg = self.cfg
        if not cfg.enabled or not cfg.briefing_on_new_chat:
            logger.info("[Presenter] Skipped: disabled or briefing_on_new_chat=False")
            return

        payload = event.get("payload", {})
        session_id = payload.get("session_id")

        sys_prompt = (
            "You are the Hecos System Presenter. Greet the user in 1 short sentence indicating that a new session has started."
        )
        user_prompt = "A new chat session was just started. Acknowledge it."
        generate_presenter_commentary(cfg, "new_chat", sys_prompt, user_prompt, session_id=session_id)

    def on_search_started(self, event: Dict[str, Any]):
        cfg = self.cfg
        if not cfg.enabled or not getattr(cfg, "live_commentary", True) or not getattr(cfg, "commentary_on_search", True):
            return
        payload = event.get("payload", {})
        query = payload.get("query", "")
        mode = payload.get("mode", "clear")
        text = f"[NetSearch] Search started for '{query}' ({mode.upper()} mode)..."
        add_feed_entry("search_milestone", text, session_id=None, persist=cfg.feed.persist)

    def on_search_completed(self, event: Dict[str, Any]):
        cfg = self.cfg
        if not cfg.enabled or not getattr(cfg, "live_commentary", True):
            return

        # If search presenter is disabled/collapsed, skip all work & LLM generation completely
        if not getattr(cfg, "commentary_on_search", True):
            logger.info("[Presenter] NetSearch presenter is OFF/collapsed. Skipping search milestone & commentary generation.")
            return

        payload = event.get("payload", {})
        query = payload.get("query", "")
        total = payload.get("total_results", 0)
        dur = payload.get("duration_ms", 0)
        mode = payload.get("mode", "clear")

        sec_str = f"{dur/1000:.1f}s" if dur >= 1000 else f"{dur}ms"
        status_text = f"[NetSearch] Search complete: {total} sources indexed in {sec_str} for '{query}'."
        add_feed_entry("search_milestone", status_text, session_id=None, persist=cfg.feed.persist)

        if getattr(cfg.voice, "enabled", False) or getattr(cfg, "commentary_on_search", True):
            sys_prompt = (
                "You are the Hecos Presenter. Provide a brief, punchy, 1-2 sentence commentary "
                "on the search that just completed. Keep it concise, expressive and direct."
            )
            user_prompt = f"Search '{query}' ({mode}) returned {total} results in {sec_str}. Give a short commentary."
            generate_presenter_commentary(cfg, "search_commentary", sys_prompt, user_prompt, session_id=None)

    def on_package_event(self, event: Dict[str, Any]):
        """Deprecated: Replaced by unified progress_milestone system."""
        pass

    def on_progress_event(self, event: Dict[str, Any]):
        """Direct feed entries for system progress milestones (downloads, installations, tasks)."""
        if not self.cfg.enabled:
            return

        payload = event.get("payload", {})
        task_id = payload.get("id", "")
        title = payload.get("title", task_id)
        state = payload.get("state", "running")
        phase = payload.get("phase") or {}
        phase_key = phase.get("key") or ""
        phase_label = phase.get("label") or phase_key
        percent = payload.get("percent", 0.0)
        source = payload.get("source", "SYSTEM")

        last_state, last_phase = self._progress_seen.get(task_id, (None, None))

        try:
            from hecos.core.progress.sinks.logger_sink import _render_bar
        except Exception:
            def _render_bar(pct, width=20):
                return ""

        # 1. Terminal events
        if state in ("done", "error", "cancelled"):
            if last_state != state:
                self._progress_seen[task_id] = (state, phase_key)
                if state == "done":
                    text = f"✅ [{source}] '{title}' {_render_bar(100.0, 16)} 100% - completed successfully."
                elif state == "cancelled":
                    text = f"⚠️ [{source}] '{title}' {_render_bar(percent, 16)} {percent:.0f}% - cancelled by user."
                else:
                    err_msg = payload.get("error") or payload.get("message") or "Unknown error"
                    text = f"❌ [{source}] '{title}' {_render_bar(percent, 16)} {percent:.0f}% - failed: {err_msg}"
                add_feed_entry("progress_milestone", text, session_id=None, persist=self.cfg.feed.persist)
            return

        # 2. Start or Phase change
        if last_state is None:
            self._progress_seen[task_id] = (state, phase_key)
            msg = f"⏳ [{source}] Operation started: '{title}' {_render_bar(percent, 16)} {percent:.0f}%"
            add_feed_entry("progress_milestone", msg, session_id=None, persist=self.cfg.feed.persist)
        elif phase_key and phase_key != last_phase:
            self._progress_seen[task_id] = (state, phase_key)
            phase_msg = phase.get("message") or ""
            detail = f" - {phase_msg}" if phase_msg else ""
            msg = f"⚙️ [{source}] {title} {_render_bar(percent, 16)} {percent:.0f}% - Phase '{phase_label}'{detail}"
            add_feed_entry("progress_milestone", msg, session_id=None, persist=self.cfg.feed.persist)

    def on_user_message_sent(self, event: Dict[str, Any]):
        """Comment on the user's message. In simulation mode -> coach. Otherwise -> commentator."""
        if not self._engine.is_running:
            return

        cfg = self.cfg
        if not cfg.enabled or not cfg.commentary_on_messages:
            return
        if getattr(cfg, 'commentary_mode', 'full') != 'full':
            return

        payload = event.get("payload", {})
        user_msg = payload.get("user_message", "")
        session_id = payload.get("session_id")
        if not user_msg or len(user_msg.strip()) < 3:
            return

        # Check simulation state
        try:
            from hecos.modules.playbooks.playbooks.storage import (
                get_simulation_state, check_forbidden_terms, get_playbook, increment_turn
            )
            sim_state = get_simulation_state(session_id or "default")
            sim_running = sim_state.get("status") == "running"
        except Exception:
            sim_running = False
            sim_state = {}

        if sim_running:
            # COACH MODE: check for violations + provide coaching
            try:
                violations = check_forbidden_terms(user_msg, sim_state.get("playbook_id"))
                increment_turn(session_id or "default")

                if violations:
                    for v in violations:
                        violation_text = (
                            f"⚠️ VIOLATION: User said '{', '.join(v['terms_found'])}'. "
                            f"Correction: {v['correction']} "
                            f"[severity: {v['severity']}]"
                        )
                        add_feed_entry("playbook_violation", violation_text, session_id=session_id, persist=cfg.feed.persist)

                pb = get_playbook(sim_state.get("playbook_id", "")) if sim_state.get("playbook_id") else None
                mission = pb.get("mission", {}) if pb else {}
                coach_role = mission.get("coach_role", "Coach")
                user_role = mission.get("user_role", "User")
                chat_role = mission.get("chat_role", "Interlocutor")
                swapped = sim_state.get("swapped", False)
                if swapped:
                    user_role, chat_role = chat_role, user_role

                coach_tasks = mission.get("coach_tasks", [])
                tasks_str = "; ".join(coach_tasks) if coach_tasks else "Guide and advise"

                violation_note = ""
                if violations:
                    v_terms = ", ".join(v['terms_found'] for v in violations)
                    v_corrections = "; ".join(v['correction'] for v in violations if v['correction'])
                    violation_note = f"\nVIOLATION DETECTED: User said forbidden term(s): [{v_terms}]. Correct answer: {v_corrections}. You MUST address this violation first."

                sys_prompt = (
                    f"You are the COACH ({coach_role}) in a live simulation.\n"
                    f"The user plays: {user_role}. The chat AI plays: {chat_role}.\n"
                    f"Your tasks: {tasks_str}\n"
                    f"Analyze the user's message and provide 1-2 concise coaching suggestions. "
                    f"Keep it under 30 words. Be direct and actionable.{violation_note}"
                )
                user_prompt = f"User ({user_role}) says: {user_msg[:300]}"
                generate_presenter_commentary(cfg, "coach_advice", sys_prompt, user_prompt, session_id=session_id)
            except Exception as e:
                logger.error(f"[Presenter] Coach mode error: {e}\n{traceback.format_exc()}")
        else:
            # COMMENTATOR MODE
            sys_prompt = (
                "You are the Hecos System Presenter, a witty third-party sports commentator for this AI system. "
                "The Admin (user) has just sent a message to the AI. "
                "Write a brief, punchy 1-sentence commentary about what the user is asking or doing. "
                "Be like a sports commentator narrating a play as it happens. Keep it under 20 words. "
                "Do NOT answer the question yourself — you are the observer, not the AI."
            )
            user_prompt = f"Admin says: {user_msg[:300]}"
            generate_presenter_commentary(cfg, "user_comment", sys_prompt, user_prompt, session_id=session_id)

    def on_assistant_response(self, event: Dict[str, Any]):
        """Comment on the AI's response. In simulation -> coach evaluates the exchange."""
        if not self._engine.is_running:
            return

        cfg = self.cfg
        if not cfg.enabled or not cfg.commentary_on_messages:
            return
        if getattr(cfg, 'commentary_mode', 'full') != 'full':
            return

        payload = event.get("payload", {})
        user_msg = payload.get("user_message", "")
        ai_msg = payload.get("assistant_message", "")
        session_id = payload.get("session_id")
        if not ai_msg or len(ai_msg.strip()) < 3:
            return

        # Check simulation state
        try:
            from hecos.modules.playbooks.playbooks.storage import get_simulation_state, get_playbook
            sim_state = get_simulation_state(session_id or "default")
            sim_running = sim_state.get("status") == "running"
        except Exception:
            sim_running = False
            sim_state = {}

        if sim_running:
            # COACH MODE: evaluate exchange
            try:
                pb = get_playbook(sim_state.get("playbook_id", "")) if sim_state.get("playbook_id") else None
                mission = pb.get("mission", {}) if pb else {}
                coach_role = mission.get("coach_role", "Coach")
                user_role = mission.get("user_role", "User")
                chat_role = mission.get("chat_role", "Interlocutor")
                swapped = sim_state.get("swapped", False)
                if swapped:
                    user_role, chat_role = chat_role, user_role

                sys_prompt = (
                    f"You are the COACH ({coach_role}) observing a simulation exchange.\n"
                    f"User plays: {user_role}. Chat AI plays: {chat_role}.\n"
                    "Evaluate the AI's response for consistency with the scenario. "
                    "Suggest how the user should respond next. "
                    "Analyze the interlocutor's personality traits based on their responses. "
                    "Keep it under 40 words. Be direct."
                )
                user_prompt = f"User ({user_role}): {user_msg[:200]}\nChat ({chat_role}): {ai_msg[:300]}"
                generate_presenter_commentary(cfg, "coach_evaluation", sys_prompt, user_prompt, session_id=session_id)
            except Exception as e:
                logger.error(f"[Presenter] Coach evaluation error: {e}\n{traceback.format_exc()}")
        else:
            # COMMENTATOR MODE
            sys_prompt = (
                "You are the Hecos System Presenter, a witty third-party sports commentator for this AI system. "
                "The AI has just responded to the Admin's question. "
                "Write a brief, punchy 1-sentence commentary about the quality, style, or content of the AI's response. "
                "Be sarcastic, funny, or impressed depending on the context. Keep it under 20 words. "
                "Do NOT repeat the response — you are the observer."
            )
            user_prompt = f"Admin asked: {user_msg[:200]}\nAI responded: {ai_msg[:300]}"
            generate_presenter_commentary(cfg, "ai_comment", sys_prompt, user_prompt, session_id=session_id)

    def on_message_exchange(self, event: Dict[str, Any]):
        """Legacy: generates commentary on the full exchange (exchange mode only)."""
        if not self._engine.is_running:
            return

        cfg = self.cfg
        if not cfg.enabled or not cfg.commentary_on_messages:
            return
        if getattr(cfg, 'commentary_mode', 'full') == 'full':
            return

        payload = event.get("payload", {})
        user_msg = payload.get("user_message", "")
        ai_msg = payload.get("assistant_message", "")
        session_id = payload.get("session_id")

        sys_prompt = (
            "You are the Hecos System Presenter, a witty and sharp sports commentator for this AI system. "
            "You are observing a chat between the Admin (user) and the AI (assistant). "
            "Write a brief, punchy 1-2 sentence commentary about this specific exchange. "
            "Be sarcastic, funny, or impressed depending on the context. If an image was generated (e.g. markdown image tags), comment on the visual! "
            "Do not act as the assistant, act as the 3rd party observer. Keep it under 25 words."
        )
        user_prompt = f"Exchange to comment on:\nAdmin: {user_msg}\nAI: {ai_msg}"
        generate_presenter_commentary(cfg, "message_exchange", sys_prompt, user_prompt, session_id=session_id)

