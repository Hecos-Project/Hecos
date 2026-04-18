"""
Module responsible for handling function keys (F1-F9) and associated menus/actions.
"""
import sys
import time
import msvcrt
from zentra.core.logging import logger
from zentra.core.system import module_loader
from zentra.core.i18n import translator
from zentra.ui import interface, ui_updater
from zentra.ui.config_editor.core import ConfigEditor
from zentra.core.processing import processore

class MenuHandler:
    """Manages system shortcuts and UI menus triggered via function keys."""
    
    def __init__(self, config_manager, state_manager, model_manager, personality_manager):
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.model_manager = model_manager
        self.personality_manager = personality_manager

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
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
        ui_updater.start(self.config_manager, self.state_manager, dashboard_mod)
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
        # Use sync_available_personalities for a consistently ordered list
        # (Zentra_System_Soul first, then alphabetical).
        souls = self.config_manager.sync_available_personalities()
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
        from zentra.core.processing import filtri
        if hasattr(filtri, 'reset_cache'):
            filtri.reset_cache()
            
        from zentra.core.llm.manager import manager
        if hasattr(manager, 'reload_config'):
            manager.reload_config()

    def handle_function_key(self, key):
        """Routes function keys to their specific actions."""
        config = self.config_manager.config
        
        if key == "F1":
            self._handle_f1()
            
        elif key == "F2":
            self._handle_f2()
            
        elif key == "F3":
            self._handle_f3()
            
        elif key == "F4": # Toggle Mic
            self.state_manager.listening_status = not self.state_manager.listening_status
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["listening_status"] = self.state_manager.listening_status
            _save_audio_config(acfg)
            processore.configure(config)
            verb = "ON" if self.state_manager.listening_status else "OFF"
            color = "\033[96m" if self.state_manager.listening_status else "\033[91m"
            print(f"\n{color}[SYSTEM] {translator.t('header_mic')}: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F5": # Refresh UI
            interface.show_complete_ui(
                config,
                self.state_manager.voice_status,
                self.state_manager.listening_status,
                self.state_manager.system_status,
                ptt_status=self.state_manager.push_to_talk
            )
            time.sleep(0.1)
            
        elif key == "F6": # Toggle Voice
            self.state_manager.voice_status = not self.state_manager.voice_status
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["voice_status"] = self.state_manager.voice_status
            _save_audio_config(acfg)
            processore.configure(config)
            verb = "ON" if self.state_manager.voice_status else "OFF"
            color = "\033[96m" if self.state_manager.voice_status else "\033[91m"
            print(f"\n{color}[SYSTEM] {translator.t('header_voice')}: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F7": # App Config
            self._handle_f7()
            
        elif key == "F8": # Toggle Push-To-Talk
            is_ptt = self.state_manager.push_to_talk
            new_ptt = not is_ptt
            self.state_manager.push_to_talk = new_ptt
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["push_to_talk"] = new_ptt
            _save_audio_config(acfg)
            verb = "ON" if new_ptt else "OFF"
            color = "\033[96m" if new_ptt else "\033[91m"
            print(f"\n{color}[SYSTEM] Push-To-Talk (PTT): {verb}\033[0m")
            time.sleep(0.5)

        elif key == "F9": # System Reboot
            print(f"\n\033[91m[SYSTEM] {translator.t('rebooting_msg')}\033[0m")
            logger.close_all_consoles()
            time.sleep(1)
            sys.exit(42)
