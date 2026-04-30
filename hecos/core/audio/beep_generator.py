"""
MODULE: Beep Generator
DESCRIPTION: Generates and plays short confirmation beeps on audio devices.
"""

import math

# --- Constants ---
BEEP_FREQ = 440       # Hz  (A4)
BEEP_DURATION = 0.18  # seconds
SAMPLE_RATE = 44100

try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

def _make_beep_array(freq: float = BEEP_FREQ, duration: float = BEEP_DURATION,
                      sample_rate: int = SAMPLE_RATE):
    """Generates a simple sine wave beep as a numpy array."""
    if not SOUNDDEVICE_AVAILABLE:
        return None
        
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
