"""
MODULO: Config Editor - Aura Core v0.7
DESCRIZIONE: Editor interattivo a console per modificare i parametri di config.json
in tempo reale. Utilizzabile sia dal menu principale (tasto F7) che come script separato.
"""

import os
import sys
import json
import msvcrt
import time
from core import grafica

# Costanti per i tasti (codici ASCII)
KEY_UP = 72
KEY_DOWN = 80
KEY_LEFT = 75
KEY_RIGHT = 77
KEY_ENTER = 13
KEY_ESC = 27
KEY_SPACE = 32

# Percorso del file di lock per accesso concorrente
LOCK_FILE = "config.lock"

class ConfigEditor:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.original_config = json.dumps(self.config, sort_keys=True)  # per rilevare modifiche
        self.modified = False
        self.cursor_pos = 0          # indice del parametro selezionato
        self.edit_mode = False        # se True, si sta modificando il valore
        self.temp_value = None        # valore temporaneo durante modifica
        self.param_list = self._build_param_list()
        self.lock_acquired = False

    def _load_config(self):
        """Carica il file di configurazione."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore caricamento config: {e}")
            sys.exit(1)

    def _save_config(self):
        """Salva il file di configurazione se modificato."""
        if self.modified:
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                print("\n✅ Configurazione salvata con successo.")
            except Exception as e:
                print(f"\n❌ Errore salvataggio: {e}")

    def _build_param_list(self):
        """
        Costruisce una lista di parametri modificabili.
        Ogni elemento è un dict con:
            - section: la sezione del config (es. "ia")
            - key: la chiave (es. "temperature")
            - label: nome leggibile
            - type: tipo (float, int, bool, str)
            - min, max, step: per numeri
            - getter/setter opzionali
        """
        params = []

        # Sezione IA
        ia = self.config.get('ia', {})
        params.append({
            'section': 'ia',
            'key': 'modello_attivo',
            'label': 'Modello attivo',
            'type': 'str',
            'options': list(ia.get('modelli_disponibili', {}).values()) if 'modelli_disponibili' in ia else None
        })
        params.append({
            'section': 'ia',
            'key': 'temperature',
            'label': 'Temperatura',
            'type': 'float',
            'min': 0.0,
            'max': 2.0,
            'step': 0.1
        })
        params.append({
            'section': 'ia',
            'key': 'num_predict',
            'label': 'Num predict',
            'type': 'int',
            'min': 100,
            'max': 2000,
            'step': 50
        })

        # Sezione Voce
        voce = self.config.get('voce', {})
        params.append({
            'section': 'voce',
            'key': 'speed',
            'label': 'Velocità voce',
            'type': 'float',
            'min': 0.5,
            'max': 2.0,
            'step': 0.05
        })
        params.append({
            'section': 'voce',
            'key': 'pitch',
            'label': 'Tono voce',
            'type': 'int',
            'min': 0,
            'max': 10,
            'step': 1
        })

        # Sezione Ascolto
        ascolto = self.config.get('ascolto', {})
        params.append({
            'section': 'ascolto',
            'key': 'soglia_energia',
            'label': 'Soglia energia',
            'type': 'int',
            'min': 100,
            'max': 1000,
            'step': 50
        })
        params.append({
            'section': 'ascolto',
            'key': 'timeout_silenzio',
            'label': 'Timeout silenzio (s)',
            'type': 'int',
            'min': 1,
            'max': 10,
            'step': 1
        })

        # Sezione Filtri
        filtri = self.config.get('filtri', {})
        params.append({
            'section': 'filtri',
            'key': 'rimuovi_asterischi',
            'label': 'Rimuovi asterischi',
            'type': 'bool'
        })
        params.append({
            'section': 'filtri',
            'key': 'rimuovi_parentesi_tonde',
            'label': 'Rimuovi parentesi tonde',
            'type': 'bool'
        })
        params.append({
            'section': 'filtri',
            'key': 'rimuovi_parentesi_quadre',
            'label': 'Rimuovi parentesi quadre',
            'type': 'bool'
        })

        return params

    def _get_value(self, param):
        """Restituisce il valore corrente del parametro."""
        return self.config.get(param['section'], {}).get(param['key'])

    def _set_value(self, param, value):
        """Imposta il valore e segna come modificato."""
        if param['section'] not in self.config:
            self.config[param['section']] = {}
        old = self.config[param['section']].get(param['key'])
        if old != value:
            self.config[param['section']][param['key']] = value
            self.modified = True

    def _format_value(self, param, value):
        """Formatta il valore per la visualizzazione."""
        if param['type'] == 'bool':
            return "[X]" if value else "[ ]"
        elif param['type'] == 'float':
            return f"{value:.2f}"
        else:
            return str(value)

    def _render_bar(self, param, value):
        """Genera una barra di progresso se il parametro è numerico con min/max."""
        if param['type'] in ('int', 'float') and 'min' in param and 'max' in param:
            percent = (value - param['min']) / (param['max'] - param['min']) * 100
            return grafica.crea_barra(percent, larghezza=15)
        return ""

    def acquire_lock(self):
        """Acquisisce il lock per evitare accessi concorrenti."""
        while os.path.exists(LOCK_FILE):
            time.sleep(0.1)
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        self.lock_acquired = True

    def release_lock(self):
        """Rilascia il lock."""
        if self.lock_acquired and os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        self.lock_acquired = False

    def run(self):
        """Avvia l'editor interattivo."""
        self.acquire_lock()
        try:
            self._main_loop()
        finally:
            self.release_lock()
            if self.modified:
                self._save_config()

    def _main_loop(self):
        """Ciclo principale dell'editor."""
        while True:
            self._clear_screen()
            self._draw_interface()
            key = self._get_key()

            if key == KEY_ESC:
                if self.modified:
                    # Chiedi conferma prima di uscire senza salvare
                    self._draw_message("Modifiche non salvate. Uscire lo stesso? (s/n)")
                    confirm = self._get_key()
                    if confirm == ord('s') or confirm == ord('S'):
                        break
                else:
                    break

            elif key == KEY_ENTER:
                # Salva ed esci
                break

            elif key == KEY_UP:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    self.edit_mode = False

            elif key == KEY_DOWN:
                if self.cursor_pos < len(self.param_list) - 1:
                    self.cursor_pos += 1
                    self.edit_mode = False

            elif key == KEY_LEFT or key == KEY_RIGHT:
                param = self.param_list[self.cursor_pos]
                current = self._get_value(param)
                if param['type'] in ('int', 'float') and 'min' in param and 'max' in param:
                    step = param['step']
                    if key == KEY_LEFT:
                        new_val = current - step
                    else:
                        new_val = current + step
                    # Applica limiti
                    if new_val < param['min']:
                        new_val = param['min']
                    if new_val > param['max']:
                        new_val = param['max']
                    self._set_value(param, new_val)
                elif param['type'] == 'bool':
                    # Inverte il booleano
                    self._set_value(param, not current)
                elif param['type'] == 'str' and param.get('options'):
                    # Scorre le opzioni
                    idx = param['options'].index(current) if current in param['options'] else 0
                    if key == KEY_LEFT:
                        idx = (idx - 1) % len(param['options'])
                    else:
                        idx = (idx + 1) % len(param['options'])
                    self._set_value(param, param['options'][idx])

            elif key == KEY_SPACE:
                # Per i booleani, spazio funziona come toggle
                param = self.param_list[self.cursor_pos]
                if param['type'] == 'bool':
                    current = self._get_value(param)
                    self._set_value(param, not current)

    def _get_key(self):
        """Legge un tasto dalla tastiera, gestendo i tasti freccia."""
        ch = msvcrt.getch()
        if ch == b'\x00' or ch == b'\xe0':
            # Tasto speciale (frecce)
            ch2 = msvcrt.getch()
            return ord(ch2)
        return ord(ch)

    def _clear_screen(self):
        """Pulisce lo schermo."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _draw_interface(self):
        """Disegna l'interfaccia principale."""
        # Intestazione
        print("╔" + "═" * 58 + "╗")
        print("║{:^58}║".format(" AURA CONFIG EDITOR "))
        print("╠" + "═" * 58 + "╣")

        # Lista parametri
        for i, param in enumerate(self.param_list):
            value = self._get_value(param)
            formatted = self._format_value(param, value)
            bar = self._render_bar(param, value)
            # Indicatore di selezione
            prefix = " > " if i == self.cursor_pos else "   "
            # Colore? Magari dopo.
            line = f"{prefix}{param['label']}: {formatted}"
            if bar:
                line += f"  {bar}"
            # Tronca se troppo lunga
            if len(line) > 58:
                line = line[:55] + "..."
            print("║ {:<56} ║".format(line))

        # Footer
        print("╠" + "═" * 58 + "╣")
        footer = " ↑/↓: naviga | ←/→: modifica | Enter: salva | Esc: esci "
        print("║{:<56}║".format(footer))
        print("╚" + "═" * 58 + "╝")

        if self.modified:
            print(" Modifiche non salvate.")

    def _draw_message(self, msg):
        """Mostra un messaggio temporaneo in fondo."""
        print("\n" + msg)