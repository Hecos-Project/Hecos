"""
MODULE: PTT Input Bus - Hecos
DESCRIPTION: Centralized Push-to-Talk signal bus using Pynput for global hooks.
             Decouples PTT detection from the audio processing stack.
             
================================================================================
⚠️ CRITICAL WARNING: CORE SYSTEM LOGIC
   DO NOT MODIFY THE BASE BEHAVIOR OF THIS MODULE (CTRL+SHIFT OR MEDIA KEYS).
   DO NOT ADD SMARTWATCH OR OTHER EXPERIMENTAL HARDWARE LOGIC HERE.
   THIS MODULE MUST REMAIN 100% STABLE FOR STANDARD KEYBOARD OPERATION.
================================================================================
"""

import threading
import time
import os
import logging
import sys
from hecos.core.logging import logger as hecos_logger

# ─────────────────────────────────────────────────────────────────────────────
# DEDICATED LOGGING FOR PTT BUS
# ─────────────────────────────────────────────────────────────────────────────

ptt_log = logging.getLogger("PTT-BUS")
ptt_log.setLevel(logging.DEBUG)

_this_dir = os.path.dirname(os.path.abspath(__file__))
_hecos_dir = os.path.normpath(os.path.join(_this_dir, "..", ".."))
_log_dir = os.path.join(_hecos_dir, "logs")

if not os.path.exists(_log_dir):
    os.makedirs(_log_dir, exist_ok=True)

_log_file = os.path.join(_log_dir, "ptt_bus.log")
# Force encoding to avoid Windows console issues
fh = logging.FileHandler(_log_file, encoding='utf-8', mode='a')
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
ptt_log.addHandler(fh)
ptt_log.propagate = False  # Avoid double-logging to root

def debug_log(msg: str):
    """Log to both Hecos system log and dedicated ptt_bus.log"""
    ptt_log.debug(msg)
    hecos_logger.debug("PTT-BUS", msg)

def info_log(msg: str):
    """Log to both Hecos system log and dedicated ptt_bus.log"""
    ptt_log.info(msg)
    hecos_logger.info("PTT-BUS", msg)

info_log(f"PTT Bus Module loaded (pynput engine initialized). Log: {_log_file}")

# ─────────────────────────────────────────────────────────────────────────────
# SHARED STATE & CACHE
# ─────────────────────────────────────────────────────────────────────────────

ptt_active: bool = False          # Read by listen.py
_state_ref = None                 # Optional StateManager reference
_last_source: str = ""            # For UI feedback / debugging
_listeners: list = []             # Active pynput listeners
_hb_stop_event = None

# Cache for PTT configuration to avoid reloading inside hooks
_ptt_cache = {
    "enabled": False,
    "hotkey": "ctrl+shift",
    "custom_key": "",
    "sources": {"keyboard_hotkey": True, "media_play_pause": False, "custom_key": False}
}

def update_cache():
    """Updates the local cache from the actual device_manager config."""
    global _ptt_cache
    try:
        from hecos.core.audio.device_manager import get_audio_config
        cfg = get_audio_config()
        _ptt_cache["enabled"]    = cfg.get("push_to_talk", False)
        _ptt_cache["hotkey"]     = cfg.get("ptt_hotkey", "ctrl+shift").lower()
        _ptt_cache["custom_key"] = cfg.get("custom_ptt_key", "").lower().strip()
        _ptt_cache["sources"]    = cfg.get("ptt_sources", {"keyboard_hotkey": True})
        debug_log(f"PTT-BUS: Cache updated. Enabled: {_ptt_cache['enabled']}")
    except Exception as e:
        debug_log(f"PTT-BUS: Failed to update cache: {e}")

# Call once immediately to initialize
update_cache()


def _beep_async(freq, duration_ms):
    if sys.platform == "win32":
        try:
            import winsound
            import threading
            threading.Thread(target=winsound.Beep, args=(freq, duration_ms), daemon=True).start()
        except:
            pass

def is_session_0():
    """Detects if we are running in Windows Session 0 (service mode)."""
    if os.name != 'nt': return False
    try:
        import ctypes
        return ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid()) == 0
    except:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# CORE SIGNAL — called by ALL sources
# ─────────────────────────────────────────────────────────────────────────────

def fire_ptt(action: str, source: str = "unknown") -> bool:
    global ptt_active, _last_source
    prev = ptt_active

    if action == "start":
        ptt_active = True
    elif action == "stop":
        ptt_active = False
    elif action == "toggle":
        ptt_active = not ptt_active
    else:
        debug_log(f"Unknown action: {action}")
        return ptt_active

    if ptt_active != prev:
        _last_source = source
        info_log(f"[{source.upper()}] PTT {'ACTIVE ▶' if ptt_active else 'STOPPED ■'}")

        # Local audio and visual feedback (TUI)
        try:
            if ptt_active:
                _beep_async(880, 80)
            else:
                _beep_async(440, 120)
                
            if _state_ref is not None:
                from hecos.ui import interface, ui_updater
                cfg = ui_updater._config_ref.config if getattr(ui_updater, '_config_ref', None) else {}
                
                status_text = "🔴 LISTENING" if ptt_active else "READY"
                _state_ref.system_status = status_text
                
                interface.update_status_bar_in_place(
                    cfg, 
                    getattr(_state_ref, 'voice_status', False), 
                    getattr(_state_ref, 'listening_status', True), 
                    status_text, 
                    ptt_status=getattr(_state_ref, 'push_to_talk', True)
                )
        except Exception as e:
            debug_log(f"Failed local UI feedback: {e}")

        if _state_ref is not None:
            try:
                _state_ref.add_event("ptt_status", {"active": ptt_active, "source": source})
            except Exception as e:
                debug_log(f"Failed to notify StateManager: {e}")

    return ptt_active


# ─────────────────────────────────────────────────────────────────────────────
# PYNPUT GLOBAL LISTENER
# ─────────────────────────────────────────────────────────────────────────────

_pressed_keys = set()

def _on_press(key):
    """Global key press handler."""
    global _pressed_keys, _ptt_cache
    try:
        # 1. Check enabled flag from cache
        if not _ptt_cache["enabled"]:
            return

        from pynput.keyboard import Key

        # IGNORE AUTO-REPEAT: If key is already pressed, don't fire events
        if key in _pressed_keys:
            return

        _pressed_keys.add(key)

        # Extract key identity
        key_name = getattr(key, 'name', None) or getattr(key, 'char', None) or str(key)
        vk = getattr(key, 'vk', None)

        # 2. Use cached settings
        sources    = _ptt_cache["sources"]
        hotkey_str = _ptt_cache["hotkey"]
        custom_key = _ptt_cache["custom_key"]

        # 1. Media Play/Pause (BT headset or other HID media key, VK 179)
        if sources.get("media_play_pause", False):
            if key == Key.media_play_pause or key_name == 'media_play_pause' or vk == 179:
                fire_ptt("toggle", "media_play_pause")

        # 2. Custom Hotkey (Hold behavior)
        if sources.get("custom_key", False) and custom_key:
            if key_name and key_name.lower() == custom_key:
                fire_ptt("start", "custom_key")

        # 3. Standard Hotkey (Ctrl+Shift) - DEFAULT
        if sources.get("keyboard_hotkey", True) and hotkey_str == "ctrl+shift":
            is_ctrl  = any(k in _pressed_keys for k in [Key.ctrl, Key.ctrl_l, Key.ctrl_r])
            is_shift = any(k in _pressed_keys for k in [Key.shift, Key.shift_l, Key.shift_r])
            if is_ctrl and is_shift:
                fire_ptt("start", "keyboard_hotkey")

    except Exception:
        pass

def _on_release(key):
    """Global key release handler."""
    global _pressed_keys, _ptt_cache
    try:
        if not _ptt_cache["enabled"]:
            if key in _pressed_keys: _pressed_keys.remove(key)
            return

        from pynput.keyboard import Key
        if key in _pressed_keys:
            _pressed_keys.remove(key)

        key_name = getattr(key, 'name', None) or getattr(key, 'char', None) or str(key)
        
        sources    = _ptt_cache["sources"]
        hotkey_str = _ptt_cache["hotkey"]
        custom_key = _ptt_cache["custom_key"]

        # 1. Standard Hotkey (Ctrl+Shift) release
        if sources.get("keyboard_hotkey", True) and hotkey_str == "ctrl+shift":
            is_ctrl  = any(k in _pressed_keys for k in [Key.ctrl, Key.ctrl_l, Key.ctrl_r])
            is_shift = any(k in _pressed_keys for k in [Key.shift, Key.shift_l, Key.shift_r])
            if not (is_ctrl and is_shift):
                fire_ptt("stop", "keyboard_hotkey")

        # 2. Custom key release
        if custom_key and key_name and key_name.lower() == custom_key:
            fire_ptt("stop", "custom_key")

    except Exception:
        pass


def _heartbeat_loop(stop_event: threading.Event):
    """Separate loop for heartbeat, log flushing, and hardware key polling watchdog."""
    global ptt_active, _pressed_keys, _ptt_cache
    
    last_hb = time.time()
    while not stop_event.is_set():
        now = time.time()
        
        # 1. Hardware watchdog to prevent "stuck" keys (Windows OS often drops Ctrl+Shift releases)
        if ptt_active and _last_source == "keyboard_hotkey" and _ptt_cache.get("hotkey") == "ctrl+shift" and sys.platform == "win32":
            try:
                import ctypes
                # VK_CONTROL = 0x11, VK_SHIFT = 0x10. Most significant bit is set if pressed.
                ctrl_down = (ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000) != 0
                shift_down = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0
                
                if not (ctrl_down and shift_down):
                    # Hardware disagrees with pynput (key was released but event dropped)
                    debug_log("PTT-BUS WATCHDOG: Keys physically released, overriding pynput state.")
                    
                    # Force clear the pressed keys array of the modifiers
                    from pynput.keyboard import Key
                    for k in [Key.ctrl, Key.ctrl_l, Key.ctrl_r, Key.shift, Key.shift_l, Key.shift_r]:
                        if k in _pressed_keys:
                            _pressed_keys.remove(k)
                            
                    fire_ptt("stop", "keyboard_hotkey")
            except Exception as e:
                pass
        
        # 2. Status heartbeat
        if now - last_hb > 300:  # 5 minutes
            debug_log("[HEARTBEAT] PTT Bus Listener active (pynput engine).")
            for h in ptt_log.handlers:
                h.flush()
            last_hb = now
            
        # Poll faster if PTT is active to make the watchdog responsive (100ms)
        time.sleep(0.1 if ptt_active else 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# BUS LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

def start(state=None):
    global _state_ref, _listeners, _hb_stop_event
    _state_ref = state

    # Stop any existing
    stop()
    time.sleep(0.1)

    try:
        update_cache() # Sync cache before starting
        
        if is_session_0():
            info_log("Skipping pynput listener (Windows Session 0 detected). Relying on Tray/WebUI PTT triggers.")
        else:
            from pynput import keyboard
            # Start the global keyboard listener
            l = keyboard.Listener(on_press=_on_press, on_release=_on_release)
            l.daemon = True
            l.start()
            _listeners.append(l)
            debug_log("Pynput Global Keyboard Listener started.")

        # Start Heartbeat thread
        _hb_stop_event = threading.Event()
        hb_thread = threading.Thread(target=_heartbeat_loop, args=(_hb_stop_event,), daemon=True, name="ptt-heartbeat")
        hb_thread.start()

    except Exception as e:
        info_log(f"Failed to start PTT Bus listeners: {e}")


def stop():
    global _listeners, _hb_stop_event
    
    # Stop pynput listeners
    for l in _listeners:
        try:
            l.stop()
        except Exception:
            pass
    _listeners = []

    # Stop heartbeat
    if _hb_stop_event:
        _hb_stop_event.set()
        _hb_stop_event = None

    info_log("PTT Bus stopped.")


def reload(state=None):
    stop()
    update_cache()
    start(state)
    info_log("PTT Bus reloaded.")


def get_status() -> dict:
    return {
        "ptt_active": ptt_active,
        "last_source": _last_source,
        "active_listeners": [l.__class__.__name__ for l in _listeners],
        "log_file": _log_file,
        "engine": "pynput"
    }

def is_ptt_active() -> bool:
    return ptt_active

def get_last_source() -> str:
    return _last_source
