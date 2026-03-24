"""
Gestione thread separati.
"""

import threading
import time
from core.audio import ascolto, voce
from core.logging import logger

class AscoltoThread(threading.Thread):
    def __init__(self, state_manager):
        super().__init__(daemon=True)
        self.state = state_manager
        self.name = "AscoltoPassivo"

    def run(self):
        logger.info("[LISTENING THREAD] Initialized.")
        while True:
            if (self.state.stato_ascolto and 
                not voce.sta_parlando and 
                not self.state.sistema_in_elaborazione):
                testo = ascolto.ascolta()
                if testo and len(testo.strip()) > 1:
                    logger.info(f"[LISTENING THREAD] Input detected: '{testo}'")
                    self.state.comando_vocale_rilevato = testo
            time.sleep(0.2)