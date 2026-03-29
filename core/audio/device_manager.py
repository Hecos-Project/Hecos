"""
MODULE: Audio Device Manager - Zentra Core
DESCRIPTION: Discovers, tests, and selects the best audio input/output device.
             Plays a short beep on the winning output device to confirm selection.
             Saves results to config_audio.json (separate from main config.json).
"""

import os
import json
import math
import struct
import time
from datetime import datetime

# --- Constants ---
CONFIG_AUDIO_PATH = "config_audio.json"
BEEP_FREQ = 440       # Hz  (A4)
BEEP_DURATION = 0.18  # seconds
SAMPLE_RATE = 44100

# --- Lazy imports (avoid hard crash if sounddevice not installed) ---
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# CONFIG I/O
# ──────────────────────────────────────────────────────────────────────────────

def _load_audio_config() -> dict:
    """Loads config_audio.json, returns defaults if missing."""
    defaults = {
        "output_device_index": -1,
        "output_device_name": "",
        "input_device_index": -1,
        "input_device_name": "",
        "auto_select": True,
        "test_on_startup": True,
        "fallback_on_error": True,
        "beep_on_select": True,
        "last_scan": "",
        
        # --- Voice Settings ---
        "voice_status": True,
        "piper_path": "C:\\piper\\piper.exe",
        "onnx_model": "C:\\piper\\it_IT-aurora-medium.onnx",
        "speed": 1.2,
        "noise_scale": 0.817,
        "noise_w": 0.9,
        "sentence_silence": 0.1,
        
        # --- Listening Settings ---
        "listening_status": True,
        "energy_threshold": 450,
        "silence_timeout": 5,
        "phrase_limit": 15,
        "push_to_talk": False,
        "ptt_hotkey": "ctrl+shift",
        "stt_source": "system",    # 'system' (PC mic) or 'web' (browser input)
        "tts_destination": "web"   # 'system' (PC speakers) or 'web' (browser audio)
    }
    try:
        if os.path.exists(CONFIG_AUDIO_PATH):
            with open(CONFIG_AUDIO_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
    except Exception:
        pass
    return defaults


def _save_audio_config(cfg: dict) -> bool:
    """Saves config_audio.json."""
    try:
        if "last_scan" not in cfg or cfg.get("last_scan") == "":
             cfg["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_AUDIO_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[AUDIO-DM] Save error: {e}")
        return False


def _migrate_from_main_config():
    """Migrates 'voice' and 'listening' dicts from config.json to config_audio.json, then deletes them."""
    main_cfg_path = "config.json"
    if not os.path.exists(main_cfg_path): return
    
    try:
        with open(main_cfg_path, "r", encoding="utf-8") as f:
            main_data = json.load(f)
            
        has_voice = "voice" in main_data
        has_listening = "listening" in main_data
        
        if not has_voice and not has_listening:
            return # Nothing to migrate
            
        audio_cfg = _load_audio_config()
        
        if has_voice:
            voice_data = main_data.pop("voice")
            if isinstance(voice_data, dict):
                for k, v in voice_data.items():
                    audio_cfg[k] = v
                    
        if has_listening:
            listening_data = main_data.pop("listening")
            if isinstance(listening_data, dict):
                for k, v in listening_data.items():
                    audio_cfg[k] = v
                    
        # Save both
        _save_audio_config(audio_cfg)
        
        with open(main_cfg_path, "w", encoding="utf-8") as f:
            json.dump(main_data, f, indent=4, ensure_ascii=False)
            
        print("[AUDIO-DM] Successfully migrated voice/listening settings to config_audio.json")
    except Exception as e:
        print(f"[AUDIO-DM] Migration error: {e}")

# Run migration early on import if needed
_migrate_from_main_config()


# ──────────────────────────────────────────────────────────────────────────────
# DEVICE LISTING
# ──────────────────────────────────────────────────────────────────────────────

def list_devices() -> dict:
    """
    Returns a dict with 'output' and 'input' lists of available devices.
    Each entry: {'index': int, 'name': str, 'channels': int, 'sample_rate': float}
    """
    result = {"output": [], "input": []}

    if not SOUNDDEVICE_AVAILABLE:
        print("[AUDIO-DM] sounddevice not available. Cannot list devices.")
        return result

    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            entry = {
                "index": i,
                "name": dev["name"],
                "channels": 0,
                "sample_rate": dev["default_samplerate"]
            }
            if dev["max_output_channels"] > 0:
                entry["channels"] = dev["max_output_channels"]
                result["output"].append(dict(entry))
            if dev["max_input_channels"] > 0:
                entry["channels"] = dev["max_input_channels"]
                result["input"].append(dict(entry))
    except Exception as e:
        print(f"[AUDIO-DM] Device listing error: {e}")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# BEEP GENERATION
# ──────────────────────────────────────────────────────────────────────────────

def _make_beep_array(freq: float = BEEP_FREQ, duration: float = BEEP_DURATION,
                      sample_rate: int = SAMPLE_RATE) -> "np.ndarray":
    """Generates a simple sine wave beep as a numpy array."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Apply a short fade-in/fade-out (10ms) to avoid clicks
    fade_samples = int(sample_rate * 0.01)
    wave = 0.4 * np.sin(2 * math.pi * freq * t).astype(np.float32)
    if len(wave) > fade_samples * 2:
        wave[:fade_samples] *= np.linspace(0, 1, fade_samples)
        wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    return wave


def _play_beep_on_device(device_index: int, sample_rate: int = SAMPLE_RATE) -> bool:
    """
    Plays a short beep on the specified output device.
    Returns True if successful, False on any error.
    """
    if not SOUNDDEVICE_AVAILABLE:
        return False
    try:
        wave = _make_beep_array(sample_rate=sample_rate)
        sd.play(wave, samplerate=sample_rate, device=device_index, blocking=True)
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# TESTING
# ──────────────────────────────────────────────────────────────────────────────

def test_output_device(device_index: int) -> bool:
    """
    Tests an output device by attempting to open a stream.
    Does NOT play audio — just checks the device is accessible.
    Returns True if the device opens successfully.
    """
    if not SOUNDDEVICE_AVAILABLE:
        return False
    try:
        dev_info = sd.query_devices(device_index, kind="output")
        sr = int(dev_info["default_samplerate"])
        # Try opening a minimal stream and immediately close it
        stream = sd.OutputStream(device=device_index, samplerate=sr, channels=1)
        stream.start()
        time.sleep(0.02)
        stream.stop()
        stream.close()
        return True
    except Exception:
        return False


def test_input_device(device_index: int) -> bool:
    """
    Tests an input device by opening a short stream.
    Returns True if the device opens successfully.
    """
    if not SOUNDDEVICE_AVAILABLE:
        return False
    try:
        dev_info = sd.query_devices(device_index, kind="input")
        sr = int(dev_info["default_samplerate"])
        stream = sd.InputStream(device=device_index, samplerate=sr, channels=1)
        stream.start()
        time.sleep(0.02)
        stream.stop()
        stream.close()
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# AUTO-SELECTION LOGIC
# ──────────────────────────────────────────────────────────────────────────────

def _score_device_name(name: str) -> int:
    """
    Heuristic scoring: prefer dedicated speakers/headphones over virtual/loopback devices.
    Higher score = better candidate.
    """
    name_lower = name.lower()
    score = 0

    # Penalize virtual / loopback / monitor devices
    bad_keywords = ["loopback", "virtual", "mix", "what u hear", "stereo mix",
                    "monitor", "null", "dummy", "vb-cable", "blackhole"]
    for kw in bad_keywords:
        if kw in name_lower:
            score -= 20

    # Prefer real hardware
    good_keywords = ["speaker", "headphone", "headset", "realtek", "hdmi",
                     "usb audio", "analog", "output", "line out"]
    for kw in good_keywords:
        if kw in name_lower:
            score += 10

    return score


def scan_and_select(verbose: bool = True) -> dict:
    """
    Main entry point.
    1. Lists all available output and input devices.
    2. Tests each one (stream open check).
    3. Picks the best output → plays a confirmation beep.
    4. Picks the best input.
    5. Saves and returns the updated audio config.
    """
    cfg = _load_audio_config()

    if not SOUNDDEVICE_AVAILABLE:
        print("[AUDIO-DM] ⚠ sounddevice not installed. Run: pip install sounddevice")
        return cfg

    if verbose:
        print("[AUDIO-DM] 🔍 Scanning audio devices...")

    devices = list_devices()

    # ── SELECT OUTPUT ──────────────────────────────────────────────────────────
    best_output_idx = -1
    best_output_name = ""
    best_output_score = -9999

    for dev in devices["output"]:
        if verbose:
            print(f"[AUDIO-DM]   Testing output [{dev['index']}] {dev['name']} ... ", end="", flush=True)

        ok = test_output_device(dev["index"])

        if verbose:
            print("✓ OK" if ok else "✗ FAIL")

        if ok:
            score = _score_device_name(dev["name"])
            if score > best_output_score:
                best_output_score = score
                best_output_idx = dev["index"]
                best_output_name = dev["name"]
                best_output_sr = int(dev["sample_rate"])

    # ── BEEP ON WINNER ─────────────────────────────────────────────────────────
    if best_output_idx >= 0 and cfg.get("beep_on_select", True):
        if verbose:
            print(f"[AUDIO-DM] 🔊 Selected output: [{best_output_idx}] {best_output_name}")
            print("[AUDIO-DM] 🎵 Playing confirmation beep...")
        _play_beep_on_device(best_output_idx, sample_rate=best_output_sr)
    elif best_output_idx < 0:
        if verbose:
            print("[AUDIO-DM] ⚠ No working output device found.")

    # ── SELECT INPUT ───────────────────────────────────────────────────────────
    best_input_idx = -1
    best_input_name = ""
    best_input_score = -9999

    for dev in devices["input"]:
        if verbose:
            print(f"[AUDIO-DM]   Testing input  [{dev['index']}] {dev['name']} ... ", end="", flush=True)

        ok = test_input_device(dev["index"])

        if verbose:
            print("✓ OK" if ok else "✗ FAIL")

        if ok:
            score = _score_device_name(dev["name"])
            if score > best_input_score:
                best_input_score = score
                best_input_idx = dev["index"]
                best_input_name = dev["name"]

    if best_input_idx >= 0 and verbose:
        print(f"[AUDIO-DM] 🎤 Selected input:  [{best_input_idx}] {best_input_name}")
    elif best_input_idx < 0 and verbose:
        print("[AUDIO-DM] ⚠ No working input device found.")

    # ── SAVE ───────────────────────────────────────────────────────────────────
    cfg["output_device_index"] = best_output_idx
    cfg["output_device_name"]  = best_output_name
    cfg["input_device_index"]  = best_input_idx
    cfg["input_device_name"]   = best_input_name
    _save_audio_config(cfg)

    if verbose:
        print("[AUDIO-DM] ✅ Audio config saved to config_audio.json")

    return cfg


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC GETTERS (used by voice.py and listen.py)
# ──────────────────────────────────────────────────────────────────────────────

def get_output_device() -> int:
    """
    Returns the configured output device index.
    Returns -1 if not configured or config missing (sounddevice will use system default).
    """
    cfg = _load_audio_config()
    return cfg.get("output_device_index", -1)


def get_input_device() -> int:
    """
    Returns the configured input device index.
    Returns None if not configured (speech_recognition will use system default).
    """
    cfg = _load_audio_config()
    idx = cfg.get("input_device_index", -1)
    return idx if idx >= 0 else None


def get_audio_config() -> dict:
    """Returns the full audio configuration dict."""
    return _load_audio_config()


def set_output_device(index: int, name: str = "") -> bool:
    """Manually sets the output device and saves."""
    cfg = _load_audio_config()
    cfg["output_device_index"] = index
    cfg["output_device_name"]  = name
    cfg["auto_select"]         = False
    return _save_audio_config(cfg)


def set_input_device(index: int, name: str = "") -> bool:
    """Manually sets the input device and saves."""
    cfg = _load_audio_config()
    cfg["input_device_index"] = index
    cfg["input_device_name"]  = name
    cfg["auto_select"]         = False
    return _save_audio_config(cfg)


# ──────────────────────────────────────────────────────────────────────────────
# STARTUP HOOK
# ──────────────────────────────────────────────────────────────────────────────

def maybe_scan_on_startup(force: bool = False) -> dict:
    """
    Called at Zentra startup.
    Optimized: only scans if no device is selected.
    If devices are already selected, it skips the slow scan to speed up boot.
    """
    cfg = _load_audio_config()
    
    # If we have valid indices, we skip the scan unless forced
    has_config = cfg.get("output_device_index", -1) >= 0 and cfg.get("input_device_index", -1) >= 0
    
    if force or not has_config:
        return scan_and_select(verbose=True)
        
    return cfg
