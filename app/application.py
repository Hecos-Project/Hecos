"""
Main class for the Zentra application.
"""

import sys
import time
import atexit
import msvcrt
from core.logging import logger
from core.system import plugin_loader, diagnostica
from core.i18n import translator
from ui import interface, graphics, ui_updater
from ui.config_editor.core import ConfigEditor
from memory import brain_interface
from .config import ConfigManager
from .state_manager import StateManager
from .input_handler import InputHandler
from .threads import AscoltoThread
from .model_manager import ModelManager
from .personality_manager import PersonalityManager
from core.processing import processore

# Register debug window closure as a guaranteed shutdown hook.
# atexit handles normal sys.exit() and Ctrl+C.
atexit.register(logger.close_all_consoles)

# On Windows, closing via the X button sends CTRL_CLOSE_EVENT which bypasses atexit.
# SetConsoleCtrlHandler intercepts this OS-level event.
import ctypes
import ctypes.wintypes

_HANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.DWORD)

@_HANDLER_ROUTINE
def _console_ctrl_handler(ctrl_type):
    # CTRL_C=0, CTRL_BREAK=1, CTRL_CLOSE=2, CTRL_LOGOFF=5, CTRL_SHUTDOWN=6
    if ctrl_type in (0, 1, 2, 5, 6):
        logger.close_all_consoles()
    return False  # False = lascia proseguire la terminazione normale

ctypes.windll.kernel32.SetConsoleCtrlHandler(_console_ctrl_handler, True)

class ZentraApplication:
    def __init__(self):
        self.config_manager = ConfigManager()
        
        from core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
        
        cv    = acfg.get('voice_status', True)
        ca    = acfg.get('listening_status', True)
        stt_s = acfg.get('stt_source', 'system')
        tts_d = acfg.get('tts_destination', 'web')
        ptt   = acfg.get('push_to_talk', False)
        hk    = acfg.get('ptt_hotkey', 'ctrl+shift')
        
        # Audio mode is legacy and still in config.json (root)
        am = self.config_manager.config.get('audio_mode', 'auto')
        
        self.state_manager = StateManager(
            initial_voice_status=cv, 
            initial_listening_status=ca, 
            initial_audio_mode=am
        )
        self.state_manager.push_to_talk    = ptt
        self.state_manager.ptt_hotkey      = hk
        self.state_manager.stt_source      = stt_s
        self.state_manager.tts_destination = tts_d
        
        self.input_handler = InputHandler(self.state_manager, self.config_manager)
        self.model_manager = ModelManager(self.config_manager)
        self.personality_manager = PersonalityManager(self.config_manager)
        self.running = True

    def _initialize(self):
        """Inizializzazione di tutti i componenti."""
        logger.init_logger(self.config_manager.config)
        # Initialize translator
        language = self.config_manager.config.get("language", "en")
        translator.init_translator(language)
        processore.configure(self.config_manager.config)
        logger.info("[APP] Zentra Core boot sequence initiated.")
        
        interface.setup_console()
        self.state_manager.system_status = translator.t("loading_memory")
        brain_interface.initialize_vault()
        brain_interface.maybe_clear_on_restart(self.config_manager.config)
        # IMPORTANT: pass current config to plugin loader
        self.state_manager.system_status = translator.t("loading_plugins")
        plugin_loader.update_capability_registry(self.config_manager.config)
        self.state_manager.system_status = translator.t("sync_plugins")
        plugin_loader.sync_plugin_config(self.config_manager)
        
        # Inject state_manager into WebUI server after plugin load (for audio toggle routes)
        try:
            from plugins.web_ui.server import set_state_manager
            set_state_manager(self.state_manager)
        except Exception as _e:
            logger.warning("APP", f"Could not inject state_manager into WebUI: {_e}")
        
        # Synchronize list of available personalities in config
        personality_files = interface.list_personalities()
        if personality_files:
            personality_dict = {str(i+1): name for i, name in enumerate(personality_files)}
            self.config_manager.set(personality_dict, 'ai', 'available_personalities')
            self.config_manager.save()
        
        config = self.config_manager.config
        self.state_manager.system_status = translator.t("diagnostics")
        diagnostica.run_initial_check(config)

        # Audio device auto-selection (Piper TTS output + Microphone input)
        try:
            from core.audio.device_manager import maybe_scan_on_startup
            self.state_manager.system_status = "Scanning audio devices..."
            maybe_scan_on_startup()
            logger.info("[APP] Audio device scan completed.")
        except Exception as _ae:
            logger.warning("APP", f"Audio device scan skipped: {_ae}")

        # Avvia il monitoraggio backend solo se il plugin è attivo
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            ui_updater.start(self.config_manager, self.state_manager, dashboard_mod)
        else:
            logger.warning("APP", "DASHBOARD plugin disabled; hardware monitoring inactive.")

    def _show_boot_animation(self):
        """Shows boot animation."""
        sys.stdout.write(f"\n\033[96m[SYSTEM] {translator.t('boot_sync_msg')}\033[0m\n")
        for progress in range(0, 101, 2):
            bar = graphics.create_bar(progress, width=40, style="cyber")
            sys.stdout.write(f"\r{bar}")
            sys.stdout.flush()
            time.sleep(0.04)
        time.sleep(0.5)

    def _show_welcome(self):
        """Shows welcome message."""
        from core.audio import voice
        self.state_manager.system_status = translator.t("speaking")
        message = self.config_manager.config.get("behavior", {}).get("welcome_message", translator.t("system_ready"))
        interface.write_zentra(message)
        if self.state_manager.voice_status:
            # We skip speaking 'ready' here to speed up the prompt availability
            pass
        self.state_manager.system_processing = False
        self.state_manager.system_status = translator.t("ready")
        
        # Start the background UI updater
        ui_updater.start(self.config_manager, self.state_manager, plugin_loader.get_plugin_module("DASHBOARD"))
        
        # Update just the status bar in place, avoid clearing the screen
        interface.update_status_bar_in_place(
            self.config_manager.config, 
            self.state_manager.voice_status, 
            self.state_manager.listening_status, 
            self.state_manager.system_status,
            ptt_status=self.state_manager.push_to_talk
        )


    def _input_digitale_sicuro(self, messaggio):
        """Legge un input numerico o ESC senza bloccare."""
        sys.stdout.write(f"\033[93m{messaggio}\033[0m")
        sys.stdout.flush()
        scelta = ""
        while True:
            if msvcrt.kbhit():
                char_raw = msvcrt.getch()
                if char_raw == b'\x1b':  # Tasto ESC
                    print()
                    return "ESC"
                char = char_raw.decode('utf-8', errors='ignore')
                if char == '\r':
                    print()
                    break
                if char.isdigit():
                    scelta += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
            time.sleep(0.05)
        return scelta

    def _handle_f1(self):
        """Help Menu (F1)."""
        ui_updater.stop()
        interface.show_help()
        ui_updater.start(self.config_manager, self.state_manager, plugin_loader.get_plugin_module("DASHBOARD"))
        interface.show_complete_ui(
            self.config_manager.config,
            self.state_manager.voice_status,
            self.state_manager.listening_status,
            self.state_manager.system_status,
            ptt_status=self.state_manager.push_to_talk
        )

    def _handle_f2(self):
        """Model selection (F2)."""
        ui_updater.stop()
        models = self.model_manager.get_available_models()
        current = self.model_manager.get_effective_model(self.config_manager.config)
        interface.show_models_menu(models, current)
        self.model_manager.handle_models(self._input_digitale_sicuro, prefetched=models)

    def _handle_f3(self):
        """Personality selection (F3)."""
        ui_updater.stop()
        souls = interface.list_personalities()
        current = self.config_manager.config.get("ai", {}).get("active_personality", "N/D")
        interface.show_personality_menu(souls, current)
        self.personality_manager.handle_personality(self._input_digitale_sicuro, soul_files=souls)

    def _handle_f7(self):
        """Configuration Menu (F7)."""
        ui_updater.stop()
        editor = ConfigEditor()
        editor.run()
        self.config_manager.reload()
        processore.configure(self.config_manager.config)
        logger.init_logger(self.config_manager.config)
        
        # Svuota le cache per garantire l'applicazione immediata
        from core.processing import filtri
        if hasattr(filtri, 'reset_cache'):
            filtri.reset_cache()
            
        from core.llm.manager import manager
        if hasattr(manager, 'reload_config'):
            manager.reload_config()

    def _handle_function_key(self, key, config):
        """Gestisce i tasti funzione."""
        
        if key == "F1":
            self._handle_f1()
            
        elif key == "F2":
            self._handle_f2()
            
        elif key == "F3":
            self._handle_f3()
            
        elif key == "F4":
            self.state_manager.listening_status = not self.state_manager.listening_status
            
            from core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["listening_status"] = self.state_manager.listening_status
            _save_audio_config(acfg)
            
            processore.configure(self.config_manager.config)
            verb = "ON" if self.state_manager.listening_status else "OFF"
            color = "\033[96m" if self.state_manager.listening_status else "\033[91m"
            print(f"\n{color}[SYSTEM] {translator.t('header_mic')}: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F5":
            self.state_manager.voice_status = not self.state_manager.voice_status
            
            from core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["voice_status"] = self.state_manager.voice_status
            _save_audio_config(acfg)
            
            processore.configure(self.config_manager.config)
            verb = "ON" if self.state_manager.voice_status else "OFF"
            color = "\033[96m" if self.state_manager.voice_status else "\033[91m"
            print(f"\n{color}[SYSTEM] {translator.t('header_voice')}: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F6":
            print(f"\n\033[91m[SYSTEM] {translator.t('rebooting_msg')}\033[0m")
            # Close all external consoles (Log and Debug)
            logger.close_all_consoles()
            time.sleep(1)
            sys.exit(42)
            
        elif key == "F7":
            self._handle_f7()
            
        elif key == "F8":
            is_ptt = self.state_manager.push_to_talk
            new_ptt = not is_ptt
            self.state_manager.push_to_talk = new_ptt
            
            from core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["push_to_talk"] = new_ptt
            _save_audio_config(acfg)
            
            verb = "ON" if new_ptt else "OFF"
            color = "\033[96m" if new_ptt else "\033[91m"
            print(f"\n{color}[SYSTEM] Push-To-Talk (PTT): {verb}\033[0m")
            time.sleep(0.5)

    def run(self):
        """Starts the main application loop."""
        self._initialize()
        
        config = self.config_manager.config
        prefisso = f"\n\033[91m# \033[0m"
        input_utente = ""
        
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")

        # Initial UI
        interface.show_complete_ui(
            config,
            self.state_manager.voice_status,
            self.state_manager.listening_status,
            self.state_manager.system_status,
            ptt_status=self.state_manager.push_to_talk
        )

        if not config.get("system", {}).get("fast_boot", False):
            self._show_boot_animation()
        
        self.state_manager.system_status = translator.t("ready")
        interface.show_complete_ui(
            config,
            self.state_manager.voice_status,
            self.state_manager.listening_status,
            self.state_manager.system_status,
            ptt_status=self.state_manager.push_to_talk
        )

        if dashboard_mod:
            ui_updater.start(self.config_manager, self.state_manager, dashboard_mod)
        else:
            ui_updater.stop()

        self._show_welcome()

        # Avvia thread ascolto
        ascolto_thread = AscoltoThread(self.state_manager)
        ascolto_thread.start()

        sys.stdout.write(prefisso)
        sys.stdout.flush()

        # Main loop
        while self.running:
            # Voice input handling (Delegated to InputHandler)
            if (self.state_manager.detected_voice_command and 
                not self.state_manager.system_processing):
                self.input_handler.handle_voice_input(prefisso)

            # Gestione input tastiera (Delegata a InputHandler)
            evento, input_utente = self.input_handler.handle_keyboard_input(prefisso, input_utente)
            
            if evento == "EXIT":
                logger.info("[APP] User confirmed exit.")
                self.running = False # Uscita pulita dal loop
            elif evento == "CANCELLED":
                # L'input handler ha già ripristinato il prompt, non fare nulla
                pass
            elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
                menu_schermo_intero = ["F1", "F2", "F3", "F7"]
                if evento in menu_schermo_intero:
                    ui_updater.stop()
                    time.sleep(0.1)
                    
                self._handle_function_key(evento, config)
                
                # Ricarica config e ricollega plugin
                config = self.config_manager.config
                dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
                
                if evento in ["F4", "F5"]:
                    interface.update_status_bar_in_place(
                        config,
                        self.state_manager.voice_status,
                        self.state_manager.listening_status,
                        self.state_manager.system_status,
                        ptt_status=self.state_manager.push_to_talk
                    )
                else:
                    interface.show_complete_ui(
                        config,
                        self.state_manager.voice_status,
                        self.state_manager.listening_status,
                        self.state_manager.system_status,
                        ptt_status=self.state_manager.push_to_talk
                    )
                
                if evento in menu_schermo_intero:
                    if dashboard_mod:
                        ui_updater.start(self.config_manager, self.state_manager, dashboard_mod)
                    else:
                        ui_updater.stop()
                    
                sys.stdout.write(prefisso + input_utente)
                sys.stdout.flush()
            elif evento == "PROCESSED":
                pass
            elif evento == "CLEAR":
                input_utente = ""
                sys.stdout.write(f"\r{prefisso}")
                sys.stdout.flush()

            time.sleep(0.01)

if __name__ == "__main__":
    app = ZentraApplication()
    app.run()