"""
MODULE: Fish Speech TTS - Audio Utilities
DESCRIPTION: Handles multi-chunk WAV concatenation with natural pause padding
             and local audio device playback with stop interruption support.
"""

import os
import time
from typing import Callable, Optional
from hecos.core.logging import logger

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


class FishSpeechAudio:
    """Audio utility methods for merging WAV chunks and playing audio."""

    @staticmethod
    def merge_wav_files(file_list: list, output_path: str, pause_duration: float = 0.12):
        """
        Merges multiple WAV files into a single WAV file with a subtle silence pause.
        """
        if not file_list:
            return
        if len(file_list) == 1:
            import shutil
            shutil.copy2(file_list[0], output_path)
            return

        if SOUNDFILE_AVAILABLE:
            try:
                import numpy as np
                combined_data = []
                sample_rate = None
                for idx, f in enumerate(file_list):
                    try:
                        data, sr = sf.read(f)
                        if sample_rate is None:
                            sample_rate = sr
                        if idx > 0 and sample_rate:
                            pause_len = int(sample_rate * pause_duration)
                            if data.ndim == 1:
                                silence = np.zeros(pause_len, dtype=data.dtype)
                            else:
                                silence = np.zeros((pause_len, data.shape[1]), dtype=data.dtype)
                            combined_data.append(silence)
                        combined_data.append(data)
                    except Exception as e:
                        logger.warning("FISH_SPEECH", f"Could not read chunk {f} for merge: {e}")

                if combined_data and sample_rate:
                    merged = np.concatenate(combined_data, axis=0)
                    sf.write(output_path, merged, sample_rate)
                    logger.debug("FISH_SPEECH", f"Merged with soundfile at {sample_rate}Hz.")
                    return
            except Exception as sfe:
                logger.warning("FISH_SPEECH", f"soundfile merge failed, trying wave fallback: {sfe}")

        # Fallback using standard library wave module
        import wave
        data = []
        params = None
        for f in file_list:
            try:
                with wave.open(f, 'rb') as w:
                    if params is None:
                        params = w.getparams()
                    data.append(w.readframes(w.getnframes()))
            except Exception:
                pass

        if params and data:
            with wave.open(output_path, 'wb') as out_w:
                out_w.setparams(params)
                for d in data:
                    out_w.writeframes(d)
            logger.debug("FISH_SPEECH", "Merged with standard library wave module.")

    @staticmethod
    def play_wav(filepath: str, is_stopped_fn: Optional[Callable[[], bool]] = None):
        """
        Plays a WAV file on the local audio device, checking is_stopped_fn to abort immediately.
        """
        if not filepath or not os.path.exists(filepath):
            return

        if SOUNDDEVICE_AVAILABLE and SOUNDFILE_AVAILABLE:
            try:
                data, fs = sf.read(filepath)
                sd.play(data, fs)
                while sd.get_stream() and sd.get_stream().active:
                    if is_stopped_fn and is_stopped_fn():
                        logger.info("FISH_SPEECH", "Playback interrupted by stop flag.")
                        sd.stop()
                        break
                    time.sleep(0.05)
                logger.info("FISH_SPEECH", "Playback finished via sounddevice.")
                return
            except Exception as sde:
                logger.warning("FISH_SPEECH", f"sounddevice playback failed: {sde}, falling back to winsound.")

        try:
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME)
            logger.info("FISH_SPEECH", "Playback finished via winsound.")
        except Exception as ws_err:
            logger.error("FISH_SPEECH", f"winsound playback error: {ws_err}")

    @staticmethod
    def stop_playback():
        if SOUNDDEVICE_AVAILABLE:
            try:
                sd.stop()
            except Exception:
                pass
