"""
MODULE: Smartwatch PTT Bus (Experimental)
DESCRIPTION: Dedicated module for handling the smartwatch Voice Assistant button signal
             (or similar alternative hardware PTT triggers) separately from the CORE keyboard hotkeys.
             
             HOW IT WORKS: 
             If the smartwatch sends a generic CTRL_L event without shift or alt, this module
             will catch it and fire a 'toggle' action to the primary ptt_bus.
"""

from pynput.keyboard import Key, Listener
import time
import threading
from zentra.core.logging import logger
from zentra.core.audio import ptt_bus
from zentra.core.audio.device_manager import get_audio_config

_listener = None
_enabled = False
_state_ref = None
_pressed_keys = set()
_last_press_time = 0

def _on_press(key):
    global _pressed_keys, _last_press_time
    try:
        from pynput.keyboard import Key
        
        if key in _pressed_keys:
            # Avoid repeat events
            return
        _pressed_keys.add(key)

        key_name = getattr(key, 'name', None) or getattr(key, 'char', None) or str(key)

        # Check configuration
        cfg = get_audio_config()
        sources = cfg.get("ptt_sources", {})
        
        # We handle ONLY watch_button (or future experimental triggers)
        if sources.get("watch_button", False):
            # The smartwatch acts as a hardware trigger. 
            # Note: We use F24 as a non-colliding placeholder. CTRL_L was causing issues.
            is_trigger = key == Key.f24 or key_name == 'f24'
            
            if is_trigger:
                now = time.time()
                # Debounce to avoid double triggers if the device sends multiple signals instantly
                if now - _last_press_time > 0.5:
                    _last_press_time = now
                    logger.info("SMARTWATCH", "Hardware voice button triggered (F24). Toggling PTT...")
                    # Since it pulses (down then instantly up), we use a TOGGLE!
                    ptt_bus.fire_ptt("toggle", "watch_button")
                    
    except Exception as e:
        logger.error(f"[SMARTWATCH-BUS] Error processing key: {e}")

def _on_release(key):
    global _pressed_keys
    if key in _pressed_keys:
        _pressed_keys.remove(key)

def start(state=None):
    """Start the dedicated smartwatch listener engine."""
    global _listener, _enabled, _state_ref
    
    stop()  # Clean up existing before starting
    
    _state_ref = state
    try:
        cfg = get_audio_config()
        if not cfg.get("ptt_sources", {}).get("watch_button", False):
            return # Don't start if not enabled in config
            
        _listener = Listener(on_press=_on_press, on_release=_on_release)
        _listener.daemon = True
        _listener.start()
        _enabled = True
        logger.info("SMARTWATCH", "Standalone PTT driver active.")
    except Exception as e:
        logger.error(f"[SMARTWATCH-BUS] Failed to start listener: {e}")

def stop():
    """Stop the listener entirely."""
    global _listener, _enabled
    if _listener:
        try:
            _listener.stop()
        except Exception:
            pass
        _listener = None
    _enabled = False
