"""
Keyboard and voice input management.
"""

import sys
import time
import threading
import msvcrt
from zentra.ui import interface
from zentra.core.processing import processore
from zentra.core.audio import voice
from zentra.core.logging import logger
from zentra.core.system import plugin_loader
from zentra.core.i18n import translator
from zentra.memory import brain_interface
# sys è importato a livello di modulo - NON usare 'import sys' inline nei metodi

class InputHandler:
    def __init__(self, state_manager, config_manager):
        self.state = state_manager
        self.config = config_manager

    def handle_keyboard_input(self, prefix, user_input):
        """Handles keyboard input."""
        evento, input_utente = interface.read_keyboard_input(prefix, user_input)
        
        if evento == "ENTER":
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
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            tools = getattr(dashboard_mod, "tools", None)
            raw_fn = getattr(tools, "_get_raw_backend_status", None) if tools else None
            if raw_fn and raw_fn() not in ["READY", "CLOUD", "ONLINE"]:
                print(f"\n\033[93m[SYSTEM] Backend not ready yet. Please wait...\033[0m")
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
        
        # --- NEW: Direct Image Commands (Bypass AI) ---
        if testo_pulito.lower().startswith(("/img ", "/foto ")):
            prompt = testo_pulito[5:].strip()
            if prompt:
                self._handle_direct_image(prompt, prefisso)
                return "PROCESSED", ""
        # ----------------------------------------------

        if testo_pulito.startswith("/istruzione") or testo_pulito.startswith("/instruction"):
            istruzione = testo_pulito.replace("/istruzione", "").replace("/instruction", "").strip()
            self.config.set(istruzione, 'ai', 'special_instructions')
            processore.configure(self.config.config)
            salva_persistente = self.config.get('ai', 'save_special_instructions', default=False)
            if salva_persistente:
                self.config.save()
                
            if istruzione:
                msg = f"\n\033[92m[SYSTEM] Special Instructions activated: '{istruzione}'\033[0m"
                if not salva_persistente:
                    msg += " (RAM only)"
            else:
                msg = f"\n\033[93m[SYSTEM] Special Instructions cleared.\033[0m"
            print(msg)
            return "CLEAR", ""
            
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            tools = getattr(dashboard_mod, "tools", None)
            raw_fn = getattr(tools, "_get_raw_backend_status", None) if tools else None
            if raw_fn:
                raw_status = raw_fn()
                if raw_status not in ["READY", "CLOUD", "ONLINE"]:
                    print(f"\n\033[93m[SYSTEM] Backend not ready ({raw_status}). Please wait...\033[0m")
                    return None, ""
            
        voice.stop_voice() # Stop any ongoing old speech
        self._execute_exchange(testo, prefisso, is_voice=False)
        return "PROCESSED", ""

    def _execute_exchange(self, text, prefix, is_voice=False):
        """Executes the exchange (text -> response) with ESC support."""
        self.state.system_processing = True
        self.state.system_status = translator.t("thinking")
        
        # Visual feedback
        sys.stdout.write(f"\r{' ' * 80}\r")
        label = "Admin (Voice)" if is_voice else "Admin"
        print(f"{prefix}\033[92m{label}: {text}\033[0m")
        print(f"\033[93m[{translator.t('press_esc_to_stop')}]\033[0m")
        
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
            print(f"\n\033[93m[SYSTEM] {translator.t('request_cancelled')}\033[0m")
            # Notify WebUI of cancellation so it un-hangs!
            self.state.add_event("system_response", {"user": text, "ai": "❌ Operazione annullata."})
            
            self.state.system_status = translator.t("ready")
            self.state.system_processing = False
            sys.stdout.write(prefix)
            sys.stdout.flush()
            return
        
        thread.join()
        interface.stop_thinking()

        if error[0]:
            logger.error(f"[INPUT] Error: {error[0]}")
            self.state.add_event("system_response", {"user": text, "ai": f"❌ Errore durante l'elaborazione: {error[0]}"})
        else:
            video_response, clean_voice_text = result
            # Show response
            interface.write_zentra(video_response)
            
            # Save to memory
            brain_interface.save_message("user", text)
            brain_interface.save_message("assistant", video_response)

            # Broadcast the response to the WebUI (so it renders the text if the Console processed it)
            self.state.add_event("system_response", {"user": text, "ai": video_response})

            if self.state.voice_status and clean_voice_text and self.state.tts_destination == 'system':
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
            
            elif self.state.voice_status and clean_voice_text and self.state.tts_destination == 'web':
                # Generate audio file but don't play locally, just notify WebUI
                from zentra.core.audio.device_manager import get_audio_config
                from zentra.plugins.web_ui.routes_chat import generate_voice_file
                try:
                    path = generate_voice_file(clean_voice_text, get_audio_config())
                    if path:
                        self.state.add_event("audio_ready")
                except Exception as e:
                    logger.debug(f"[INPUT] Web audio generation failed: {e}")
                # At the end of voice, returns to READY (already handled below)

        self.state.system_status = translator.t("ready")
        self.state.system_processing = False
        # Force a status bar refresh to remove "THINKING" or "SPEAKING"
        interface.update_status_bar_in_place(
            self.config.config, self.state.voice_status, self.state.listening_status, self.state.system_status,
            ptt_status=self.state.push_to_talk
        )
        # Restore prompt for next input
        sys.stdout.write(prefix)
        sys.stdout.flush()

    def _handle_esc(self, prefix):
        """Handles ESC key: stops voice and, if necessary, asks for exit confirmation."""
        now = time.time()
        # If voice was stopped manually very recently, ignore this ESC (race condition buffer)
        # If Zentra was speaking, ESC should just stop the voice and return to prompt
        if self.state.system_speaking or voice.is_speaking:
            voice.stop_voice()
            self.state.system_speaking = False
            return "PROCESSED", "" # Back to prompt
            
        # Otherwise, ask for exit confirmation
        sys.stdout.write(f"\n\033[93m[SYSTEM] {translator.t('confirm_exit')} (Y/N): \033[0m")
        sys.stdout.flush()
        
        # Wait for Y or N character
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch().decode('utf-8', errors='ignore').upper()
                if ch == 'Y' or ch == 'S': # Keep S for compatibility with Italian habits
                    print("Y")
                    return "EXIT", None
                elif ch == 'N':
                    print("N")
                    sys.stdout.write(f"\r{' ' * 50}\r{prefix}")
                    sys.stdout.flush()
                    return "CANCELLED", "" # Back to prompt without exiting
                elif ch == '\x1b': # ESC again to cancel
                    sys.stdout.write(f"\r{' ' * 50}\r{prefix}")
                    sys.stdout.flush()
                    return "CANCELLED", ""
            time.sleep(0.05)

    def _handle_direct_image(self, prompt, prefix):
        """Generates an image directly, bypassing the LLM analysis."""
        self.state.system_processing = True
        self.state.system_status = translator.t("generating_image")
        
        # Visual feedback in console
        print(f"{prefix}\033[92mAdmin: /img {prompt}\033[0m")
        print(f"\033[93m[SYSTEM] Direct Image Request — Bypassing AI Analysis...\033[0m")
        
        interface.start_thinking()
        self.state.add_event("processing_start")

        try:
            # Import and call plugin directly
            from zentra.plugins.image_gen.main import tools as image_gen_tools
            result = image_gen_tools.generate_image(prompt)
            
            # Show response in console
            interface.write_zentra(result)
            
            # Save to memory so the AI can "know" what happened in next turns
            brain_interface.save_message("user", f"/img {prompt}")
            brain_interface.save_message("assistant", result)

            # Update WebUI
            self.state.add_event("system_response", {"user": f"/img {prompt}", "ai": result})
            
        except Exception as e:
            logger.error(f"[INPUT] Direct Image Error: {e}")
            err_msg = f"❌ Errore generazione diretta: {e}"
            print(f"\n\033[91m{err_msg}\033[0m")
            self.state.add_event("system_response", {"user": f"/img {prompt}", "ai": err_msg})

        interface.stop_thinking()
        self.state.system_status = translator.t("ready")
        self.state.system_processing = False
        
        # Restore prompt
        sys.stdout.write(prefix)
        sys.stdout.flush()