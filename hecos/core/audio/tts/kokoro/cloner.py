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
    def enroll_from_wav(source_wav: str, output_pt_path: str = None, lang_prefix: str = "af", prosody_mode: str = "auto") -> torch.Tensor:
        """
        Reads a WAV reference audio track and extracts the Kokoro style tensor pack.
        Optionally saves it directly to output_pt_path.
        Returns the torch.Tensor pack of shape [510, 1, 256].
        
        prosody_mode:
          - "auto": automatic pitch/syllable match via inno_kokoro, but if lang is Italian (im/if),
                    anchors the predictor to native Italian (im_nicola / if_sara) for authentic cadence.
          - "native": force native language prosody (e.g. im_nicola / if_sara for IT).
          - "inno_blend": standard inno_kokoro convex blend across English stock voices.
        """
        if not os.path.isfile(source_wav):
            raise FileNotFoundError(f"Source WAV not found: {source_wav}")

        tuner = get_tuner()
        from inno_kokoro.enroll import enroll, read

        logger.info("KOKORO_CLONER", f"Reading source WAV: {source_wav}")
        audio, sr = read(source_wav)

        logger.info("KOKORO_CLONER", f"Enrolling speaker embedding (sr={sr}, samples={len(audio)})...")
        pack, weights = enroll(audio, sr, tuner)

        if not isinstance(pack, torch.Tensor) or pack.ndim != 3:
            raise ValueError(f"Extracted pack invalid tensor format: {type(pack)}, shape: {getattr(pack, 'shape', None)}")

        # Check if native prosody anchor should be applied
        use_native = (prosody_mode == "native") or (prosody_mode == "auto" and lang_prefix.startswith("i"))
        if use_native:
            from huggingface_hub import hf_hub_download
            is_male = lang_prefix.endswith("m") or ("m" in lang_prefix and not lang_prefix.endswith("f"))
            anchor_voice = "im_nicola" if is_male else "if_sara"

            try:
                logger.info("KOKORO_CLONER", f"Aligning predictor prosody with native anchor '{anchor_voice}'...")
                stock_path = hf_hub_download("hexgrad/Kokoro-82M", f"voices/{anchor_voice}.pt")
                stock_pack = torch.load(stock_path, weights_only=True)
                # Keep extracted timbre (first 128 dims), apply native Italian prosody (last 128 dims)
                pack = torch.cat([pack[:, :, :128], stock_pack[:, :, 128:]], dim=-1)
                logger.info("KOKORO_CLONER", f"Applied native prosody anchor '{anchor_voice}' to custom voice pack.")
            except Exception as pe:
                logger.warning("KOKORO_CLONER", f"Could not anchor native prosody: {pe}")

        if output_pt_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_pt_path)), exist_ok=True)
            torch.save(pack, output_pt_path)
            logger.info("KOKORO_CLONER", f"Saved Kokoro style pack ({pack.shape}) to {output_pt_path}")

        return pack
