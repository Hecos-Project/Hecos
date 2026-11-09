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

    def _execute_exchange(self, text, prefix, is_voice=False):
        """Executes the exchange (text -> response) inside Zone 2 with ESC cancellation support."""
        # Suspend Zone 3 prompt while generating
        interface.set_active_prompt("", "")
        
        self.state.system_processing = True
        self.state.system_status = translator.t("thinking")
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
        stop_event = threading.Event()

        def execute():
            try:
                video_response, clean_voice_text = processore.process_exchange(
                    text, voice_status=self.state.voice_status, sm=self.state
                )
                result[0] = video_response
                result[1] = clean_voice_text
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

        # Signal processing start to WebUI
        self.state.add_event("processing_start")

        # Max seconds to wait for the LLM before auto-cancelling
        llm_timeout = self.config.get('ai', 'llm_timeout_seconds', default=90)
        deadline = time.time() + llm_timeout

        while thread.is_alive():
            # Check ESC from console keyboard
            if msvcrt.kbhit() and msvcrt.getch() == b'\x1b':
                stop_event.set()
                break
            # Check stop request from WebUI (/api/system/stop)
            if getattr(self.state, "webui_stop_requested", False):
                self.state.webui_stop_requested = False
                stop_event.set()
                break
            # Auto-timeout: avoid blocking forever
            if time.time() > deadline:
                logger.warning("[INPUT] LLM timeout — automatic cancellation.")
                stop_event.set()
                break
            time.sleep(0.1)

        if stop_event.is_set():
            interface.stop_thinking()
            voice.stop_voice() # Immediately stop audio if playing
            # Clear keyboard buffer from multiple ESC presses
            while msvcrt.kbhit():
                msvcrt.getch()
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
            
            # Save to memory
            brain_interface.save_message("user", text)
            brain_interface.save_message("assistant", video_response)

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
