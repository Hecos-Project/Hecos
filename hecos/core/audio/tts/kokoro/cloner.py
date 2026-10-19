"""
hecos/core/audio/tts/kokoro/cloner.py
Zero-shot voice cloning and style embedding extraction ([510, 1, 256]) for Kokoro TTS.
"""

import os
import threading
import torch
from hecos.core.logging import logger

_TUNER_LOCK = threading.Lock()
_TUNER_INSTANCE = None


def get_tuner():
    """Returns a lazily-initialized singleton instance of inno_kokoro Tuner."""
    global _TUNER_INSTANCE
    if _TUNER_INSTANCE is None:
        with _TUNER_LOCK:
            if _TUNER_INSTANCE is None:
                try:
                    logger.info("KOKORO_CLONER", "Initializing Kokoro clone Tuner encoder...")
                    from inno_kokoro.enroll import Tuner
                    _TUNER_INSTANCE = Tuner()
                    logger.info("KOKORO_CLONER", "Kokoro clone Tuner encoder ready.")
                except Exception as e:
                    logger.error("KOKORO_CLONER", f"Failed to initialize inno_kokoro Tuner: {e}")
                    raise
    return _TUNER_INSTANCE


class KokoroCloner:
    """Extracts style pack embeddings ([510, 1, 256]) from audio tracks for Kokoro TTS."""

    @staticmethod
    def is_available() -> bool:
        try:
            import inno_kokoro  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def enroll_from_wav(source_wav: str, output_pt_path: str = None) -> torch.Tensor:
        """
        Reads a WAV reference audio track and extracts the Kokoro style tensor pack.
        Optionally saves it directly to output_pt_path.
        Returns the torch.Tensor pack of shape [510, 1, 256].
        """
        if not os.path.isfile(source_wav):
            raise FileNotFoundError(f"Source WAV not found: {source_wav}")

        tuner = get_tuner()
        from inno_kokoro.enroll import enroll, read

        logger.info("KOKORO_CLONER", f"Reading source WAV: {source_wav}")
        audio, sr = read(source_wav)

        logger.info("KOKORO_CLONER", f"Enrolling speaker embedding (sr={sr}, samples={len(audio)})...")
        pack, _ = enroll(audio, sr, tuner)

        if not isinstance(pack, torch.Tensor) or pack.ndim != 3:
            raise ValueError(f"Extracted pack invalid tensor format: {type(pack)}, shape: {getattr(pack, 'shape', None)}")

        if output_pt_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_pt_path)), exist_ok=True)
            torch.save(pack, output_pt_path)
            logger.info("KOKORO_CLONER", f"Saved Kokoro style pack ({pack.shape}) to {output_pt_path}")

        return pack
