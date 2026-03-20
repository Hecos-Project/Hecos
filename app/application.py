"""
Classe principale dell'applicazione Aura.
"""

import sys
import time
import threading
import msvcrt
from core import logger, plugin_loader, diagnostica, processore, ascolto, voce
import plugins.dashboard.main as dashboard
from ui import interfaccia, grafica, ui_updater
from ui.config_editor.core import ConfigEditor
from memoria import brain_interface
from .config import ConfigManager
from .state_manager import StateManager
from .input_handler import InputHandler
from .threads import AscoltoThread

class AuraApplication:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.state_manager = StateManager()
        self.input_handler = InputHandler(self.state_manager, self.config_manager)
        self.running = True

    def _initialize(self):
        """Inizializzazione di tutti i componenti."""
        logger.info("[APP] Avvio sequenza di boot Aura Core.")
        
        interfaccia.setup_console()
        brain_interface.inizializza_caveau()
        plugin_loader.aggiorna_registro_capacita()
        
        config = self.config_manager.config
        diagnostica.esegui_check_iniziale(config)
        dashboard.avvia_monitoraggio_backend()

    def _show_boot_animation(self):
        """Mostra animazione di avvio."""
        sys.stdout.write(f"\n\033[96m[SISTEMA] Sincronizzazione Rete Neurale e Memoria...\033[0m\n")
        for progresso in range(0, 101, 2):
            barra = grafica.crea_barra(progresso, larghezza=40, stile="cyber")
            sys.stdout.write(f"\r{barra}")
            sys.stdout.flush()
            time.sleep(0.04)
        time.sleep(0.5)

    def _show_welcome(self):
        """Mostra messaggio di benvenuto."""
        self.state_manager.sistema_in_elaborazione = True
        interfaccia.scrivi_aura("Sistemi pronti. Connessione neurale stabilita, Admin.")
        if self.state_manager.stato_voce:
            voce.parla("Sistemi pronti.")
        self.state_manager.sistema_in_elaborazione = False

    def _input_digitale_sicuro(self, messaggio):
        """Legge un input numerico senza bloccare."""
        sys.stdout.write(f"\033[93m{messaggio}\033[0m")
        sys.stdout.flush()
        scelta = ""
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch().decode('utf-8', errors='ignore')
                if char == '\r':
                    print()
                    break
                if char.isdigit():
                    scelta += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
        return scelta

    def _handle_f2(self, config):
        """Gestione F2 - Selezione modelli con lettura automatica da Ollama."""
        print(f"\n\n\033[96m[ GESTIONE MODELLI ]\033[0m")
        
        backend_type = config.get('backend', {}).get('tipo', 'ollama')
        backend_config = config.get('backend', {}).get(backend_type, {})
        
        # Ottieni la lista dei modelli disponibili da Ollama
        modelli_ollama = []
        model_sizes = self._get_model_sizes()
        
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                modelli_ollama = [m.get('name') for m in data.get('models', []) if m.get('name')]
        except Exception as e:
            logger.debug("APP", f"Errore connessione a Ollama: {e}")
            modelli_ollama = []
        
        if not modelli_ollama:
            # Fallback: usa la lista dal config se Ollama non risponde
            print(f"\033[93mOllama non raggiungibile. Uso lista locale...\033[0m")
            modelli = backend_config.get('modelli_disponibili', {})
            if not modelli:
                print(f"\033[91mNessun modello configurato per il backend {backend_type}.\033[0m")
                print(f"\033[93mVerifica che in config.json ci sia 'modelli_disponibili' dentro '{backend_type}'.\033[0m")
                time.sleep(3)
                return
            modelli_ollama = [modelli[k] for k in sorted(modelli.keys(), key=int)]
        
        print(f"\033[96mBackend attuale: {backend_type.upper()}\033[0m")
        print(f"\033[96mModelli disponibili ({len(modelli_ollama)}):\033[0m")
        
        attuale = backend_config.get('modello', '')
        max_len = max([len(m) for m in modelli_ollama]) + 2
        
        for idx, model_name in enumerate(modelli_ollama, 1):
            prefisso = "\033[92m>> " if model_name == attuale else "   "
            size_info = model_sizes.get(model_name, "")
            if size_info:
                size_info = f" \033[90m[{size_info}]\033[0m"
            
            nome_formattato = model_name.ljust(max_len)
            print(f" {prefisso}[{idx}] {nome_formattato}{size_info}\033[0m")
        
        print(f"\n\033[93mDigita il numero del modello da attivare (o ESC per annullare):\033[0m")
        
        scelta = ""
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char == b'\x1b':
                    scelta = "ESC"
                    break
                try:
                    ch = char.decode('utf-8')
                    if ch == '\r':
                        break
                    if ch.isdigit():
                        scelta += ch
                        sys.stdout.write(ch)
                        sys.stdout.flush()
                except:
                    pass
            time.sleep(0.05)
        
        if scelta and scelta != "ESC":
            idx = int(scelta) - 1
            if 0 <= idx < len(modelli_ollama):
                nuovo_modello = modelli_ollama[idx]
                self.config_manager.set(nuovo_modello, 'backend', backend_type, 'modello')
                
                # Opzionale: aggiorna anche la lista modelli_disponibili
                modelli_dict = {str(i+1): name for i, name in enumerate(modelli_ollama)}
                self.config_manager.set(modelli_dict, 'backend', backend_type, 'modelli_disponibili')
                
                self.config_manager.save()
                print(f"\n\033[92m✅ Modello impostato: {nuovo_modello} (backend: {backend_type})\033[0m")
                
                if backend_type == 'kobold':
                    print(f"\033[93mNota: Per KoboldCPP, assicurati che il file '{nuovo_modello}' sia nella cartella models e che KoboldCPP sia in esecuzione.\033[0m")
            else:
                print(f"\n\033[91mNumero non valido.\033[0m")
            time.sleep(2)

    def _handle_f3(self, config):
        """Gestione F3 - Selezione personalità."""
        anime_files = interfaccia.elenca_personalita()
        if not anime_files:
            print(f"\n\033[91m[!] Nessun file .txt in /personalita!\033[0m")
            time.sleep(1)
        else:
            print(f"\n\n\033[96m--- SELEZIONE ANIMA (PERSONALITÀ) ---\033[0m")
            for i, nome_file in enumerate(anime_files, 1):
                print(f" [{i}] {nome_file}")
            
            scelta = self._input_digitale_sicuro("Seleziona numero: ")
            if scelta.isdigit():
                idx = int(scelta) - 1
                if 0 <= idx < len(anime_files):
                    nuova_p = anime_files[idx]
                    self.config_manager.set(nuova_p, 'ia', 'personalita_attiva')
                    self.config_manager.save()
                    print(f"\033[92m[SISTEMA] Personalità aggiornata: {nuova_p}\033[0m")
                    time.sleep(1)
                else:
                    print(f"\033[91m[ERRORE] Indice non valido.\033[0m")
                    time.sleep(1)

    def _handle_function_key(self, key, config):
        """Gestisce i tasti funzione."""
        
        if key == "F1":
            interfaccia.mostra_help()
            
        elif key == "F2":
            self._handle_f2(config)
            
        elif key == "F3":
            self._handle_f3(config)
            
        elif key == "F4":
            self.state_manager.stato_voce = not self.state_manager.stato_voce
            print(f"\n\033[96m[SISTEMA] Voce: {'ON' if self.state_manager.stato_voce else 'OFF'}\033[0m")
            time.sleep(0.5)
            
        elif key == "F5":
            self.state_manager.stato_ascolto = not self.state_manager.stato_ascolto
            print(f"\n\033[96m[SISTEMA] Ascolto: {'ON' if self.state_manager.stato_ascolto else 'OFF'}\033[0m")
            time.sleep(0.5)
            
        elif key == "F6":
            print(f"\n\033[91m[SISTEMA] REBOOT IN CORSO...\033[0m")
            time.sleep(1)
            sys.exit(42)
            
        elif key == "F7":
            editor = ConfigEditor()
            editor.run()
            # Ricarica la configurazione dopo l'editor
            self.config_manager.reload()

    def run(self):
        """Avvia il loop principale dell'applicazione."""
        self._initialize()
        
        config = self.config_manager.config
        prefisso = f"\n\033[91m# \033[0m"
        input_utente = ""

        # UI iniziale
        interfaccia.mostra_ui_completa(
            config,
            self.state_manager.stato_voce,
            self.state_manager.stato_ascolto,
            dashboard.get_backend_status()
        )

        self._show_boot_animation()
        
        interfaccia.mostra_ui_completa(
            config,
            self.state_manager.stato_voce,
            self.state_manager.stato_ascolto,
            dashboard.get_backend_status()
        )

        # Avvia aggiornamento in-place della riga hardware (no flickering)
        ui_updater.avvia(self.config_manager, self.state_manager, dashboard)

        self._show_welcome()

        # Avvia thread ascolto
        ascolto_thread = AscoltoThread(self.state_manager)
        ascolto_thread.start()

        sys.stdout.write(prefisso)
        sys.stdout.flush()

        # Loop principale
        while self.running:
            # Gestione input vocale
            if (self.state_manager.comando_vocale_rilevato and 
                not self.state_manager.sistema_in_elaborazione):
                self._handle_voice_input(prefisso)

            # Gestione input tastiera
            evento, input_utente = self.input_handler.handle_keyboard_input(prefisso, input_utente)
            
            if evento == "EXIT":
                logger.info("[APP] Shutdown di emergenza.")
                sys.exit(0)
            elif evento == "ESC_AGAIN":
                print(f"\n\033[93m[SISTEMA] ESC di nuovo per uscire.\033[0m")
            elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]:
                self._handle_function_key(evento, config)
                # Ricarica config nel caso sia stato modificato
                config = self.config_manager.config
                interfaccia.mostra_ui_completa(
                    config,
                    self.state_manager.stato_voce,
                    self.state_manager.stato_ascolto,
                    dashboard.get_backend_status()
                )
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

    def _handle_voice_input(self, prefisso):
        """Gestisce input vocale."""
        if dashboard.get_backend_status() != "PRONTA":
            print(f"\n\033[93m[SISTEMA] Backend non ancora pronto. Attendere...\033[0m")
            self.state_manager.comando_vocale_rilevato = None
            return

        self.state_manager.sistema_in_elaborazione = True
        testo_v = self.state_manager.comando_vocale_rilevato
        self.state_manager.comando_vocale_rilevato = None

        interfaccia.avvia_pensiero()
        sys.stdout.write(f"\r{' ' * 80}\r")
        print(f"{prefisso}\033[92mAdmin (Voce): {testo_v}\033[0m")
        print(f"\033[93m[Premi ESC per interrompere]\033[0m")

        stop_event = threading.Event()
        risultato = [None, None]
        errore = [None]

        def esegui():
            try:
                rv, tv = processore.elabora_scambio(testo_v, self.state_manager.stato_voce)
                risultato[0] = rv
                risultato[1] = tv
            except Exception as e:
                errore[0] = e

        thread = threading.Thread(target=esegui)
        thread.start()

        while thread.is_alive():
            if msvcrt.kbhit() and msvcrt.getch() == b'\x1b':
                stop_event.set()
                break
            time.sleep(0.1)

        if stop_event.is_set():
            interfaccia.ferma_pensiero()
            print(f"\n\033[93m[SISTEMA] Richiesta annullata.\033[0m")
            sys.stdout.write(prefisso)
            sys.stdout.flush()
            self.state_manager.sistema_in_elaborazione = False
            return

        thread.join()
        interfaccia.ferma_pensiero()

        if errore[0]:
            logger.errore(f"[APP] Errore ciclo vocale: {errore[0]}")
        else:
            risposta_video, testo_voce_pulito = risultato
            brain_interface.salva_messaggio("user", testo_v)
            brain_interface.salva_messaggio("assistant", risposta_video)
            interfaccia.scrivi_aura(risposta_video)
            if self.state_manager.stato_voce and testo_voce_pulito:
                voce.parla(testo_voce_pulito)

        sys.stdout.write(prefisso)
        sys.stdout.flush()
        self.state_manager.sistema_in_elaborazione = False
        
    def _get_model_sizes(self):
        """Recupera le dimensioni dei modelli da Ollama."""
        model_sizes = {}
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                for model in data.get('models', []):
                    name = model.get('name')
                    size = model.get('size', 0)
                    if size > 1024**3:
                        size_str = f"{size/(1024**3):.1f} GB"
                    elif size > 1024**2:
                        size_str = f"{size/(1024**2):.1f} MB"
                    else:
                        size_str = f"{size/1024:.0f} KB"
                    model_sizes[name] = size_str
        except Exception as e:
            logger.debug("APP", f"Impossibile recuperare dimensioni modelli: {e}")
        return model_sizes