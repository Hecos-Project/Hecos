"""
Gestione dell'interfaccia utente: disegno e interazione.
"""

from .utils import clear_screen, get_key, flush_input
from ui import grafica
import sys
import shutil
from collections import OrderedDict

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
        self.scroll_top = 0      # Indice della riga in alto nel viewport
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
                    # Se il parametro è una stringa libera, attiva modifica
                    param = self.param_list[self.cursor]
                    if param.type == 'str' and not param.options:
                        self._edit_string(param)
                    else:
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
                        if param.type in ('int', 'float'):
                            # Determina step e limiti
                            if param.type == 'int':
                                step = param.step or 1
                            else:
                                step = param.step or 0.1
                            if key == KEY_LEFT:
                                new_val = current - step
                            else:
                                new_val = current + step
                            # Applica limiti se presenti
                            if param.min is not None:
                                new_val = max(param.min, new_val)
                            if param.max is not None:
                                new_val = min(param.max, new_val)
                            # Arrotonda per evitare precisione float fastidiosa
                            if param.type == 'float':
                                new_val = round(new_val, 2)
                            else:
                                new_val = int(new_val)
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

    def _edit_string(self, param):
        """Modifica una stringa libera con input utente."""
        current = self.get_value(param) or ""
        # Mostra prompt
        print(f"\n{GIALLO}Modifica {param.label}:{RESET}")
        print(f"Valore attuale: {current}")
        print("Inserisci nuovo valore (Invio per confermare, ESC per annullare):")
        # Leggi input
        new_val = input().strip()
        if new_val:  # se l'utente ha inserito qualcosa
            self.set_value(param, new_val)
            self.modified = True
            print(f"{VERDE}Valore aggiornato.{RESET}")
        else:
            print(f"{GIALLO}Modifica annullata.{RESET}")
        # Attendi un momento per far leggere il messaggio
        import time
        time.sleep(1)

    def _wait_for_key(self):
        while True:
            ch = get_key(timeout=None)
            if ch is not None:
                return ch

    def _get_section_title(self, param):
        """Restituisce il titolo della sezione per un parametro."""
        if param.section == 'system':
            return "⚡ SISTEMA"
        elif param.section == 'logging':
            return "📊 LOGGING"
        elif param.section == 'filtri':
            return "📝 FILTRI"
        elif param.section == 'ascolto':
            return "🎤 ASCOLTO"
        elif param.section == 'voce':
            return "🔊 VOCE"
        elif param.section == 'backend':
            # Distingue modello dagli altri parametri di backend
            if param.key == 'modello':
                return "🤖 MODELLO"
            else:
                return "⚙️ GENERAZIONE"
        elif param.section == 'plugin':
            return f"🔌 {param.plugin_tag}"
        else:
            return "ALTRO"

    def _draw(self):
        clear_screen(first_time=self.first_draw)
        self.first_draw = False
        
        from core.system.version import get_version_string
        
        # Intestazione
        intestazione = f" {get_version_string()} - CONFIGURAZIONE SISTEMA "
        print(f"\033[44m\033[97m{intestazione.center(60)}\033[0m")
        
        # 1. Genera lista piatta di "righe renderizzabili"
        all_rows = [] # Conterrà tuple (tipo, contenuto, param_idx)
        
        sections = OrderedDict()
        for i, param in enumerate(self.param_list):
            title = self._get_section_title(param)
            sections.setdefault(title, []).append((i, param))
        
        order_standard = ["🤖 MODELLO", "⚙️ GENERAZIONE", "🔊 VOCE", "🎤 ASCOLTO", "📝 FILTRI", "📊 LOGGING", "⚡ SISTEMA"]
        
        def add_section_to_rows(title, params_with_idx):
            all_rows.append(('header', title, None))
            for p_idx, p in params_with_idx:
                all_rows.append(('param', p, p_idx))

        # Aggiungi sezioni standard
        for title in order_standard:
            if title in sections:
                add_section_to_rows(title, sections[title])
                sections.pop(title, None)
        
        # Aggiungi plugin
        for title, params in sections.items():
            add_section_to_rows(title, params)

        # 2. Gestione scorrimento (Viewport)
        # Ottieni altezza terminale attuale e calcola limite sicuro
        try:
            # Svuota buffer terminale per evitare letture vecchie
            term_size = shutil.get_terminal_size()
            term_height = term_size.lines
            # Riserva solo lo stretto necessario (2 righe per header/footer + 1 per margine)
            safe_limit = max(10, term_height - 4)
        except:
            safe_limit = 30 # Fallback più generoso
            
        # Altezza dinamica: mostra tutto se possibile, altrimenti usa il limite
        viewport_height = min(len(all_rows), safe_limit)
        
        # Trova la riga corrispondente al cursore attuale
        cursor_row_idx = 0
        for idx, row in enumerate(all_rows):
            if row[0] == 'param' and row[2] == self.cursor:
                cursor_row_idx = idx
                break

        # Aggiusta scroll_top per tenere il cursore nel viewport
        if cursor_row_idx < self.scroll_top:
            self.scroll_top = cursor_row_idx
        elif cursor_row_idx >= self.scroll_top + viewport_height:
            self.scroll_top = cursor_row_idx - viewport_height + 1

        # 3. Disegna il viewport con Scrollbar
        visible_rows = all_rows[self.scroll_top : self.scroll_top + viewport_height]
        
        # Calcolo scrollbar
        total_rows = len(all_rows)
        thumb_range = None
        if total_rows > viewport_height:
            # Dimensione thumb (minimo 1 riga)
            thumb_size = max(1, int((viewport_height / total_rows) * viewport_height))
            # Escursione possibile per il thumb
            scroll_range = total_rows - viewport_height
            if scroll_range > 0:
                # Proporzione dello scroll attuale
                thumb_pos = int((self.scroll_top / scroll_range) * (viewport_height - thumb_size))
            else:
                thumb_pos = 0
            thumb_range = range(thumb_pos, thumb_pos + thumb_size)

        for r_idx, (row_type, content, p_idx) in enumerate(visible_rows):
            # Carattere scrollbar: block per il thumb, linea sottile per la traccia
            sb_char = "█" if (thumb_range and r_idx in thumb_range) else "│"
            
            if row_type == 'header':
                # Riga titolo con scrollbar integrata (rimpiazza l'ultimo carattere)
                titolo_base = f"├─ {content} "
                # 58 caratteri di linea + 1 scrollbar = 59. 
                riempimento = "─" * (58 - len(titolo_base))
                print(f"{CIANO}{titolo_base}{riempimento}{RESET}{sb_char}")
            else:
                self._draw_param_row(content, p_idx, sb_char)

        # 4. Riempimento per mantenere il footer fisso in basso (allungamento barra)
        # Se il contenuto è minore del limite sicuro, aggiungiamo righe vuote
        rows_to_fill = safe_limit - viewport_height
        for _ in range(rows_to_fill):
            print(f"| {' ' * 57} {sb_char if total_rows > viewport_height else '│'}")

        # Footer (ancorato in fondo al safe_limit)
        footer = " ↑/↓: naviga | ←/→: modifica | Invio: salva/stringa | Esc: esci "
        print(f"\033[47m\033[30m{footer.center(60)}\033[0m")
        
        if self.modified:
            print(f"{GIALLO} Modifiche non salvate.{RESET}{' ' * 30}")
        else:
            print(f"{' ' * 56}")

    def _draw_param_row(self, param, i, sb_char="│"):
        """Disegna una singola riga di parametro."""
        if param.type == 'command':
            disp = "▶ Esegui"
        else:
            value = self.get_value(param)
            if value is None:
                disp = "N/A"
            else:
                if param.type == 'bool':
                    disp = "[X]" if value else "[ ]"
                elif param.type == 'float':
                    disp = f"{value:.2f}"
                else:
                    disp = str(value)
        
        prefisso = " > " if self.cursor == i else "   "
        testo_base = f"{prefisso}{param.label}: {disp}"
        
        if len(testo_base) > 56:
            testo_base = testo_base[:53] + "..."
        else:
            testo_base = f"{testo_base:<56}"
        
        if self.cursor == i:
            testo_render = f"{VERDE}{testo_base}{RESET}"
        else:
            testo_render = testo_base
        
        # Stampa la riga rimpiazzando l'ultimo bordo con la scrollbar
        print(f"| {testo_render} {sb_char}")

    def _confirm(self, message):
        print(f"\n{GIALLO}{message}{RESET}")
        while True:
            ch = self._wait_for_key()
            if ch in (ord('s'), ord('S')):
                return True
            if ch in (ord('n'), ord('N'), KEY_ESC):
                return False