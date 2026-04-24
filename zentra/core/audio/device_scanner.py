"""
MODULE: Device Scanner Stub
DESCRIPTION: Audio device scanning logic has been removed. We now delegate entirely to the OS.
"""

from .audio_config import _load_audio_config

def list_devices() -> dict:
    return {"output": [], "input": []}

def test_output_device(device_index: int) -> bool:
    return True

def test_input_device(device_index: int) -> bool:
    return True

def scan_and_select(verbose: bool = False) -> dict:
    return _load_audio_config()

def maybe_scan_on_startup(force: bool = False) -> dict:
    return _load_audio_config()
