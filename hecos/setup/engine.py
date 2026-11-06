"""
Hecos Setup - Core Engine Facade
Re-exports environment setup, Piper TTS, and Neural TTS installers for 100% backward compatibility.
"""

from .setup_env import (
    check_python_version,
    check_dependencies,
    install_dependencies,
    enable_autostart,
    start_tray,
    auto_fix_piper_path,
    set_system_language,
    unattended_onboarding,
)

from .setup_piper import (
    VOICES_CACHE,
    fetch_piper_voices,
    download_voice,
    download_piper_engine,
)

from .setup_neural_tts import (
    _run_pip_install,
    _install_espeak_ng,
    _patch_espeak_path,
    download_kokoro_engine,
    _patch_python_headers,
    _install_msvc_build_tools,
    download_xtts_engine,
    check_fish_speech_engine,
    download_fish_speech_engine,
)

__all__ = [
    # Environment & dependencies
    "check_python_version",
    "check_dependencies",
    "install_dependencies",
    "enable_autostart",
    "start_tray",
    "auto_fix_piper_path",
    "set_system_language",
    "unattended_onboarding",
    # Piper TTS
    "VOICES_CACHE",
    "fetch_piper_voices",
    "download_voice",
    "download_piper_engine",
    # Neural TTS
    "_run_pip_install",
    "_install_espeak_ng",
    "_patch_espeak_path",
    "download_kokoro_engine",
    "_patch_python_headers",
    "_install_msvc_build_tools",
    "download_xtts_engine",
    "check_fish_speech_engine",
    "download_fish_speech_engine",
]
