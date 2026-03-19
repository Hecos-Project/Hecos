"""
Gestione thread separati.
"""

import threading
import time
from core import ascolto, voce, logger

class AscoltoThread(threading.Thread):
    def __init__(self, state_manager):
        super().__init__(daemon=True)
        self.state = state_manager
        self.name = "AscoltoPassivo"

    def run(self):
        logger.info("[THREAD ASCOLTO] Inizializzato.")
        while True:
            if (self.state.stato_ascolto and 
                not voce.sta_parlando and 
                not self.state.sistema_in_elaborazione):
                testo = ascolto.ascolta()
                if testo and len(testo.strip()) > 1:
                    logger.info(f"[THREAD ASCOLTO] Input rilevato: '{testo}'")
                    self.state.comando_vocale_rilevato = testo
            time.sleep(0.2)