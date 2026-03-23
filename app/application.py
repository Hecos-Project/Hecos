"""
Classe principale dell'applicazione Zentra.
"""

import sys
import time
import threading
import msvcrt
from core.logging import logger
from core.system import plugin_loader, diagnostica
from core.i18n import translator
from core.processing import processore
from core.audio import ascolto, voce
from ui import interfaccia, grafica, ui_updater
from ui.config_editor.core import ConfigEditor
from memoria import brain_interface
from .config import ConfigManager
from .state_manager import StateManager
from .input_handler import InputHandler
from .threads import AscoltoThread

class ZentraApplication:
    def __init__(self):
        self.config_manager = ConfigManager()
        
        cv = self.config_manager.get('voce', 'stato_voce', default=True)
        ca = self.config_manager.get('ascolto', 'stato_ascolto', default=True)
        self.state_manager = StateManager(stato_voce_iniziale=cv, stato_ascolto_iniziale=ca)
        
        self.input_handler = InputHandler(self.state_manager, self.config_manager)
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
        sys.stdout.write(f"\n\033[96m[SISTEMA] Sincronizzazione Rete Neurale e Memoria...\033[0m\n")
        for progresso in range(0, 101, 2):
            barra = grafica.crea_barra(progresso, larghezza=40, stile="cyber")
            sys.stdout.write(f"\r{barra}")
            sys.stdout.flush()
            time.sleep(0.04)
        time.sleep(0.5)

    def _show_welcome(self):
        """Mostra messaggio di benvenuto."""
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

    def _handle_f2(self, config):
        """Gestione F2 - Selezione modelli universale (Ollama, Kobold, Cloud)."""
        print(f"\n\n\033[96m[ GESTIONE MODELLI UNIFICATA ]\033[0m")
        
        all_models = [] # Lista di dict: {"name": str, "type": str, "provider": str}
        model_sizes = self._get_model_sizes()
        
        # 1. Recupero Modelli OLLAMA (Local)
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                for m in response.json().get('models', []):
                    all_models.append({"name": m['name'], "type": "ollama", "provider": "local"})
        except:
            # Fallback su config
            for m in config.get('backend', {}).get('ollama', {}).get('modelli_disponibili', {}).values():
                all_models.append({"name": m, "type": "ollama", "provider": "local"})
                
        # 2. Recupero Modelli KOBOLD (Local)
        for m in config.get('backend', {}).get('kobold', {}).get('modelli_disponibili', {}).values():
            # Evita duplicati se già presenti (rari tra backend diversi ma possibile)
            all_models.append({"name": m, "type": "kobold", "provider": "local"})

        # 3. Recupero Modelli CLOUD (Dinamico + Fallback)
        allow_cloud = config.get('llm', {}).get('allow_cloud', False)
        if allow_cloud:
            providers = config.get('llm', {}).get('providers', {})
            for provider_name, p_data in providers.items():
                api_key = p_data.get('api_key')
                cloud_models = []
                
                # Tentativo di recupero dinamico per Groq e OpenAI
                if provider_name in ["groq", "openai"] and api_key:
                    cloud_models = self._fetch_cloud_models(provider_name, api_key)
                
                # Se il recupero dinamico fallisce o non è supportato, usa la lista nel config
                if not cloud_models:
                    cloud_models = p_data.get('modelli', [])
                
                for m_name in cloud_models:
                    # Assicuriamoci che il nome abbia il prefisso del provider per LiteLLM
                    full_name = f"{provider_name}/{m_name}" if not m_name.startswith(f"{provider_name}/") else m_name
                    all_models.append({"name": full_name, "type": "cloud", "provider": provider_name})

        if not all_models:
            print(f"\033[91mNessun modello trovato. Controlla la configurazione.\033[0m")
            time.sleep(2)
            return

        # 4. Visualizzazione
        backend_attuale = config.get('backend', {}).get('tipo', 'ollama')
        modello_attuale = config.get('backend', {}).get(backend_attuale, {}).get('modello', '')
        
        print(f"\033[96mBackend attivo: {backend_attuale.upper()} | Modello: {modello_attuale}\033[0m\n")
        
        # Raggruppiamo per tipo per una visualizzazione ordinata
        current_section = ""
        for idx, m in enumerate(all_models, 1):
            section = f"{m['type'].upper()} ({m['provider'].upper()})"
            if section != current_section:
                print(f"\n\033[34m--- {section} ---\033[0m")
                current_section = section
            
            prefisso = "\033[92m >> " if m['name'] == modello_attuale else "    "
            size = model_sizes.get(m['name'], "")
            size_str = f" \033[90m[{size}]\033[0m" if size else ""
            
            print(f"{prefisso}[{idx:2}] {m['name']}{size_str}\033[0m")

        print(f"\n\033[93mSeleziona il numero del modello (o ESC per annullare):\033[0m")
        scelta = self._input_digitale_sicuro(">> ")
        
        if scelta and scelta != "ESC":
            try:
                idx = int(scelta) - 1
                if 0 <= idx < len(all_models):
                    target = all_models[idx]
                    nuovo_modello = target['name']
                    nuovo_tipo = target['type']
                    
                    # Aggiorna il tipo di backend principale
                    self.config_manager.set(nuovo_tipo, 'backend', 'tipo')
                    # Aggiorna il modello nella sezione specifica
                    self.config_manager.set(nuovo_modello, 'backend', nuovo_tipo, 'modello')
                    
                    # Se è un modello cloud, assicuriamoci di impostare il provider se serve (LiteLLM lo deduce dal nome di solito)
                    
                    self.config_manager.save()
                    print(f"\n\033[92m✅ Modello impostato su {nuovo_modello} ({nuovo_tipo})\033[0m")
                else:
                    print(f"\n\033[91mIndice non valido.\033[0m")
            except:
                print(f"\n\033[91mErrore nella selezione.\033[0m")
            time.sleep(2)

    def _handle_f3(self, config):
        """Gestione F3 - Selezione personalità."""
        anime_files = interfaccia.elenca_personalita()
        
        # Sincronizza config
        if anime_files:
            anime_dict = {str(i+1): name for i, name in enumerate(anime_files)}
            self.config_manager.set(anime_dict, 'ia', 'personalita_disponibili')
            self.config_manager.save()
            
        if not anime_files:
            print(f"\n\033[91m[!] Nessun file .txt in /personalita!\033[0m")
            time.sleep(1)
        else:
            print(f"\n\n\033[96m--- SELEZIONE ANIMA (PERSONALITÀ) ---\033[0m")
            for i, nome_file in enumerate(anime_files, 1):
                print(f" [{i}] {nome_file}")
            
            scelta = self._input_digitale_sicuro("Seleziona numero (o ESC per annullare): ")
            if scelta == "ESC":
                print(f"\033[93m[SISTEMA] Operazione annullata.\033[0m")
                return
                
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
            self.state_manager.stato_ascolto = not self.state_manager.stato_ascolto
            self.config_manager.set(self.state_manager.stato_ascolto, 'ascolto', 'stato_ascolto')
            self.config_manager.save()
            verb = "ON" if self.state_manager.stato_ascolto else "OFF"
            color = "\033[96m" if self.state_manager.stato_ascolto else "\033[91m"
            print(f"\n{color}[SISTEMA] Ascolto: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F5":
            self.state_manager.stato_voce = not self.state_manager.stato_voce
            self.config_manager.set(self.state_manager.stato_voce, 'voce', 'stato_voce')
            self.config_manager.save()
            verb = "ON" if self.state_manager.stato_voce else "OFF"
            color = "\033[96m" if self.state_manager.stato_voce else "\033[91m"
            print(f"\n{color}[SISTEMA] Voce: {verb}\033[0m")
            time.sleep(0.5)
            
        elif key == "F6":
            print(f"\n\033[91m[SISTEMA] REBOOT IN CORSO...\033[0m")
            # Chiudi la finestra dei log esterna se presente
            logger.chiudi_console_log()
            time.sleep(1)
            sys.exit(42)
            
        elif key == "F7":
            editor = ConfigEditor()
            editor.run()
            # Ricarica la configurazione dopo l'editor
            self.config_manager.reload()
            logger.init_logger(self.config_manager.config)

    def run(self):
        """Avvia il loop principale dell'applicazione."""
        self._initialize()
        
        config = self.config_manager.config
        prefisso = f"\n\033[91m# \033[0m"
        input_utente = ""
        
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")

        # UI iniziale (Stato sistema dinamico da StateManager)
        interfaccia.mostra_ui_completa(
            config,
            self.state_manager.stato_voce,
            self.state_manager.stato_ascolto,
            self.state_manager.sistema_status
        )

        self._show_boot_animation()
        
        self.state_manager.sistema_status = "PRONTA"
        interfaccia.mostra_ui_completa(
            config,
            self.state_manager.stato_voce,
            self.state_manager.stato_ascolto,
            self.state_manager.sistema_status
        )

        # Avvia aggiornamento in-place della riga hardware (no flickering) solo se il plugin è attivo
        if dashboard_mod:
            ui_updater.avvia(self.config_manager, self.state_manager, dashboard_mod)
        else:
            # Assicuriamoci che l'updater sia fermo (utile se siamo in un loop di ricaricamento)
            ui_updater.ferma()

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
                # Sospendi UI updater per evitare corruzione grafica a schermo intero
                menu_schermo_intero = ["F1", "F2", "F3", "F7"]
                if evento in menu_schermo_intero:
                    ui_updater.ferma()
                    time.sleep(0.1) # Assicura che si fermi il vecchio thread
                    
                self._handle_function_key(evento, config)
                
                # Ricarica config nel caso sia stato modificato
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

    def _handle_voice_input(self, prefisso):
        """Gestisce input vocale."""
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod and dashboard_mod.get_backend_status() != "PRONTA":
            print(f"\n\033[93m[SISTEMA] Backend non ancora pronto. Attendere...\033[0m")
            self.state_manager.comando_vocale_rilevato = None
            return

        self.state_manager.sistema_in_elaborazione = True
        testo_v = self.state_manager.comando_vocale_rilevato
        self.state_manager.comando_vocale_rilevato = None

        self.state_manager.sistema_status = translator.t("thinking")
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
            interfaccia.scrivi_zentra(risposta_video)
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

    def _fetch_cloud_models(self, provider, api_key):
        """Tenta di recuperare la lista modelli direttamente dalle API del provider."""
        import requests
        try:
            url = ""
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/models"
            elif provider == "openai":
                url = "https://api.openai.com/v1/models"
            else:
                return []
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                data = response.json().get('data', [])
                return [m['id'] for m in data]
        except:
            pass
        return []

if __name__ == "__main__":
    app = ZentraApplication()
    app.run()