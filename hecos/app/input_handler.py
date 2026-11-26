"""
Keyboard and voice input management.
"""

import sys
import time
import threading
import msvcrt
from hecos.ui import interface
from hecos.ui.viewport import get_viewport
from hecos.core.processing import processore
from hecos.core.audio import voice
from hecos.core.logging import logger
from hecos.core.system import module_loader
from hecos.core.i18n import translator
from hecos.memory import brain_interface
# sys è importato a livello di modulo - NON usare 'import sys' inline nei metodi

class InputHandler:
    def __init__(self, state_manager, config_manager):
        self.state = state_manager
        self.config = config_manager

    def handle_keyboard_input(self, prefix, user_input):
        """Handles keyboard input."""
        evento, input_utente = interface.read_keyboard_input(prefix, user_input)
        
        if evento == "ENTER":
            if input_utente.strip():
                interface.push_cli_history(input_utente)
            return self._process_text_input(input_utente, prefix)
        elif evento == "CLEAR":
            return "CLEAR", ""
        elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"]:
            return evento, input_utente
        elif evento == "ESC":
            return self._handle_esc(prefix)
        
        return None, input_utente

    def handle_voice_input(self, prefix):
        """Handles voice input."""
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            tools = getattr(dashboard_mod, "tools", None)
            raw_fn = getattr(tools, "_get_raw_backend_status", None) if tools else None
            if raw_fn and raw_fn() not in ["READY", "CLOUD", "ONLINE"]:
                interface.print_scrolling("\033[93m[SYSTEM] Backend not ready yet. Please wait...\033[0m")
                self.state.detected_voice_command = None
                return

        text_v = self.state.detected_voice_command
        self.state.detected_voice_command = None
        
        # Indicates we are processing voice input
        voice.stop_voice() # Stop any ongoing old speech
        self.state.add_event("voice_detected", {"text": text_v})
        self._execute_exchange(text_v, prefix, is_voice=True)

    def _process_text_input(self, testo, prefisso):
        """Processa input testuale."""
        if not testo.strip():
            return None, testo
            
        testo_pulito = testo.strip()
        
        if testo_pulito.startswith("/istruzione") or testo_pulito.startswith("/instruction"):
            istruzione = testo_pulito.replace("/istruzione", "").replace("/instruction", "").strip()
            self.config.set(istruzione, 'ai', 'special_instructions')
            processore.configure(self.config.config)
            salva_persistente = self.config.get('ai', 'save_special_instructions', default=False)
            if salva_persistente:
                self.config.save()
                
            if istruzione:
                msg = f"\033[92m[SYSTEM] Special Instructions activated: '{istruzione}'\033[0m"
                if not salva_persistente:
                    msg += " (RAM only)"
            else:
                msg = "\033[93m[SYSTEM] Special Instructions cleared.\033[0m"
            interface.print_scrolling(msg)
            return "CLEAR", ""

        if testo_pulito.lower() == "/think" or testo_pulito.lower().startswith("/think "):
            arg = testo_pulito[6:].strip().lower()
            if arg in ("on", "true", "1"):
                self.config.set(True, 'backend', 'ollama', 'enable_thinking')
                self.config.save()
                processore.configure(self.config.config)
                interface.print_scrolling("\033[92m[SYSTEM] Ollama Thinking: ON\033[0m")
            elif arg in ("off", "false", "0"):
                self.config.set(False, 'backend', 'ollama', 'enable_thinking')
                self.config.save()
                processore.configure(self.config.config)
                interface.print_scrolling("\033[93m[SYSTEM] Ollama Thinking: OFF\033[0m")
            elif arg in ("auto", "default", "reset"):
                self.config.set(None, 'backend', 'ollama', 'enable_thinking')
                self.config.save()
                processore.configure(self.config.config)
                interface.print_scrolling("\033[96m[SYSTEM] Ollama Thinking: AUTO\033[0m")
            else:
                cur = self.config.get('backend', 'ollama', 'enable_thinking', default=None)
                cur_lbl = "AUTO" if cur is None else ("ON" if cur else "OFF")
                interface.print_scrolling(
                    f"\033[96m[SYSTEM] Ollama Thinking is currently {cur_lbl}. Usage: /think on | off | auto\033[0m"
                )
            return "CLEAR", ""
            
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            tools = getattr(dashboard_mod, "tools", None)
            raw_fn = getattr(tools, "_get_raw_backend_status", None) if tools else None
            if raw_fn:
                raw_status = raw_fn()
                if raw_status not in ["READY", "CLOUD", "ONLINE"]:
                    interface.print_scrolling(
                        f"\033[93m[SYSTEM] Backend not ready ({raw_status}). Please wait...\033[0m"
                    )
                    interface.set_active_prompt(prefisso, "")
                    return None, ""
            
        voice.stop_voice() # Stop any ongoing old speech
        
        # Add to history
        try:
            from hecos.modules.input_history import history_mgr
            history_mgr.push(testo, user="admin")
        except Exception:
            pass
            
        self._execute_exchange(testo, prefisso, is_voice=False)
        return "PROCESSED", ""

    def _resolve_inactivity_timeout(self) -> int:
        """Resolves per-step inactivity timeout (seconds) for CLI turns."""
        explicit = self.config.get('ai', 'llm_timeout_seconds', default=None)
        if explicit is not None:
            try:
                return max(60, min(1800, int(explicit)))
            except (TypeError, ValueError):
                pass
        btype = str(self.config.get('backend', 'type', default='ollama') or 'ollama').lower()
        if btype == 'hybrid':
            btype = str(self.config.get('backend', 'active_model_source', default='ollama') or 'ollama').lower()
        req_to = self.config.get('backend', btype, 'request_timeout_sec', default=300)
        try:
            return max(60, min(1800, int(req_to or 300)))
        except (TypeError, ValueError):
            return 300

    def _execute_exchange(self, text, prefix, is_voice=False):
        """Executes the exchange (text -> response) inside Zone 2 with real ESC cancellation support."""
        from hecos.core.agent.turn_control import register_turn, cancel_session_turns, complete_turn

        # Suspend Zone 3 prompt while generating
        interface.set_active_prompt("", "")
        
        self.state.system_processing = True
        self.state.system_status = translator.t("thinking")
        if hasattr(self.state, "record_chat_message"):
            self.state.record_chat_message(text)
        interface.update_status_bar_in_place(
            self.config.config,
            self.state.voice_status,
            self.state.listening_status,
            self.state.system_status,
            ptt_status=self.state.push_to_talk,
        )
        
        # Visual feedback strictly inside Zone 2 (Body)
        label = "Admin (Voice)" if is_voice else "Admin"
        interface.print_scrolling(f"{prefix}\033[92m{label}: {text}\033[0m")
        
        # Non-intrusive spinner + [Press ESC to stop] inside Zone 3 (Footer)
        interface.start_thinking()
        
        result = [None, None]
        error = [None]
        cli_turn_key = "cli_console"
        turn_id, cancel_event = register_turn(cli_turn_key)
        t_start = time.monotonic()
        last_activity = [t_start]

        def _cli_trace_callback(msg, level: str = "info"):
            last_activity[0] = time.monotonic()
            if cancel_event.is_set():
                return
            if isinstance(msg, dict) and msg.get("type") != "heartbeat":
                try:
                    self.state.add_event(msg.get("type", "agent_trace"), msg)
                except Exception:
                    pass

        def execute():
            try:
                video_response, clean_voice_text = processore.process_exchange(
                    text,
                    voice_status=self.state.voice_status,
                    sm=self.state,
                    config_manager=self.config,
                    cancel_event=cancel_event,
                    turn_id=turn_id,
                    trace_callback=_cli_trace_callback,
                )
                result[0] = video_response
                result[1] = clean_voice_text
            except Exception as e:
                error[0] = e
            finally:
                complete_turn(turn_id)

        thread = threading.Thread(target=execute, daemon=True, name="HecosCLIExchange")
        thread.start()

        # Signal processing start to WebUI
        self.state.add_event("processing_start")

        # Activity-based inactivity timeout + generous hard cap (matches WebUI watchdog behavior)
        inactivity_timeout = self._resolve_inactivity_timeout()
        hard_cap = max(inactivity_timeout * 4, 1800)
        cancel_reason = None

        while thread.is_alive():
            # Check ESC from console keyboard (consume extended key pairs cleanly)
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):
                    if msvcrt.kbhit():
                        msvcrt.getch()
                elif ch == b'\x1b':
                    cancel_reason = "user_esc"
                    cancel_session_turns(cli_turn_key, by_user=True)
                    cancel_event.set()
                    break
            # Check stop request from WebUI (/api/system/stop)
            if getattr(self.state, "webui_stop_requested", False):
                self.state.webui_stop_requested = False
                cancel_reason = "webui_stop"
                cancel_session_turns(cli_turn_key, by_user=True)
                cancel_event.set()
                break
            # Auto-timeout only on true inactivity or hard cap
            now = time.monotonic()
            if (now - last_activity[0]) > inactivity_timeout or (now - t_start) > hard_cap:
                logger.warning(
                    f"[INPUT] LLM timeout — automatic cancellation "
                    f"(elapsed={now - t_start:.1f}s, inactivity={now - last_activity[0]:.1f}s, limit={inactivity_timeout}s)."
                )
                cancel_reason = "timeout"
                cancel_session_turns(cli_turn_key, by_user=False)
                cancel_event.set()
                break
            time.sleep(0.08)

        if cancel_event.is_set():
            interface.stop_thinking()
            voice.stop_voice() # Immediately stop audio if playing
            # Wait briefly for aborted socket/thread to unwind cleanly so no stray traces print after prompt
            thread.join(timeout=2.0)
            # Clear keyboard buffer from multiple ESC presses
            while msvcrt.kbhit():
                msvcrt.getch()
            if cancel_reason == "timeout":
                interface.print_scrolling(
                    f"\033[93m[SYSTEM] Timeout ({inactivity_timeout}s inactivity) — {translator.t('request_cancelled')}\033[0m"
                )
            else:
                interface.print_scrolling(f"\033[93m[SYSTEM] {translator.t('request_cancelled')}\033[0m")
            interface.print_scrolling("")
            # Notify WebUI of cancellation so it un-hangs!
            self.state.add_event("system_response", {"user": text, "ai": "❌ Operazione annullata."})
            
            self.state.system_status = translator.t("ready")
            self.state.system_processing = False
            interface.update_status_bar_in_place(
                self.config.config,
                self.state.voice_status,
                self.state.listening_status,
                self.state.system_status,
                ptt_status=self.state.push_to_talk,
            )
            interface.set_active_prompt(prefix, "")
            return
        
        thread.join()
        interface.stop_thinking()

        if error[0]:
            logger.error(f"[INPUT] Error: {error[0]}")
            interface.print_scrolling(f"\033[91m[ERROR] {error[0]}\033[0m")
            interface.print_scrolling("")
            self.state.add_event("system_response", {"user": text, "ai": f"❌ Errore durante l'elaborazione: {error[0]}"})
        else:
            video_response, clean_voice_text = result
            # Show response inside Zone 2
            interface.write_hecos(video_response)

            # Note: History persistence (user + assistant + metadata/traces) is already handled
            # cleanly inside AgentExecutor._conclude_turn -> sync_assistant_history().
            # Do NOT call brain_interface.save_message() again here, or every CLI turn is duplicated x2.

            # Broadcast the response to the WebUI (so it renders the text if the Console processed it)
            self.state.add_event("system_response", {"user": text, "ai": video_response})

            if self.state.voice_status and clean_voice_text:
                self.state.system_status = translator.t("speaking")
                interface.update_status_bar_in_place(
                    self.config.config, 
                    self.state.voice_status, 
                    self.state.listening_status, 
                    self.state.system_status,
                    ptt_status=self.state.push_to_talk
                )
                
                # NON-BLOCKING SPEECH: Run in a daemon thread so prompt returns immediately
                def _speak_task():
                    try:
                        voice.speak(clean_voice_text, state=self.state)
                    finally:
                        # Once finished naturally or stopped, restore READY status
                        if not self.state.system_processing: # only if we are still at prompt
                            self.state.system_status = translator.t("ready")
                            interface.update_status_bar_in_place(
                                self.config.config, self.state.voice_status, 
                                self.state.listening_status, self.state.system_status,
                                ptt_status=self.state.push_to_talk
                            )
                
                threading.Thread(target=_speak_task, daemon=True).start()

        self.state.system_status = translator.t("ready")
        self.state.system_processing = False
        # Force a status bar refresh to remove "THINKING" or "SPEAKING"
        interface.update_status_bar_in_place(
            self.config.config, self.state.voice_status, self.state.listening_status, self.state.system_status,
            ptt_status=self.state.push_to_talk
        )
        # Re-enable Zone 3 prompt and reset input buffer
        interface.set_active_prompt(prefix, "")

    def _handle_esc(self, prefix):
        """Handles ESC key: stops voice and, if necessary, asks for exit confirmation in Zone 3."""
        # If Hecos was speaking, ESC should just stop the voice and return to prompt
        if self.state.system_speaking or voice.is_speaking:
            voice.stop_voice()
            self.state.system_speaking = False
            return "PROCESSED", "" # Back to prompt
            
        # Ask for exit confirmation cleanly on the Zone 3 Footer bar
        vp = get_viewport()
        vp.set_footer_override(
            f"\033[93m [SYSTEM] {translator.t('confirm_exit')} (Y/N): \033[0m",
            show_cursor=True,
        )
        
        # Wait for Y or N character
        while True:
            if msvcrt.kbhit():
                ch_raw = msvcrt.getch()
                if ch_raw in (b'\x00', b'\xe0'):
                    msvcrt.getch()
                    continue
                if ch_raw == b'\x1b': # ESC again to cancel
                    interface.set_active_prompt(prefix, "")
                    return "CANCELLED", ""
                ch = ch_raw.decode('utf-8', errors='ignore').upper()
                if ch in ('Y', 'S'): # Keep S for compatibility with Italian habits
                    vp.set_footer_override(None)
                    return "EXIT", None
                elif ch == 'N':
                    interface.set_active_prompt(prefix, "")
                    return "CANCELLED", "" # Back to prompt without exiting
            time.sleep(0.05)
