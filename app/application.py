"""
Classe principale dell'applicazione Zentra.
"""

import sys
import time
import msvcrt
from core.logging import logger
from core.system import plugin_loader, diagnostica
from core.i18n import translator
from ui import interfaccia, grafica, ui_updater
from ui.config_editor.core import ConfigEditor
from memoria import brain_interface
from .config import ConfigManager
from .state_manager import StateManager
from .input_handler import InputHandler
from .threads import AscoltoThread
from .model_manager import ModelManager
from .personality_manager import PersonalityManager

class ZentraApplication:
    def __init__(self):
        self.config_manager = ConfigManager()
        
        cv = self.config_manager.get('voce', 'stato_voce', default=True)
        ca = self.config_manager.get('ascolto', 'stato_ascolto', default=True)
        self.state_manager = StateManager(stato_voce_iniziale=cv, stato_ascolto_iniziale=ca)
        
        self.input_handler = InputHandler(self.state_manager, self.config_manager)
        self.model_manager = ModelManager(self.config_manager)
        self.personality_manager = PersonalityManager(self.config_manager)
        self.running = True

    def _initialize(self):
        """Inizializzazione di tutti i componenti."""
        logger.init_logger(self.config_manager.config)
        # Inizializza traduttore
        lingua = self.config_manager.config.get("lingua", "it")
        translator.init_translator(lingua)
        logger.info("[APP] Avvio sequenza di boot Zentra Core.")
        
        interfaccia.setup_console()
        self.state_manager.sistema_status = translator.t("loading_memory")
        brain_interface.inizializza_caveau()
        # IMPORTANTE: passa il config corrente al plugin loader
        self.state_manager.sistema_status = translator.t("loading_plugins")
        plugin_loader.aggiorna_registro_capacita(self.config_manager.config)
        # Sincronizza la configurazione dei plugin
        plugin_loader.sincronizza_config_plugin(self.config_manager)
        
        # Sincronizza lista personalità disponibili nel config
        anime_files = interfaccia.elenca_personalita()
        if anime_files:
            anime_dict = {str(i+1): name for i, name in enumerate(anime_files)}
            self.config_manager.set(anime_dict, 'ia', 'personalita_disponibili')
            self.config_manager.save()
        
        config = self.config_manager.config
        self.state_manager.sistema_status = translator.t("diagnostics")
        diagnostica.esegui_check_iniziale(config)
        
        # Avvia il monitoraggio backend solo se il plugin è attivo
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            dashboard_mod.avvia_monitoraggio_backend()
        else:
            logger.warning("APP", "Plugin DASHBOARD disabilitato, monitoraggio hardware non attivo.")

    def _show_boot_animation(self):
        """Mostra animazione di avvio."""
        sys.stdout.write(f"\n\033[96m[SYSTEM] {translator.t('boot_sync_msg')}\033[0m\n")
        for progresso in range(0, 101, 2):
            barra = grafica.crea_barra(progresso, larghezza=40, stile="cyber")
            sys.stdout.write(f"\r{barra}")
            sys.stdout.flush()
            time.sleep(0.04)
        time.sleep(0.5)

    def _show_welcome(self):
        """Mostra messaggio di benvenuto."""
        from core.audio import voce
        self.state_manager.sistema_status = translator.t("speaking")
        messaggio = self.config_manager.config.get("comportamento", {}).get("messaggio_benvenuto", translator.t("system_ready"))
        interfaccia.scrivi_zentra(messaggio)
        if self.state_manager.stato_voce:
            voce.parla(translator.t("system_ready"))
        self.state_manager.sistema_in_elaborazione = False
        self.state_manager.sistema_status = translator.t("ready")

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

    def _handle_function_key(self, key, config):
        """Gestisce i tasti funzione."""
        
        if key == "F1":
            interfaccia.mostra_help()
            
        elif key == "F2":
            self.model_manager.handle_modelli(self._input_digitale_sicuro)
            
        elif key == "F3":
            self.personality_manager.handle_personalita(self._input_digitale_sicuro)
            
        elif key == "F4":
            self.state_manager.stato_ascolto = not self.state_manager.stato_ascolto
            self.config_manager.set(self.state_manager.stato_ascolto, 'ascolto', 'stato_ascolto')
            self.config_manager.save()
            verb = "ON" if self.state_manager.stato_ascolto else "OFF"
            color = "\033[96m" if self.state_manager.stato_ascolto else "\033[91m"
            print(f"\n{color}[SYSTEM] {translator.t('header_mic')}: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F5":
            self.state_manager.stato_voce = not self.state_manager.stato_voce
            self.config_manager.set(self.state_manager.stato_voce, 'voce', 'stato_voce')
            self.config_manager.save()
            verb = "ON" if self.state_manager.stato_voce else "OFF"
            color = "\033[96m" if self.state_manager.stato_voce else "\033[91m"
            print(f"\n{color}[SYSTEM] {translator.t('header_voice')}: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F6":
            print(f"\n\033[91m[SYSTEM] {translator.t('rebooting_msg')}\033[0m")
            # Chiudi la finestra dei log esterna se presente
            logger.chiudi_console_log()
            time.sleep(1)
            sys.exit(42)
            
        elif key == "F7":
            editor = ConfigEditor()
            editor.run()
            self.config_manager.reload()
            logger.init_logger(self.config_manager.config)

    def run(self):
        """Avvia il loop principale dell'applicazione."""
        self._initialize()
        
        config = self.config_manager.config
        prefisso = f"\n\033[91m# \033[0m"
        input_utente = ""
        
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")

        # UI iniziale
        interfaccia.mostra_ui_completa(
            config,
            self.state_manager.stato_voce,
            self.state_manager.stato_ascolto,
            self.state_manager.sistema_status
        )

        self._show_boot_animation()
        
        self.state_manager.sistema_status = translator.t("ready")
        interfaccia.mostra_ui_completa(
            config,
            self.state_manager.stato_voce,
            self.state_manager.stato_ascolto,
            self.state_manager.sistema_status
        )

        if dashboard_mod:
            ui_updater.avvia(self.config_manager, self.state_manager, dashboard_mod)
        else:
            ui_updater.ferma()

        self._show_welcome()

        # Avvia thread ascolto
        ascolto_thread = AscoltoThread(self.state_manager)
        ascolto_thread.start()

        sys.stdout.write(prefisso)
        sys.stdout.flush()

        # Loop principale
        while self.running:
            # Gestione input vocale (Delegata a InputHandler)
            if (self.state_manager.comando_vocale_rilevato and 
                not self.state_manager.sistema_in_elaborazione):
                self.input_handler.handle_voice_input(prefisso)

            # Gestione input tastiera (Delegata a InputHandler)
            evento, input_utente = self.input_handler.handle_keyboard_input(prefisso, input_utente)
            
            if evento == "EXIT":
                logger.info("[APP] Shutdown di emergenza.")
                sys.exit(0)
            elif evento == "ESC_AGAIN":
                print(f"\n\033[93m[SYSTEM] {translator.t('esc_to_exit')}\033[0m")
            elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]:
                menu_schermo_intero = ["F1", "F2", "F3", "F7"]
                if evento in menu_schermo_intero:
                    ui_updater.ferma()
                    time.sleep(0.1)
                    
                self._handle_function_key(evento, config)
                
                # Ricarica config e ricollega plugin
                config = self.config_manager.config
                dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
                
                if evento in ["F4", "F5"]:
                    interfaccia.aggiorna_barra_stato_in_place(
                        config,
                        self.state_manager.stato_voce,
                        self.state_manager.stato_ascolto,
                        self.state_manager.sistema_status
                    )
                else:
                    interfaccia.mostra_ui_completa(
                        config,
                        self.state_manager.stato_voce,
                        self.state_manager.stato_ascolto,
                        self.state_manager.sistema_status
                    )
                
                if evento in menu_schermo_intero:
                    if dashboard_mod:
                        ui_updater.avvia(self.config_manager, self.state_manager, dashboard_mod)
                    else:
                        ui_updater.ferma()
                    
                sys.stdout.write(prefisso + input_utente)
                sys.stdout.flush()
            elif evento == "PROCESSED":
                sys.stdout.write(prefisso)
                sys.stdout.flush()
            elif evento == "CLEAR":
                input_utente = ""
                sys.stdout.write(f"\r{prefisso}")
                sys.stdout.flush()

            time.sleep(0.01)

if __name__ == "__main__":
    app = ZentraApplication()
    app.run()