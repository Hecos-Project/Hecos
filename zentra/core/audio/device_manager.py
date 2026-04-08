"""
MODULE: Audio Device Manager - Zentra Core
DESCRIPTION: Facade module for audio device configuration and discovery.
             Logic has been split into:
             - audio_config.py
             - beep_generator.py
             - device_scanner.py
"""

from .audio_config import (
    _load_audio_config, 
    _save_audio_config, 
    _migrate_from_main_config,
    get_output_device, 
    get_input_device, 
    get_audio_config,
    set_output_device, 
    set_input_device
)
from .device_scanner import (
    list_devices, 
    test_output_device, 
    test_input_device,
    _score_device_name, 
    scan_and_select, 
    maybe_scan_on_startup
)
from .beep_generator import (
    _make_beep_array, 
    _play_beep_on_device, 
    SOUNDDEVICE_AVAILABLE
)
