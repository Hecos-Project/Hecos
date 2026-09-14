"""
hecos/ui/terminal_input.py
Handles readline-style input buffer rendering and keyboard event catching.
"""
import sys
import os
import json
import msvcrt
import logging

from colorama import Fore, Style

_cli_history = []
_cli_history_idx = -1
_cli_history_draft = ""
_cli_history_loaded = False

# Readline-style prompt state
_prompt_active = False
_active_prompt_prefix = ""
_active_input_buffer = ""
_current_prompt_len = 0


def set_active_prompt(prefix: str, buf: str = ""):
    """Called by the main loop to register the current prompt state for safe log printing."""
    global _prompt_active, _active_prompt_prefix, _active_input_buffer
    _prompt_active = True
    _active_prompt_prefix = prefix
    _active_input_buffer = buf


def print_scrolling(text):
    """Readline-style safe print: erases the prompt, prints the message, then redraws the prompt."""
    from hecos.ui.ui_updater import stdout_lock
    global _prompt_active, _active_prompt_prefix, _active_input_buffer
    with stdout_lock:
        if _prompt_active:
            # 2K clears entire line, \r moves to the beginning
            sys.stdout.write("\033[2K\r")
            # Print the new message on its own line
            sys.stdout.write(text + "\n")
            # Reprint the prompt + whatever the user has typed so far
            sys.stdout.write(_active_prompt_prefix + _active_input_buffer)
            sys.stdout.flush()
        else:
            print(text)


def write_hecos(text):
    """Prints Hecos's response safely without clobbering the prompt."""
    from hecos.core.processing import filtri
    text = filtri.clean_for_video(text)
    prefix = f"{Fore.CYAN}HECOS:{Style.RESET_ALL} "
    print_scrolling(prefix + text)
    print_scrolling("")  # Add an empty line for visual spacing before the prompt


def read_keyboard_input(prefix, current_input):
    """
    Reads a single char from stdin (non-blocking) and handles F-keys/arrows.
    Returns: (ActionType, NewInputBuffer)
    """
    global _current_prompt_len, _active_input_buffer, _active_prompt_prefix
    # Keep prompt state in sync for readline-style redraw
    _active_prompt_prefix = prefix
    _active_input_buffer = current_input
    _current_prompt_len = len(prefix) + len(current_input)
    
    if msvcrt.kbhit():
        ch_raw = msvcrt.getch()
        # Function keys F1-F6 and Arrows
        if ch_raw in [b'\x00', b'\xe0']:
            special_key = msvcrt.getch()
            # F1-F9 keys
            if special_key == b';': return "F1", current_input
            if special_key == b'<': return "F2", current_input
            if special_key == b'=': return "F3", current_input
            if special_key == b'>': return "F4", current_input
            if special_key == b'?': return "F5", current_input
            if special_key == b'@': return "F6", current_input
            if special_key == b'A': return "F7", current_input
            if special_key == b'B': return "F8", current_input
            if special_key == b'C': return "F9", current_input
            
            # Up / Down Arrows for Input History
            if special_key in [b'H', b'P']: # 0x48 (Up), 0x50 (Down)
                global _cli_history, _cli_history_idx, _cli_history_draft, _cli_history_loaded
                _ih_log = logging.getLogger("hecos.input_history")
                
                if not _cli_history_loaded:
                    _cli_history_loaded = True
                    try:
                        _cfg_mgr = getattr(sys, "hecos_config_manager", None)
                        if _cfg_mgr:
                            _ih_cfg = _cfg_mgr.config.get("input_history", {})
                            if _ih_cfg.get("enabled", True) and _ih_cfg.get("persist", True):
                                _hist_path = os.path.join(_cfg_mgr.data_dir, "cli_history.json")
                                if os.path.exists(_hist_path):
                                    with open(_hist_path, "r", encoding="utf-8") as _f:
                                        _cli_history = json.load(_f)
                                    _ih_log.info(f"[InputHistory:CLI] Loaded {len(_cli_history)} entries from disk.")
                                else:
                                    _ih_log.info("[InputHistory:CLI] No persisted history found on disk.")
                        else:
                            _ih_log.info("[InputHistory:CLI] hecos_config_manager not available yet, using RAM only.")
                    except Exception as _e:
                        _ih_log.warning(f"[InputHistory:CLI] Failed to load from disk: {_e}")

                if not _cli_history:
                    _ih_log.info("[InputHistory:CLI] ArrowUp pressed but history is empty.")
                    _msg = " [No input history yet — start typing and press Enter]"
                    sys.stdout.write('\r' + ' ' * (len(current_input) + len(prefix) + 5) + '\r')
                    sys.stdout.write(f"\033[90m{_msg}\033[0m")
                    sys.stdout.flush()
                    import time; time.sleep(1.2)
                    sys.stdout.write('\r' + ' ' * len(_msg) + '\r')
                    sys.stdout.write(prefix + current_input)
                    sys.stdout.flush()
                    return None, current_input
                
                if _cli_history_idx == -1:
                    _cli_history_draft = current_input
                    _cli_history_idx = len(_cli_history)

                if special_key == b'H': # Up
                    if _cli_history_idx > 0: _cli_history_idx -= 1
                else: # Down
                    if _cli_history_idx < len(_cli_history): _cli_history_idx += 1

                if _cli_history_idx >= len(_cli_history):
                    new_input = _cli_history_draft
                    _cli_history_idx = -1
                else:
                    new_input = _cli_history[_cli_history_idx]

                if new_input != current_input:
                    sys.stdout.write('\b' * len(current_input) + ' ' * len(current_input) + '\b' * len(current_input))
                    current_input = new_input
                    _active_input_buffer = current_input
                    sys.stdout.write(current_input)
                    sys.stdout.flush()
                    _ih_log.debug(f"[InputHistory:CLI] Navigated to: {current_input!r}")
                return None, current_input

            return None, current_input

        if ch_raw == b'\x1b':  # ESC
            if current_input:
                _active_input_buffer = ""
                return "CLEAR", ""
            else:
                return "ESC", current_input

        try:
            ch = ch_raw.decode('utf-8')
        except Exception:
            return None, current_input

        if ch == '\r': return "ENTER", current_input
        elif ch == '\b':
            if len(current_input) > 0:
                current_input = current_input[:-1]
                _active_input_buffer = current_input
                sys.stdout.write('\b \b')
                sys.stdout.flush()
            return "CHAR", current_input
        else:
            current_input += ch
            _active_input_buffer = current_input
            sys.stdout.write(ch)
            sys.stdout.flush()
            return "CHAR", current_input

    return None, current_input


def push_cli_history(text):
    """Pushes a new input command into the CLI history buffer."""
    global _cli_history, _cli_history_idx, _cli_history_loaded
    _log = logging.getLogger("hecos.input_history")
    # Mark as loaded so ArrowUp doesn't overwrite in-memory history with stale disk data
    _cli_history_loaded = True
    try:
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        cfg = cfg_mgr.config.get("input_history", {}) if cfg_mgr else {}
        
        if not cfg.get("enabled", True):
            _log.debug("[InputHistory:CLI] push_cli_history: disabled, skipping.")
            return
        
        deduplicate = cfg.get("deduplicate", True)
        if deduplicate and _cli_history and _cli_history[-1] == text:
            _log.debug("[InputHistory:CLI] push_cli_history: deduplicate match, skipping.")
            _cli_history_idx = -1
            return
        
        _cli_history.append(text)
        max_entries = cfg.get("max_entries", 5)
        if len(_cli_history) > max_entries:
            _cli_history = _cli_history[-max_entries:]
        _cli_history_idx = -1
        _log.info(f"[InputHistory:CLI] Saved: {text!r} | Total: {len(_cli_history)}")
        
        if cfg.get("persist", True) and cfg_mgr:
            try:
                hist_path = os.path.join(cfg_mgr.data_dir, "cli_history.json")
                with open(hist_path, "w", encoding="utf-8") as f:
                    json.dump(_cli_history, f)
                _log.debug(f"[InputHistory:CLI] Persisted to {hist_path}")
            except Exception as _pe:
                _log.warning(f"[InputHistory:CLI] Persist error: {_pe}")
    except Exception as _e:
        _log.warning(f"[InputHistory:CLI] push_cli_history error: {_e}")
