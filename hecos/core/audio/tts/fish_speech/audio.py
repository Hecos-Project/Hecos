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
    def normalize_pcm16_data(data_int16, target_rms_db: float = -14.0, volume_factor: float = 1.0):
        """
        Normalizes and optimizes 16-bit PCM audio loudness to match broadcast / Piper levels (~ -14 to -16 dBFS RMS).
        Uses speech-active RMS detection (ignoring pauses) and smooth soft-knee tanh compression
        for the highest peaks to avoid harsh digital clipping.
        """
        if data_int16 is None or len(data_int16) == 0:
            return data_int16

        import numpy as np

        data = data_int16.astype(np.float32)
        if data.ndim == 2:
            non_silent = data[np.max(np.abs(data), axis=1) > 300]
        else:
            non_silent = data[np.abs(data) > 300]

        if len(non_silent) == 0:
            return data_int16

        current_rms = float(np.sqrt(np.mean(non_silent**2)))
        effective_target_db = target_rms_db
        if volume_factor > 0 and volume_factor != 1.0:
            import math
            effective_target_db += 20.0 * math.log10(volume_factor)

        target_rms = 32767.0 * (10.0 ** (effective_target_db / 20.0))
        gain = target_rms / max(current_rms, 1.0)
        gain = float(np.clip(gain, 0.5, 12.0))

        amplified = data * gain
        thresh = 22000.0
        limit = 32000.0
        headroom = limit - thresh

        signs = np.sign(amplified)
        abs_amp = np.abs(amplified)
        mask = abs_amp > thresh
        compressed = abs_amp.copy()
        if np.any(mask):
            excess = abs_amp[mask] - thresh
            compressed[mask] = thresh + headroom * np.tanh(excess / headroom)

        return np.clip(signs * compressed, -32767, 32767).astype(np.int16)

    @staticmethod
    def normalize_wav_bytes(wav_bytes: bytes, target_rms_db: float = -14.0, volume_factor: float = 1.0) -> bytes:
        """
        Takes raw WAV bytes, performs speech loudness normalization, and returns normalized WAV bytes.
        """
        if not wav_bytes or len(wav_bytes) < 44:
            return wav_bytes
        try:
            import io
            import wave
            import numpy as np

            in_buf = io.BytesIO(wav_bytes)
            with wave.open(in_buf, 'rb') as w:
                params = w.getparams()
                nframes = w.getnframes()
                sampwidth = w.getsampwidth()
                nchannels = w.getnchannels()
                frames = w.readframes(nframes)

            if sampwidth != 2 or not frames:
                return wav_bytes

            data_int16 = np.frombuffer(frames, dtype=np.int16)
            if nchannels > 1:
                data_int16 = data_int16.reshape(-1, nchannels)

            norm_int16 = FishSpeechAudio.normalize_pcm16_data(data_int16, target_rms_db=target_rms_db, volume_factor=volume_factor)

            out_buf = io.BytesIO()
            with wave.open(out_buf, 'wb') as out_w:
                out_w.setparams(params)
                out_w.writeframes(norm_int16.tobytes())

            return out_buf.getvalue()
        except Exception as e:
            logger.debug("FISH_SPEECH", f"normalize_wav_bytes notice: {e}")
            return wav_bytes

    @staticmethod
    def normalize_wav_file(filepath: str, target_rms_db: float = -14.0, volume_factor: float = 1.0) -> bool:
        """
        Normalizes a WAV file on disk in-place.
        """
        if not filepath or not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "rb") as f:
                raw_bytes = f.read()
            norm_bytes = FishSpeechAudio.normalize_wav_bytes(raw_bytes, target_rms_db=target_rms_db, volume_factor=volume_factor)
            if norm_bytes and len(norm_bytes) >= 44:
                with open(filepath, "wb") as f:
                    f.write(norm_bytes)
                return True
            return False
        except Exception as e:
            logger.warning("FISH_SPEECH", f"normalize_wav_file failed for {filepath}: {e}")
            return False

    @staticmethod
    def merge_wav_files(file_list: list, output_path: str, pause_duration: float = 0.12, volume_factor: float = 1.0):
        """
        Merges multiple WAV files into a single WAV file with a subtle silence pause
        and applies audio volume normalization.
        """
        if not file_list:
            return
        if len(file_list) == 1:
            import shutil
            shutil.copy2(file_list[0], output_path)
            FishSpeechAudio.normalize_wav_file(output_path, volume_factor=volume_factor)
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
                    FishSpeechAudio.normalize_wav_file(output_path, volume_factor=volume_factor)
                    logger.debug("FISH_SPEECH", f"Merged with soundfile at {sample_rate}Hz.")
                    return
            except Exception as sfe:
                logger.warning("FISH_SPEECH", f"soundfile merge failed, trying wave fallback: {sfe}")

        # Fallback using standard library wave module
        import wave
        data = []
        params = None
        for idx, f in enumerate(file_list):
            try:
                with wave.open(f, 'rb') as w:
                    if params is None:
                        params = w.getparams()
                    nframes = w.getnframes()
                    if idx > 0 and params and pause_duration > 0:
                        pause_len = int(params.framerate * pause_duration)
                        silence = b'\x00' * (pause_len * params.sampwidth * params.nchannels)
                        data.append(silence)
                    data.append(w.readframes(nframes))
            except Exception as we:
                logger.warning("FISH_SPEECH", f"Could not read chunk {f} with wave: {we}")

        if params and data:
            with wave.open(output_path, 'wb') as out_w:
                out_w.setparams(params)
                for d in data:
                    out_w.writeframes(d)
            FishSpeechAudio.normalize_wav_file(output_path, volume_factor=volume_factor)
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
