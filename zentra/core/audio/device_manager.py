"""
MODULE: Audio Device Manager - Zentra Core
DESCRIPTION: Facade module for audio device configuration.
             Logic has been heavily simplified to delegate to the OS.
"""

from .audio_config import (
    _load_audio_config, 
    _save_audio_config, 
    _migrate_from_main_config,
    get_audio_config
)
from .device_scanner import (
    list_devices, 
    scan_and_select, 
    maybe_scan_on_startup
)
from .beep_generator import (
    _make_beep_array, 
    _play_beep_on_device, 
    SOUNDDEVICE_AVAILABLE
)
