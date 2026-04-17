"""
Main class for the Zentra application.
"""

import sys
import time
import atexit
import msvcrt
from zentra.core.logging import logger
from zentra.core.system import module_loader, diagnostica
from zentra.core.i18n import translator
from zentra.ui import interface, graphics, ui_updater
from zentra.ui.config_editor.core import ConfigEditor
from zentra.memory import brain_interface
from .config import ConfigManager
from .state_manager import StateManager
from .input_handler import InputHandler
from .threads import AscoltoThread
from .model_manager import ModelManager
from .personality_manager import PersonalityManager
from zentra.core.processing import processore

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
        
        from zentra.core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
        
        cv    = acfg.get('voice_status', True)
        ca    = acfg.get('listening_status', True)
        stt_s = acfg.get('stt_source', 'system')
        tts_d = acfg.get('tts_destination', 'web')
        ptt   = acfg.get('push_to_talk', False)
        hk    = acfg.get('ptt_hotkey', 'ctrl+shift')
        
        # audio_mode is now stored in config_audio.json
        am = acfg.get('audio_mode', 'auto')
        
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
        
        from .bootstrapper import SystemBootstrapper
        from .menu_handler import MenuHandler
        self.bootstrapper = SystemBootstrapper(self.config_manager, self.state_manager)
        self.menu_handler = MenuHandler(self.config_manager, self.state_manager, self.model_manager, self.personality_manager)
        
        self.running = True



    def run(self):
        """Starts the main application loop."""
        self.bootstrapper.initialize()
        
        config = self.config_manager.config
        prefisso = graphics.STILE_INPUT
        input_utente = ""
        
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")

        # Initial UI
        interface.show_complete_ui(
            config,
            self.state_manager.voice_status,
            self.state_manager.listening_status,
            self.state_manager.system_status,
            ptt_status=self.state_manager.push_to_talk
        )

        if not config.get("system", {}).get("fast_boot", False):
            self.bootstrapper.show_boot_animation()
        
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

        # [WEB_UI] Inject live managers into plugin if active, then start the Flask server.
        # Must happen BEFORE show_welcome() so the link info is printed after server is live.
        web_ui_mod = module_loader.get_plugin_module("WEB_UI")
        if web_ui_mod and hasattr(web_ui_mod, "tools"):
            if hasattr(web_ui_mod.tools, "_set_config_manager"):
                web_ui_mod.tools._set_config_manager(self.config_manager)
            if hasattr(web_ui_mod.tools, "_set_state_manager"):
                web_ui_mod.tools._set_state_manager(self.state_manager)
            # Start the Flask server now that managers are injected.
            # In console mode this is never triggered otherwise (the server starts
            # lazily only when the agent calls open_browser/get_panel_url).
            if hasattr(web_ui_mod.tools, "_ensure_server"):
                try:
                    web_ui_mod.tools._ensure_server()
                except Exception as _ws_e:
                    logger.warning(f"[APP] WebUI server startup error: {_ws_e}")

        self.bootstrapper.show_welcome()

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
            elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"]:
                menu_schermo_intero = ["F1", "F2", "F3", "F7"]
                if evento in menu_schermo_intero:
                    ui_updater.stop()
                    time.sleep(0.1)
                    
                self.menu_handler.handle_function_key(evento)
                
                # Ricarica config e ricollega plugin
                config = self.config_manager.config
                dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
                
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