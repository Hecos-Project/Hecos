"""
Gestione input tastiera e vocale.
"""

import sys
import time
import threading
import msvcrt
from ui import interfaccia
from core import processore, voce, logger
from plugins import dashboard

class InputHandler:
    def __init__(self, state_manager, config_manager):
        self.state = state_manager
        self.config = config_manager

    def handle_keyboard_input(self, prefisso, input_utente):
        """Gestisce input da tastiera."""
        evento, nuovo_input = interfaccia.leggi_tastiera(prefisso, input_utente)
        
        if evento == "ENTER":
            return self._process_text_input(nuovo_input, prefisso)
        elif evento == "CLEAR":
            return "CLEAR", ""
        elif evento in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]:
            return evento, nuovo_input
        elif evento == "ESC":
            return self._handle_esc()
        
        return None, nuovo_input

    def _process_text_input(self, testo, prefisso):
        """Processa input testuale."""
        if not testo.strip():
            return None, testo
            
        if dashboard.get_backend_status() != "PRONTA":
            print(f"\n\033[93m[SISTEMA] Backend non pronto. Attendere...\033[0m")
            return None, ""
            
        self.state.sistema_in_elaborazione = True
        
        # --- STAMPA IL MESSAGGIO DELL'UTENTE (come per input vocale) ---
        sys.stdout.write(f"\r{' ' * 80}\r")
        print(f"{prefisso}\033[92mAdmin: {testo}\033[0m")
        print(f"\033[93m[Premi ESC per interrompere]\033[0m")
        # --------------------------------------------------------------
        
        interfaccia.avvia_pensiero()
        
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

        # Gestione interruzione ESC
        while thread.is_alive():
            if msvcrt.kbhit() and msvcrt.getch() == b'\x1b':
                stop_event.set()
                break
            time.sleep(0.1)

        if stop_event.is_set():
            interfaccia.ferma_pensiero()
            print(f"\n\033[93m[SISTEMA] Richiesta annullata.\033[0m")
            self.state.sistema_in_elaborazione = False
            return "CLEAR", ""

        thread.join()
        interfaccia.ferma_pensiero()

        if errore[0]:
            logger.errore(f"[INPUT] Errore: {errore[0]}")
        else:
            risposta_video, testo_voce_pulito = risultato
            # Mostra la risposta
            interfaccia.scrivi_aura(risposta_video)
            if self.state.stato_voce and testo_voce_pulito:
                voce.parla(testo_voce_pulito)

        self.state.sistema_in_elaborazione = False
        return "PROCESSED", ""

    def _handle_esc(self):
        """Gestisce pressione ESC."""
        ora = time.time()
        if ora - self.state.ultimo_esc < 0.5:
            return "EXIT", None
        else:
            self.state.ultimo_esc = ora
            return "ESC_AGAIN", None