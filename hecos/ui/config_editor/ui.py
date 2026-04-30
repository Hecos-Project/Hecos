"""
Gestione dell'interfaccia utente: disegno e interazione.
"""

from .utils import clear_screen, get_key, flush_input
from hecos.ui import graphics
from hecos.core.i18n import translator
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
    def __init__(self, param_list, getter, setter, command_handler=None):
        self.get_value = getter
        self.set_value = setter
        self.command_handler = command_handler
        
        # Define visual order priority
        self.order_standard = [
            translator.t("section_models"), 
            translator.t("section_ia"),
            translator.t("section_llm"), 
            "🌐 OpenAI", "🌐 Anthropic", "🌐 Groq", "🌐 Gemini", 
            translator.t("section_generation"), 
            translator.t("section_voice"), 
            translator.t("section_listening"), 
            translator.t("section_filters"), 
            translator.t("section_logging"), 
            translator.t("section_cognition"),
            translator.t("section_system"),
        ]
        
        # Helper to get priority index
        def get_priority(p):
            title = self._get_section_title(p)
            try:
                return self.order_standard.index(title)
            except ValueError:
                if title.startswith("🔌"): return 200 # Plugins last
                return 100 # Other
                
        # Sort param_list to MATCH the visual order
        self.param_list = sorted(param_list, key=get_priority)
        
        self.cursor = 0
        self.scroll_top = 0
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
                        print(f"\n\n{GIALLO}You have unsaved changes. [S] = Save and Exit | [N] = Discard Changes | [ESC] = Cancel{RESET}")
                        while True:
                            c = self._wait_for_key()
                            if c in (ord('s'), ord('S'), ord('y'), ord('Y'), KEY_ENTER):
                                return "SAVE"
                            elif c in (ord('n'), ord('N')):
                                return "DISCARD"
                            elif c == KEY_ESC:
                                break # Ritorna all'editor continuo
                    else:
                        return "NO_CHANGES"
                elif key == KEY_ENTER:
                    # Comportamento ENTER: Se è stringa libera, edita. Se bool, togga. Se comando, esegue.
                    param = self.param_list[self.cursor]
                    if param.readonly:
                        pass  # ignora per sola lettura
                    elif param.type == 'str' and not param.options:
                        self._edit_string(param)
                    elif param.type == 'bool':
                        current = self.get_value(param)
                        self.set_value(param, not current)
                        self.modified = True
                    elif param.type == 'command':
                        if param.command == 'save_exit':
                            return "SAVE"
                        elif param.command == 'reboot':
                            return "REBOOT"
                        elif param.command == 'clear_instructions':
                            dummy_param = type('T', (), {'section': 'ai', 'key': 'special_instructions'})()
                            self.set_value(dummy_param, "")
                            self.modified = True
                            print(f"\n{VERDE}{translator.t('instruction_cleared')}{RESET}")
                            import time
                            time.sleep(0.8)
                        elif self.command_handler and self.command_handler(param.command):
                            # Custom command handled externally (e.g. rescan_audio_devices)
                            self.first_draw = True  # Force full redraw after command
                            self.param_list = self.param_list  # handler may rebuild it
                elif key == KEY_UP:
                    if self.cursor > 0:
                        self.cursor -= 1
                elif key == KEY_DOWN:
                    if self.cursor < len(self.param_list) - 1:
                        self.cursor += 1
                elif key == KEY_LEFT or key == KEY_RIGHT:
                    param = self.param_list[self.cursor]
                    if param.readonly:
                        pass  # sola lettura, nessuna azione
                    elif param.type == 'command':
                        if param.command == 'reboot':
                            return "REBOOT"
                        elif param.command == 'save_exit':
                            return "SAVE"
                        elif param.command == 'clear_instructions':
                            # Rimuove sia dal config temporaneo che salvato
                            dummy_param = type('T', (), {'section': 'ai', 'key': 'special_instructions'})()
                            self.set_value(dummy_param, "")
                            self.modified = True
                            print(f"\n{VERDE}{translator.t('instruction_cleared')}{RESET}")
                            import time
                            time.sleep(0.8)
                        elif self.command_handler and self.command_handler(param.command):
                            self.first_draw = True
                    else:
                        current = self.get_value(param)
                        if param.type in ('int', 'float'):
                            if param.type == 'int':
                                step = param.step or 1
                            else:
                                step = param.step or 0.1
                            if key == KEY_LEFT:
                                new_val = current - step
                            else:
                                new_val = current + step
                            if param.min is not None:
                                new_val = max(param.min, new_val)
                            if param.max is not None:
                                new_val = min(param.max, new_val)
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
                    if not param.readonly and param.type == 'bool':
                        current = self.get_value(param)
                        self.set_value(param, not current)
                        self.modified = True
        finally:
            # Ripristina il cursore 
            sys.stdout.write('\033[?25h')
            sys.stdout.flush()
        
        return "SAVE" if self.modified else "NO_CHANGES"

    def _edit_string(self, param):
        """Modifica una stringa libera con input utente, supportando ESC per annullare."""
        current = self.get_value(param) or ""
        print(f"\n{GIALLO}{translator.t('edit_string_title', label=param.label)}{RESET}")
        print(f"{translator.t('current_value', value=current)}")
        print(translator.t('enter_new_value'))
        
        # Mostra cursore per la digitazione
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
        
        flush_input()
        chars = []
        import msvcrt
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b'\x1b': # ESC
                    print(f"\n{GIALLO}{translator.t('edit_cancelled')}{RESET}")
                    sys.stdout.write('\033[?25l')
                    sys.stdout.flush()
                    import time
                    time.sleep(1)
                    return
                elif ch == b'\r': # ENTER
                    break
                elif ch == b'\x08': # BACKSPACE
                    if chars:
                        chars.pop()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                else:
                    try:
                        c = ch.decode('utf-8')
                        chars.append(c)
                        sys.stdout.write(c)
                        sys.stdout.flush()
                    except:
                        pass
        
        new_val = "".join(chars).strip()
        self.set_value(param, new_val)
        self.modified = True
        print(f"\n{VERDE}{translator.t('value_updated')}{RESET}")
        
        # Nasconde cursore e attende
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()
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
            return translator.t("section_system")
        elif param.section == 'ai':
            return translator.t("section_ia")
        elif param.section == 'llm':
            return translator.t("section_llm")
        elif param.section == 'llm_openai':
            return "🌐 OpenAI"
        elif param.section == 'llm_anthropic':
            return "🌐 Anthropic"
        elif param.section == 'llm_groq':
            return "🌐 Groq"
        elif param.section == 'llm_gemini':
            return "🌐 Gemini"
        elif param.section == 'logging':
            return translator.t("section_logging")
        elif param.section == 'filters':
            return translator.t("section_filters")
        elif param.section == 'listening':
            return translator.t("section_listening")
        elif param.section == 'voice':
            return translator.t("section_voice")
        elif param.section == 'backend':
            # Distingue modello dagli altri parametri di backend
            if param.key == 'model' or param.key == '_f2_hint':
                return translator.t("section_models")
            else:
                return translator.t("section_generation")
        elif param.section in ('ollama', 'kobold'):
            return translator.t("section_generation")
        elif param.section == 'plugin':
            return f"🔌 {param.plugin_tag}"
        else:
            return "OTHER"

    def _draw(self):
        # Riposizioniamo il cursore invece di pulire tutto (evita flickering)
        if self.first_draw:
            clear_screen(first_time=True)
            self.first_draw = False
        else:
            sys.stdout.write('\033[H')
            
        output_buffer = []
        def outprint(text):
            output_buffer.append(text + "\n")
            
        from hecos.core.system.version import get_version_string
        
        try:
            term_size = shutil.get_terminal_size()
            PANEL_WIDTH = min(110, max(60, term_size.columns - 4))
            term_height = term_size.lines
            safe_limit = max(10, term_height - 4)
        except:
            PANEL_WIDTH = 80
            safe_limit = 30
            
        # Header
        intestazione = f" {get_version_string()} - CONTROL PANEL "
        outprint(f"\033[44m\033[97m{intestazione.center(PANEL_WIDTH)}\033[0m")
        
        # 1. Generate flat list of renderable rows based on the ALREADY SORTED list
        all_rows = [] 
        current_header = None
        
        for i, param in enumerate(self.param_list):
            title = self._get_section_title(param)
            if title != current_header:
                all_rows.append(('header', title, None))
                current_header = title
            all_rows.append(('param', param, i))

        # 2. Gestione scorrimento (Viewport)
        viewport_height = min(len(all_rows), safe_limit)
        
        cursor_row_idx = 0
        for idx, row in enumerate(all_rows):
            if row[0] == 'param' and row[2] == self.cursor:
                cursor_row_idx = idx
                break

        # Aggiusta scroll_top
        if cursor_row_idx < self.scroll_top:
            self.scroll_top = cursor_row_idx
        elif cursor_row_idx >= self.scroll_top + viewport_height:
            self.scroll_top = cursor_row_idx - viewport_height + 1

        # 3. Disegna il viewport con Scrollbar
        visible_rows = all_rows[self.scroll_top : self.scroll_top + viewport_height]
        
        total_rows = len(all_rows)
        thumb_range = None
        if total_rows > viewport_height:
            thumb_size = max(1, int((viewport_height / total_rows) * viewport_height))
            scroll_range = total_rows - viewport_height
            if scroll_range > 0:
                thumb_pos = int((self.scroll_top / scroll_range) * (viewport_height - thumb_size))
            else:
                thumb_pos = 0
            thumb_range = range(thumb_pos, thumb_pos + thumb_size)

        for r_idx, (row_type, content, p_idx) in enumerate(visible_rows):
            sb_char = "█" if (thumb_range and r_idx in thumb_range) else "│"
            
            if row_type == 'header':
                titolo_base = f"├─ {content} "
                riempimento = "─" * (PANEL_WIDTH - 2 - len(titolo_base))
                outprint(f"{CIANO}{titolo_base}{riempimento}{RESET}{sb_char}")
            else:
                outprint(self._draw_param_row(content, p_idx, sb_char, PANEL_WIDTH))

        # 4. Riempimento per mantenere footer fisso
        rows_to_fill = safe_limit - viewport_height
        for _ in range(rows_to_fill):
            spazi = " " * (PANEL_WIDTH - 3)
            ultimo_char = sb_char if total_rows > viewport_height else "│"
            outprint(f"| {spazi} {ultimo_char}")

        # Footer
        footer = f" {translator.t('menu_nav_help')} "
        outprint(f"\033[47m\033[30m{footer.center(PANEL_WIDTH)}\033[0m")
        
        if self.modified:
            outprint(f"{GIALLO} {translator.t('config_unsaved_changes')}{RESET}\033[K")
        else:
            outprint("\033[K")
            
        sys.stdout.write("".join(output_buffer))
        sys.stdout.flush()

    def _draw_param_row(self, param, i, sb_char, panel_width):
        """Disegna una singola riga di parametro."""
        # --- Tipo 'info': riga informativa statica (non modificabile) ---
        if param.type == 'info':
            disp = param.info_value or ""
            prefisso = " ℹ " if self.cursor == i else "   "
            testo_base = f"{prefisso}{param.label}: {disp}"
            max_testo = panel_width - 4
            if len(testo_base) > max_testo:
                testo_base = testo_base[:max_testo-3] + "..."
            else:
                testo_base = f"{testo_base:<{max_testo}}"
            # Render: ciano scuro (dim + ciano) per distinguerlo visivamente
            testo_render = f"\033[2m{CIANO}{testo_base}{RESET}"
            return f"| {testo_render} {sb_char}"
        
        # --- Tipo standard ---
        if param.type == 'command':
            disp = "▶ Execute"
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
                    # Supporto traduzione per valori noti (es. option_both)
                    if isinstance(value, str):
                        key_traduzione = f"option_{value.lower().replace(' ', '_')}"
                        tradotto = translator.t(key_traduzione)
                        if tradotto != key_traduzione:
                            disp = tradotto
            
            # Per plugin modello_llm vuoto: mostra quale modello verrà usato
            if param.key == "modello_llm" and not value and param.global_default_model:
                disp = f"(global: {param.global_default_model})"
        
        if param.readonly:
            prefisso = " \U0001f512 " if self.cursor == i else "   "
        else:
            prefisso = " > " if self.cursor == i else "   "
        testo_base = f"{prefisso}{param.label}: {disp}"
        
        max_testo = panel_width - 4
        if len(testo_base) > max_testo:
            testo_base = testo_base[:max_testo-3] + "..."
        else:
            testo_base = f"{testo_base:<{max_testo}}"
        
        if self.cursor == i:
            if param.readonly:
                testo_render = f"\033[2m{testo_base}{RESET}"  # dim: sola lettura
            else:
                testo_render = f"{VERDE}{testo_base}{RESET}"
        else:
            testo_render = testo_base
        
        return f"| {testo_render} {sb_char}"

    def _confirm(self, message):
        print(f"\n{GIALLO}{message}{RESET}")
        while True:
            ch = self._wait_for_key()
            if ch in (ord('s'), ord('S'), ord('y'), ord('Y')):
                return True
            if ch in (ord('n'), ord('N'), KEY_ESC):
                return False