"""
Gestione centralizzata degli stati dell'applicazione.
"""

import threading

class StateManager:
    def __init__(self, stato_voce_iniziale=True, stato_ascolto_iniziale=True):
        self._stato_voce = stato_voce_iniziale
        self._stato_ascolto = stato_ascolto_iniziale
        self._ultimo_esc = 0
        self._comando_vocale_rilevato = None
        self._sistema_in_elaborazione = False
        self._lock = threading.Lock()

    # Proprietà con lock per thread safety
    @property
    def stato_voce(self):
        with self._lock:
            return self._stato_voce

    @stato_voce.setter
    def stato_voce(self, value):
        with self._lock:
            self._stato_voce = value

    @property
    def stato_ascolto(self):
        with self._lock:
            return self._stato_ascolto

    @stato_ascolto.setter
    def stato_ascolto(self, value):
        with self._lock:
            self._stato_ascolto = value

    @property
    def ultimo_esc(self):
        with self._lock:
            return self._ultimo_esc

    @ultimo_esc.setter
    def ultimo_esc(self, value):
        with self._lock:
            self._ultimo_esc = value

    @property
    def comando_vocale_rilevato(self):
        with self._lock:
            return self._comando_vocale_rilevato

    @comando_vocale_rilevato.setter
    def comando_vocale_rilevato(self, value):
        with self._lock:
            self._comando_vocale_rilevato = value

    @property
    def sistema_in_elaborazione(self):
        with self._lock:
            return self._sistema_in_elaborazione

    @sistema_in_elaborazione.setter
    def sistema_in_elaborazione(self, value):
        with self._lock:
            self._sistema_in_elaborazione = value