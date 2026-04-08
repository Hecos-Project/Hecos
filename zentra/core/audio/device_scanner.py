"""
MODULE: Device Scanner
DESCRIPTION: Discovers, tests, and auto-selects the best audio input/output device.
"""

import time
from .audio_config import _load_audio_config, _save_audio_config
from .beep_generator import _play_beep_on_device, SOUNDDEVICE_AVAILABLE

try:
    import sounddevice as sd
except ImportError:
    pass

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
