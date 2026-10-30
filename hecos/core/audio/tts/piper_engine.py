"""
MODULE: Piper TTS Daemon (JSON IPC Edition)
DESCRIPTION: Runs a permanent `piper.exe --json-input` subprocess in the background.
             Accepts JSON requests via stdin. Avoids loading the Heavy ONNX model
             for every sentence. Guaranteed zero-latency synthesis with zero external
             pip dependencies (no piper-tts python module needed).
"""
import os
import sys
import json
import time
import queue
import subprocess
import threading
import wave
import uuid

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


def _get_project_root():
    current_file = os.path.abspath(__file__)
    return os.path.normpath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))))


def _get_sample_rate(model_path: str) -> int:
    json_path = model_path + ".json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("audio", {}).get("sample_rate", 22050)
    except Exception:
        return 22050


class PiperEngine(BaseTTSEngine):
    def __init__(self):
        self._proc = None
        self._sample_rate = 22050
        self._lock = threading.Lock()
        
        self._is_speaking = False
        self._stop_flag = False
        
        # Events and syncing
        self._synth_complete_event = threading.Event()
        self._ready_event = threading.Event()   # Fired when model finishes loading
        self._stderr_thread = None

        # Audio Config
        self._length_scale = 1.0
        self._noise_scale = 0.667
        self._noise_w = 0.8
        self._sentence_silence = 0.2
        self._daemon_model = None
        self._daemon_length_scale = None
        self._daemon_noise_scale = None
        self._daemon_noise_w = None
        self._daemon_sentence_silence = None

    def preload(self, delay: float = 3.0):
        threading.Thread(target=self._start_daemon_delayed, args=(delay,), daemon=True).start()

    def _start_daemon_delayed(self, delay):
        time.sleep(delay)
        self._ensure_running()

    def _ensure_running(self):
        with self._lock:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                audio_cfg = get_audio_config()
                root = _get_project_root()
                
                default_piper = os.path.join(root, "bin", "piper", "piper.exe")
                default_model = os.path.join(root, "bin", "piper", "it_IT-paola-medium.onnx")
                piper_path = audio_cfg.get("piper_path", default_piper)
                model_path = audio_cfg.get("onnx_model", default_model)
                
                if not os.path.isfile(piper_path): piper_path = default_piper
                if not os.path.isfile(model_path): model_path = default_model
                
                if not os.path.isfile(piper_path):
                    logger.warning("PIPER_DAEMON", f"Piper executable not found at {piper_path}. TTS daemon will not start.")
                    self._proc = None
                    return
                    
                from hecos.core.ext_deps import require
                if not require("vc_redist"):
                    logger.warning("PIPER_DAEMON", "VC Redist missing. Piper TTS daemon will not start.")
                    self._proc = None
                    return
                    
                self._sample_rate = _get_sample_rate(model_path)
                speed = float(audio_cfg.get("speed", 1.0) if audio_cfg.get("speed") is not None else 1.0)
                self._length_scale = round(1.0 / speed, 3) if speed > 0 else 1.0
                self._noise_scale = round(float(audio_cfg.get("noise_scale", 0.667) if audio_cfg.get("noise_scale") is not None else 0.667), 3)
                self._noise_w = round(float(audio_cfg.get("noise_w", 0.8) if audio_cfg.get("noise_w") is not None else 0.8), 3)
                self._sentence_silence = round(float(audio_cfg.get("sentence_silence", 0.2) if audio_cfg.get("sentence_silence") is not None else 0.2), 3)

                if self._proc is not None and self._proc.poll() is None:
                    if (self._daemon_model == model_path and
                        self._daemon_length_scale == self._length_scale and
                        self._daemon_noise_scale == self._noise_scale and
                        self._daemon_noise_w == self._noise_w and
                        self._daemon_sentence_silence == self._sentence_silence):
                        return
                    logger.info("PIPER_DAEMON", "Piper settings changed — recycling IPC daemon...")
                    try:
                        self._proc.terminate()
                        self._proc.wait(timeout=2.0)
                    except Exception:
                        try: self._proc.kill()
                        except Exception: pass
                    self._proc = None

                logger.info("PIPER_DAEMON", f"Booting background JSON IPC Daemon (model={os.path.basename(model_path)}, len_scale={self._length_scale})...")

                cmd = [
                    piper_path, "-m", model_path,
                    "--length_scale", str(self._length_scale),
                    "--noise_scale", str(self._noise_scale),
                    "--noise_w", str(self._noise_w),
                    "--sentence_silence", str(self._sentence_silence),
                    "--json-input", "--debug"
                ]
                
                kwargs = {
                    "stdin": subprocess.PIPE, 
                    "stderr": subprocess.PIPE, 
                    "stdout": subprocess.DEVNULL,
                    "cwd": os.path.dirname(piper_path)
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000  # NO_WINDOW
                    
                self._ready_event.clear()
                self._proc = subprocess.Popen(cmd, **kwargs)

                self._daemon_model = model_path
                self._daemon_length_scale = self._length_scale
                self._daemon_noise_scale = self._noise_scale
                self._daemon_noise_w = self._noise_w
                self._daemon_sentence_silence = self._sentence_silence

                if self._stderr_thread is None or not self._stderr_thread.is_alive():
                    self._stderr_thread = threading.Thread(target=self._read_stderr_loop, daemon=True)
                    self._stderr_thread.start()

                logger.info("PIPER_DAEMON", "Eternal JSON Daemon booted — waiting for model load...")

            except Exception as e:
                logger.error("PIPER_DAEMON", f"Failed to start JSON daemon: {e}")
                self._proc = None

    def _read_stderr_loop(self):
        """Monitors Piper stderr. Sets ready/synth events at the right moments."""
        while self._proc and self._proc.poll() is None:
            try:
                line = self._proc.stderr.readline()
                if not line:
                    break
                txt = line.decode('utf-8', errors='ignore')
                if "Initialized piper" in txt:
                    self._ready_event.set()
                    logger.info("PIPER_DAEMON", "Eternal JSON Daemon ready.")
                elif "Real-time factor" in txt:
                    # One synthesis workload completed
                    self._synth_complete_event.set()
            except Exception:
                break

    @staticmethod
    def _resolve_piper_params(session_overrides=None):
        """Resolves binary path, model path, length_scale, noise and sentence silence."""
        from hecos.core.audio.device_manager import get_audio_config
        audio_cfg = get_audio_config()
        root = _get_project_root()
        overrides = session_overrides or {}

        default_piper = os.path.join(root, "bin", "piper", "piper.exe")
        default_model = os.path.join(root, "bin", "piper", "it_IT-paola-medium.onnx")

        piper_path = overrides.get("piper_path") or audio_cfg.get("piper_path", default_piper)
        if not os.path.isfile(piper_path):
            piper_path = default_piper

        model_candidate = (
            overrides.get("onnx_model")
            or overrides.get("piper_model")
            or overrides.get("tts_voice")
            or audio_cfg.get("onnx_model", default_model)
        )
        if not model_candidate or not os.path.isfile(str(model_candidate)):
            basename = os.path.basename(str(model_candidate))
            if basename and os.path.isfile(os.path.join(root, "bin", "piper", basename)):
                model_candidate = os.path.join(root, "bin", "piper", basename)
            else:
                model_candidate = default_model
        model_path = model_candidate

        def _get_num(*keys, default=0.0):
            for k in keys:
                if k in overrides and overrides[k] is not None:
                    try:
                        return float(overrides[k])
                    except (ValueError, TypeError):
                        pass
                if k in audio_cfg and audio_cfg[k] is not None:
                    try:
                        return float(audio_cfg[k])
                    except (ValueError, TypeError):
                        pass
            return default

        speed = _get_num("speed", "piper_speed", default=1.0)
        if speed <= 0:
            speed = 1.0
        length_scale = round(1.0 / speed, 3)

        noise_scale = round(_get_num("noise_scale", "noise", "piper_noise", default=0.667), 3)
        noise_w = round(_get_num("noise_w", "noisew", "piper_noisew", default=0.8), 3)
        sentence_silence = round(_get_num("sentence_silence", "silence", "piper_silence", default=0.2), 3)
        volume = round(_get_num("volume", "piper_volume", default=1.0), 2)

        timeout = _get_num("piper_timeout", default=180.0)

        return {
            "piper_path": piper_path,
            "model_path": model_path,
            "speed": speed,
            "length_scale": length_scale,
            "noise_scale": noise_scale,
            "noise_w": noise_w,
            "sentence_silence": sentence_silence,
            "volume": volume,
            "timeout": timeout,
        }

    @staticmethod
    def _adjust_volume(filepath: str, volume: float) -> bool:
        """Scales WAV volume with soft-knee limiting to prevent digital clipping."""
        if not filepath or not os.path.isfile(filepath):
            return False
        if abs(volume - 1.0) < 0.01:
            return True
        try:
            import wave
            import numpy as np
            with wave.open(filepath, "rb") as w:
                params = w.getparams()
                frames = w.readframes(params.nframes)
            if params.sampwidth == 2:
                data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                amplified = data * volume
                if volume > 1.0:
                    thresh = 24000.0
                    limit = 32000.0
                    headroom = limit - thresh
                    signs = np.sign(amplified)
                    abs_amp = np.abs(amplified)
                    mask = abs_amp > thresh
                    res = np.where(mask, thresh + headroom * np.tanh((abs_amp - thresh) / headroom), abs_amp)
                    clamped = np.clip(signs * res, -32767, 32767).astype(np.int16)
                else:
                    clamped = np.clip(amplified, -32767, 32767).astype(np.int16)

                with wave.open(filepath, "wb") as w:
                    w.setparams(params)
                    w.writeframes(clamped.tobytes())
                return True
            return False
        except Exception as e:
            logger.warning("PIPER_DAEMON", f"Volume adjustment error for {filepath}: {e}")
            return False

    def generate_wav(self, text: str, filepath: str, session_overrides=None, **kwargs) -> bool:
        """
        Synthesizes audio directly to a WAV file via Piper CLI with full support
        for runtime parameters (speed, noise_scale, noise_w, sentence_silence, onnx_model).
        """
        if not text:
            return False

        clean = text.replace('"', "").replace('\n', " ").strip()
        if not clean:
            return False

        overrides = session_overrides or kwargs.get("session_overrides") or {}
        params = self._resolve_piper_params(overrides)

        piper_bin = params["piper_path"]
        model_file = params["model_path"]

        if not os.path.isfile(piper_bin) or not os.path.isfile(model_file):
            logger.error("PIPER_DAEMON", f"Missing piper binary ({piper_bin}) or model ({model_file})")
            return False

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        cmd = [
            piper_bin,
            "-m", model_file,
            "-f", filepath,
            "--length_scale", str(params["length_scale"]),
            "--noise_scale", str(params["noise_scale"]),
            "--noise_w", str(params["noise_w"]),
            "--sentence_silence", str(params["sentence_silence"]),
        ]

        logger.info("PIPER_DAEMON", f"CLI synth: model={os.path.basename(model_file)}, len_scale={params['length_scale']}, noise={params['noise_scale']}, noisew={params['noise_w']}, silence={params['sentence_silence']}")

        kwargs_proc = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.PIPE,
            "cwd": os.path.dirname(piper_bin),
        }
        if sys.platform == "win32":
            kwargs_proc["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        try:
            proc = subprocess.Popen(cmd, **kwargs_proc)
            _, err = proc.communicate(input=clean.encode("utf-8"), timeout=params["timeout"])
            if proc.returncode != 0:
                err_msg = err.decode("utf-8", errors="ignore") if err else "Unknown error"
                logger.error("PIPER_DAEMON", f"Piper CLI synthesis failed (RC={proc.returncode}): {err_msg}")
                root = _get_project_root()
                fallback_m = os.path.join(root, "bin", "piper", "it_IT-paola-medium.onnx")
                if model_file != fallback_m and os.path.isfile(fallback_m):
                    logger.warning("PIPER_DAEMON", f"Retrying with fallback model: {fallback_m}")
                    cmd[2] = fallback_m
                    proc = subprocess.Popen(cmd, **kwargs_proc)
                    _, err = proc.communicate(input=clean.encode("utf-8"), timeout=params["timeout"])
            success = os.path.isfile(filepath) and os.path.getsize(filepath) > 44
            if success and params.get("volume") and abs(params["volume"] - 1.0) >= 0.01:
                self._adjust_volume(filepath, params["volume"])
            return success
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error("PIPER_DAEMON", f"Piper CLI synthesis timed out after {params['timeout']}s")
            return False
        except Exception as exc:
            logger.error("PIPER_DAEMON", f"Piper CLI synthesis error: {exc}")
            return False

    def generate_wav_chunked(self, text: str, filepath: str, progress_callback=None, on_chunk_ready=None, session_overrides=None, **kwargs) -> bool:
        """
        Generates WAV audio respecting speed and acoustic overrides, reporting progress and chunk events.
        """
        if not text:
            return False

        overrides = session_overrides or kwargs.get("session_overrides") or {}

        if progress_callback:
            try:
                progress_callback(0, 1)
            except Exception:
                pass

        success = self.generate_wav(text, filepath, session_overrides=overrides, **kwargs)

        if success:
            if progress_callback:
                try:
                    progress_callback(1, 1)
                except Exception:
                    pass
            if on_chunk_ready and os.path.exists(filepath):
                try:
                    with open(filepath, "rb") as _f:
                        _cb = _f.read()
                    on_chunk_ready(0, 1, filepath, _cb)
                except Exception:
                    pass
        return success

    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0, session_overrides=None, **kwargs):
        """
        Main PC TTS. Splits text into phrases, generates temp wav files
        virtually instantly via the IPC daemon, and streams playback natively.
        """
        if not text: return
        self._ensure_running()
        if self._proc is None or self._proc.poll() is not None:
            return

        clean = text.replace('"', "").replace("\n", " ").strip()
        if not clean: return

        import re
        raw = re.split(r'(?<=[.!?…])\s+|(?<=[—\-]{2})\s*', clean)
        sentences = [r.strip() for r in raw if r.strip()]

        self._is_speaking = True
        self._stop_flag = False
        if state: state.system_speaking = True

        def _should_stop():
            if self._stop_flag: return True
            if _run_id:
                try:
                    from hecos.modules.flows.engine import is_run_aborted
                    if is_run_aborted(_run_id): return True
                except: pass
            if _timeout and _timeout > 0 and (time.time() - _start) > _timeout:
                return True
            return False

        # Block until model is ready (up to 30s for slow hardware)
        if not self._ready_event.wait(timeout=30.0):
            logger.error("PIPER_DAEMON", "Piper not ready within 30s — aborting speak()")
            self._is_speaking = False
            if state: state.system_speaking = False
            return

        root = _get_project_root()
        temp_dir = os.path.join(root, "hecos", "media", "audio", "temp_tts")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            for s in sentences:
                if _should_stop(): break
                
                # Generate unique temp file
                uid = uuid.uuid4().hex[:8]
                tmp_wav = os.path.join(temp_dir, f"chunk_{uid}.wav")
                
                req = {"text": s, "output_file": tmp_wav}
                
                self._synth_complete_event.clear()
                with self._lock:
                    if self._proc and self._proc.poll() is None:
                        try:
                            self._proc.stdin.write((json.dumps(req) + "\n").encode('utf-8'))
                            self._proc.stdin.flush()
                        except: break

                # Wait for inference (extremely fast because model is already in RAM)
                # Note: changed from 5.0s to 30.0s because long sentences on slow GPUs/CPUs
                # can easily take more than 5s, leading to EOFError (file empty/incomplete).
                waited = self._synth_complete_event.wait(30.0)

                if _should_stop(): break
                
                if not waited:
                    logger.error("PIPER_DAEMON", "Timeout waiting for TTS chunk synthesis.")
                    continue
                
                # Play chunk synchronously
                if SOUNDDEVICE_AVAILABLE and os.path.exists(tmp_wav) and os.path.getsize(tmp_wav) > 44:
                    try:
                        with wave.open(tmp_wav, 'rb') as wf:
                            frames = wf.readframes(wf.getnframes())
                            import numpy as np
                            pcm = np.frombuffer(frames, dtype="int16")
                            vol = float(audio_cfg.get("volume", 1.0) or 1.0)
                            pcm_f = pcm.astype("float32") / 32768.0
                            if abs(vol - 1.0) >= 0.01:
                                pcm_f = np.clip(pcm_f * vol, -1.0, 1.0)
                            # Non-blocking play with cooperative checks
                            sd.play(pcm_f, samplerate=wf.getframerate())
                            duration = len(pcm) / wf.getframerate()
                            end_time = time.time() + duration
                            while time.time() < end_time:
                                if _should_stop():
                                    sd.stop()
                                    break
                                time.sleep(0.05)
                    except EOFError:
                        logger.error("PIPER_DAEMON", "EOFError: generated wav file is empty or corrupted.")
                    except Exception as e:
                        import traceback
                        logger.error("PIPER_DAEMON", f"Playback chunk error: {repr(e)}\n{traceback.format_exc()}")
                elif not os.path.exists(tmp_wav) or os.path.getsize(tmp_wav) <= 44:
                    logger.error("PIPER_DAEMON", "Generated wav file is missing or too small (empty).")

                # Cleanup temp wav
                try:
                    if os.path.exists(tmp_wav): os.remove(tmp_wav)
                except: pass

        except Exception as e:
            logger.error("PIPER_DAEMON", f"speak error: {e}")
        finally:
            self._is_speaking = False
            if state: state.system_speaking = False

    def stop(self):
        logger.debug("PIPER_DAEMON", "Stopping TTS.")
        self._stop_flag = True
        self._is_speaking = False
        if SOUNDDEVICE_AVAILABLE:
            try: sd.stop()
            except: pass
        try:
            import winsound as ws
            ws.PlaySound(None, ws.SND_PURGE)
        except: pass


    def get_available_voices(self) -> dict:
        """
        Returns available Piper voices based on downloaded .onnx models.
        """
        root = _get_project_root()
        piper_dir = os.path.join(root, "bin", "piper")
        if not os.path.exists(piper_dir):
            return {}
        
        import glob
        models = glob.glob(os.path.join(piper_dir, "*.onnx"))
        voices = {}
        for m in models:
            basename = os.path.basename(m)
            voice_id = basename.replace('.onnx', '')
            voices[voice_id] = voice_id  # Piper doesn't have a built-in friendly name registry easily accessible here
        return voices


_engine_instance: PiperEngine | None = None
_engine_lock = threading.Lock()

def get_engine() -> PiperEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = PiperEngine()
    return _engine_instance
