"""
Gestione dell'interfaccia utente: disegno e interazione.
"""

from .utils import clear_screen, get_key, flush_input
from ui import grafica
import sys

# Costanti tasti
KEY_UP = 72
KEY_DOWN = 80
KEY_LEFT = 75
KEY_RIGHT = 77
KEY_ENTER = 13
KEY_ESC = 27
KEY_SPACE = 32

# Colori ANSI (base)
GIALLO = '\033[93m'
VERDE = '\033[92m'
ROSSO = '\033[91m'
CIANO = '\033[96m'
RESET = '\033[0m'

class UIManager:
    def __init__(self, param_list, getter, setter):
        self.param_list = param_list
        self.get_value = getter
        self.set_value = setter
        self.cursor = 0
        self.modified = False
        self.first_draw = True

    def run(self):
        # Nasconde il cursore lampeggiante del terminale
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()
        flush_input()
        try:
            while True:
                self._draw()
                key = self._wait_for_key()

                if key == KEY_ESC:
                    if self.modified:
                        if self._confirm("Uscire senza salvare? (s/n)"):
                            break
                    else:
                        break
                elif key == KEY_ENTER:
                    break
                elif key == KEY_UP:
                    if self.cursor > 0:
                        self.cursor -= 1
                elif key == KEY_DOWN:
                    if self.cursor < len(self.param_list) - 1:
                        self.cursor += 1
                elif key == KEY_LEFT or key == KEY_RIGHT:
                    param = self.param_list[self.cursor]
                    if param.type == 'command':
                        if param.command == 'reboot':
                            print(f"\n{GIALLO}Riavvio in corso...{RESET}")
                            return "REBOOT"
                    else:
                        current = self.get_value(param)
                        if param.type in ('int', 'float') and param.min is not None:
                            step = param.step or 1
                            new_val = current - step if key == KEY_LEFT else current + step
                            # Arrotonda per evitare precisione float fastidiosa
                            new_val = round(max(param.min, min(param.max, new_val)), 2)
                            self.set_value(param, new_val)
                            self.modified = True
                        elif param.type == 'bool':
                            self.set_value(param, not current)
                            self.modified = True
                        elif param.type == 'str' and param.options:
                            try:
                                idx = param.options.index(current) if current in param.options else 0
                            except ValueError:
                                idx = 0
                            idx = (idx - 1) % len(param.options) if key == KEY_LEFT else (idx + 1) % len(param.options)
                            self.set_value(param, param.options[idx])
                            self.modified = True
                elif key == KEY_SPACE:
                    param = self.param_list[self.cursor]
                    if param.type == 'bool':
                        current = self.get_value(param)
                        self.set_value(param, not current)
                        self.modified = True
        finally:
            # Ripristina il cursore 
            sys.stdout.write('\033[?25h')
            sys.stdout.flush()
        return self.modified

    def _wait_for_key(self):
        while True:
            ch = get_key(timeout=None)
            if ch is not None:
                return ch

    def _draw(self):
        clear_screen(first_time=self.first_draw)
        self.first_draw = False
        
        # Importa le informazioni di versione centralizzate
        from core.version import get_version_string
        
        # Intestazione compatta fusa (1 sola riga) per risparmiare spazio verticale!
        intestazione = f" {get_version_string()} - CONFIGURAZIONE SISTEMA "
        print(f"\033[44m\033[97m{intestazione.center(60)}\033[0m")
        
        # Definizione delle sezioni e degli indici dei parametri
        sezioni = {
            "🤖 MODELLO": [0],  # Indice del modello attivo
            "⚙️ GENERAZIONE": [1, 2, 3, 4],  # Temperatura, Num predict, Contesto, Layer GPU
            "🔊 VOCE": [5, 6, 7, 8],  # Velocità, Variabilità, Fluidità, Pausa
            "🎤 ASCOLTO": [9, 10],  # Soglia energia, Timeout silenzio
            "📝 FILTRI": [11, 12, 13],  # Filtri vari
            "📊 LOGGING": [14, 15], # Destinazione, Tipo
            "⚡ SISTEMA": [16]  # RIAVVIA AURA
        }

        idx = 0
        for nome_sezione, indici in sezioni.items():
            # Stampa intestazione sezione
            print(f"{CIANO}├─ {nome_sezione} ─────────────────────────────{RESET}")
            
            for i in indici:
                if i >= len(self.param_list):
                    continue
                    
                param = self.param_list[i]
                
                # Gestione separata per i comandi
                if param.type == 'command':
                    disp = "▶ Esegui"
                    bar = ""
                else:
                    value = self.get_value(param)
                    # Gestione valori None
                    if value is None:
                        disp = "N/A"
                    else:
                        # Formatta il valore in base al tipo
                        if param.type == 'bool':
                            disp = "[X]" if value else "[ ]"
                        elif param.type == 'float':
                            disp = f"{value:.2f}"
                        else:
                            disp = str(value)
                    
                    # Barra rimossa per evitare confusioni con la dashboard HW
                    bar = ""

                # Formatta il testo senza colori
                prefisso = " > " if self.cursor == i else "   "
                testo_base = f"{prefisso}{param.label}: {disp}"
                
                # Tronca o riempi per avere larghezza fissa esatta (56 char)
                if len(testo_base) > 56:
                    testo_base = testo_base[:53] + "..."
                else:
                    testo_base = f"{testo_base:<56}"

                # Costruzione riga finale con colori
                if self.cursor == i:
                    linea_finale = f"{VERDE}{testo_base}{RESET}"
                else:
                    linea_finale = testo_base
                
                print(f"| {linea_finale} |")
                idx += 1

        # Footer compatto (1 riga)
        footer = " ↑/↓: naviga | ←/→: modifica | Invio: salva | Esc: esci "
        print(f"\033[47m\033[30m{footer.center(60)}\033[0m")
        
        if self.modified:
            print(f"{GIALLO} Modifiche non salvate.{RESET}{' ' * 30}")
        else:
            print(f"{' ' * 56}")

    def _confirm(self, message):
        print(f"\n{GIALLO}{message}{RESET}")
        while True:
            ch = self._wait_for_key()
            if ch in (ord('s'), ord('S')):
                return True
            if ch in (ord('n'), ord('N'), KEY_ESC):
                return False