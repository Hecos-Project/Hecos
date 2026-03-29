"""
MODULE: zentra_bridge/webui/audio.py
DESCRIPTION: Local TTS (Piper) management for the WebUI bridge.
             Runs in a background daemon thread — never blocks the HTTP stream.
"""

import os
import subprocess
import threading
import logging

bridge_logger = logging.getLogger("WebUI_Bridge")


def speak_local(testo: str, voice_cfg: dict, bridge_dir: str) -> None:
    """
    Synthesises `testo` with Piper and plays the resulting WAV file.
    Spawns a daemon thread so the caller is never blocked.

    Args:
        testo:      The text to synthesise.
        voice_cfg:   The ``voice`` section of config.json.
        bridge_dir: Absolute path to the Zentra-Core root (used for WAV output).
    """
    if not testo or not testo.strip():
        return

    def _run() -> None:
        try:
            piper_path   = voice_cfg.get("piper_path",   r"C:\piper\piper.exe")
            model_path   = voice_cfg.get("onnx_model", r"C:\piper\it_IT-paola-medium.onnx")
            speed        = voice_cfg.get("speed",               1.2)
            length_scale = round(1.0 / max(0.1, speed), 3)
            noise_scale  = voice_cfg.get("noise_scale",       0.817)
            noise_w      = voice_cfg.get("noise_w",            0.9)
            silence      = voice_cfg.get("sentence_silence",   0.1)

            testo_pulito = testo.strip().replace('"', "").replace("\n", " ")
            wav_path     = os.path.join(bridge_dir, "risposta_bridge.wav")

            cmd = [
                piper_path, "-m", model_path,
                "--length_scale",    str(length_scale),
                "--noise_scale",     str(noise_scale),
                "--noise_w",         str(noise_w),
                "--sentence_silence", str(silence),
                "-f", wav_path,
            ]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            proc.communicate(input=testo_pulito)

            if os.path.exists(wav_path):
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                bridge_logger.info(f"[TTS] Spoken locally: {len(testo_pulito)} chars")

        except Exception as exc:
            bridge_logger.error(f"[TTS] Local voice error: {exc}")

    threading.Thread(target=_run, daemon=True).start()
