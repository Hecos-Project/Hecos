"""
PACKAGE: zentra.core.audio
DESCRIPTION: Audio subsystem package.
             Submodules:
               - voice.py         → TTS (Piper + sounddevice)
               - listen.py        → STT (speech_recognition)
               - ptt_bus.py       → PTT signal bus (all input sources)
               - device_manager.py → Audio device config facade

IMPORT PATTERNS (used by external consumers):
    from zentra.core.audio import listen    → use as listen.listen()
    from zentra.core.audio import voice    → use as voice.speak()
    from zentra.core.audio import ptt_bus  → use as ptt_bus.fire_ptt()
    from zentra.core.audio.voice import speak  → direct function import

NOTE: This __init__.py is intentionally minimal. Do NOT add function
      re-exports here — it would shadow the submodule names
      (e.g. making `listen` a function instead of the listen module).
"""