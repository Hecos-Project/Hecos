"""
Gestione input tastiera e vocale.
"""

import sys
import time
import threading
import msvcrt
from ui import interface
from core.processing import processore
from core.audio import voce
from core.logging import logger
from core.system import plugin_loader
from core.i18n import translator
from memory import brain_interface
# sys è importato a livello di modulo - NON usare 'import sys' inline nei metodi

class InputHandler:
    def __init__(self, state_manager, config_manager):
        self.state = state_manager
        self.config = config_manager

    def handle_keyboard_input(self, prefisso, input_utente):
        """Gestisce input da tastiera."""
        evento, nuovo_input = interface.leggi_tastiera(prefisso, input_utente)
        
        if evento == "ENTER":
            return self._process_text_input(nuovo_input, prefisso)
        elif evento == "CLEAR":
            return "CLEAR", ""
        elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]:
            return evento, nuovo_input
        elif evento == "ESC":
            return self._handle_esc(prefisso)
        
        return None, nuovo_input

    def handle_voice_input(self, prefisso):
        """Gestisce input vocale."""
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            tools = getattr(dashboard_mod, "tools", None)
            raw_fn = getattr(tools, "_get_raw_backend_status", None) if tools else None
            if raw_fn and raw_fn() not in ["READY", "CLOUD", "ONLINE"]:
                print(f"\n\033[93m[SYSTEM] Backend not ready yet. Please wait...\033[0m")
                self.state.comando_vocale_rilevato = None
                return

        testo_v = self.state.comando_vocale_rilevato
        self.state.comando_vocale_rilevato = None
        
        # Indica che stiamo processando input vocale
        self._execute_exchange(testo_v, prefisso, is_voice=True)

    def _process_text_input(self, testo, prefisso):
        """Processa input testuale."""
        if not testo.strip():
            return None, testo
            
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            tools = getattr(dashboard_mod, "tools", None)
            raw_fn = getattr(tools, "_get_raw_backend_status", None) if tools else None
            if raw_fn:
                raw_status = raw_fn()
                if raw_status not in ["READY", "CLOUD", "ONLINE"]:
                    print(f"\n\033[93m[SYSTEM] Backend not ready ({raw_status}). Please wait...\033[0m")
                    return None, ""
            
        self._execute_exchange(testo, prefisso, is_voice=False)
        return "PROCESSED", ""

    def _execute_exchange(self, testo, prefisso, is_voice=False):
        """Esegue lo scambio (testo -> risposta) con supporto ESC."""
        self.state.sistema_in_elaborazione = True
        self.state.sistema_status = translator.t("thinking")
        
        # Feedback visivo
        sys.stdout.write(f"\r{' ' * 80}\r")
        label = "Admin (Voce)" if is_voice else "Admin"
        print(f"{prefisso}\033[92m{label}: {testo}\033[0m")
        print(f"\033[93m[{translator.t('press_esc_to_stop')}]\033[0m")
        
        interface.avvia_pensiero()
        
        risultato = [None, None]
        errore = [None]
        stop_event = threading.Event()

        def esegui():
            try:
                rv, tv = processore.elabora_scambio(testo, self.state.stato_voce)
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
            interface.ferma_pensiero()
            voce.ferma_voce() # Interrompe immediatamente l'audio se in riproduzione
            # Pulisci il buffer della tastiera da eventuali ESC multipli premuti tenendo premuto il tasto
            while msvcrt.kbhit():
                msvcrt.getch()
            print(f"\n\033[93m[SYSTEM] {translator.t('request_cancelled')}\033[0m")
            self.state.sistema_status = translator.t("ready")
            self.state.sistema_in_elaborazione = False
            sys.stdout.write(prefisso)
            sys.stdout.flush()
            return

        thread.join()
        interface.ferma_pensiero()

        if errore[0]:
            logger.errore(f"[INPUT] Error: {errore[0]}")
        else:
            risposta_video, testo_voce_pulito = risultato
            # Salvataggio in memoria
            brain_interface.salva_messaggio("user", testo)
            brain_interface.salva_messaggio("assistant", risposta_video)
            
            # Mostra la risposta
            interface.scrivi_zentra(risposta_video)
            if self.state.stato_voce and testo_voce_pulito:
                self.state.sistema_status = translator.t("speaking")
                interface.aggiorna_barra_stato_in_place(
                    self.config.config, 
                    self.state.stato_voce, 
                    self.state.stato_ascolto, 
                    self.state.sistema_status
                )
                voce.parla(testo_voce_pulito, state=self.state)
                # Al termine della voce, torna a PRONTO (già gestito in fondo al metodo)

        self.state.sistema_status = translator.t("ready")
        self.state.sistema_in_elaborazione = False
        # Forza un refresh della barra di stato per rimuovere "PENSANDO" o "PARLANDO"
        interface.aggiorna_barra_stato_in_place(
            self.config.config, 
            self.state.stato_voce, 
            self.state.stato_ascolto, 
            self.state.sistema_status
        )
        # Ripristina il prompt a video per il prossimo input
        sys.stdout.write(prefisso)
        sys.stdout.flush()

    def _handle_esc(self, prefisso):
        """Gestisce pressione ESC: ferma la voce e, se necessario, chiede conferma uscita."""
        ora = time.time()
        # Se la voce è stata fermata manualmente da pochissimo, ignora questo ESC (race condition buffer)
        if ora - self.state.ultimo_stop_voce < 0.5:
            return "CANCELLED", "" # Ignora silenziosamente

        # Se Zentra stava parlando, ESC deve solo fermare la voce e tornare al prompt
        if self.state.sistema_parla or voce.sta_parlando:
            voce.ferma_voce()
            self.state.sistema_parla = False
            return "PROCESSED", "" # Torna al prompt
            
        # Altrimenti, chiede conferma per uscire
        sys.stdout.write(f"\n\033[93m[SYSTEM] {translator.t('confirm_exit')} (S/N): \033[0m")
        sys.stdout.flush()
        
        # Aspetta un carattere S o N
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch().decode('utf-8', errors='ignore').upper()
                if ch == 'S':
                    print("S")
                    return "EXIT", None
                elif ch == 'N':
                    print("N")
                    sys.stdout.write(f"\r{' ' * 50}\r{prefisso}")
                    sys.stdout.flush()
                    return "CANCELLED", "" # Torna al prompt senza uscire
                elif ch == '\x1b': # ESC di nuovo per annullare
                    sys.stdout.write(f"\r{' ' * 50}\r{prefisso}")
                    sys.stdout.flush()
                    return "CANCELLED", ""
            time.sleep(0.05)