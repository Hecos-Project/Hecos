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

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


def _get_project_root():
    current_file = os.path.abspath(__file__)
    return os.path.normpath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))


def _get_sample_rate(model_path: str) -> int:
    json_path = model_path + ".json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("audio", {}).get("sample_rate", 22050)
    except Exception:
        return 22050


class PiperDaemon:
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

    def preload(self, delay: float = 3.0):
        threading.Thread(target=self._start_daemon_delayed, args=(delay,), daemon=True).start()

    def _start_daemon_delayed(self, delay):
        time.sleep(delay)
        self._ensure_running()

    def _ensure_running(self):
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return

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
                    
                self._sample_rate = _get_sample_rate(model_path)
                speed = audio_cfg.get("speed", 1.0)
                self._length_scale = round(1.0 / speed, 3) if speed > 0 else 1.0
                self._noise_scale = round(audio_cfg.get("noise_scale", 0.667), 3)
                self._noise_w = round(audio_cfg.get("noise_w", 0.8), 3)
                self._sentence_silence = round(audio_cfg.get("sentence_silence", 0.2), 3)

                logger.info("PIPER_DAEMON", "Booting background JSON IPC Daemon...")

                cmd = [
                    piper_path, "-m", model_path, "--json-input", "--debug"
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

    def generate_wav(self, text: str, filepath: str) -> bool:
        """
        Requests Piper to generate a WAV via JSON IPC and waits for completion.
        Used by WebUI to get instant responses instead of subprocess lag.
        """
        if not text: return False
        
        self._ensure_running()
        if self._proc is None or self._proc.poll() is not None:
            logger.error("PIPER_DAEMON", "Piper IPC Daemon is dead.")
            return False

        # Block until the ONNX model is fully loaded (takes ~4-20s depending on hardware)
        if not self._ready_event.wait(timeout=30.0):
            logger.error("PIPER_DAEMON", "Piper did not initialize within 30s.")
            return False

        clean = text.replace('"', "").replace('\n', " ").strip()
        if not clean: return False

        req = {
            "text": clean,
            "output_file": filepath
        }

        self._synth_complete_event.clear()
        try:
            with self._lock:
                self._proc.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
                self._proc.stdin.flush()
        except Exception as e:
            logger.error("PIPER_DAEMON", f"IPC Write Error: {e}")
            return False

        # Wait max 120s for the wav to be completed (long texts can take more time)
        waited = self._synth_complete_event.wait(120.0)
        return waited and os.path.exists(filepath)

    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0):
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
                            # Non-blocking play with cooperative checks
                            sd.play(pcm.astype("float32") / 32768.0, samplerate=wf.getframerate())
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


_daemon_instance: PiperDaemon | None = None
_daemon_lock = threading.Lock()

def get_daemon() -> PiperDaemon:
    global _daemon_instance
    if _daemon_instance is None:
        with _daemon_lock:
            if _daemon_instance is None:
                _daemon_instance = PiperDaemon()
    return _daemon_instance
