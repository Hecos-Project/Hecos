"""
MODULE: Piper TTS Daemon (JSON IPC Edition)
DESCRIPTION: Runs a permanent `piper.exe --json-input` subprocess in the background.
             Accepts JSON requests via stdin for both WebUI WAV synthesis and PC speaker
             streaming, avoiding reloading the ONNX model on every message.
"""
import os
import sys
import json
import time
import atexit
import subprocess
import threading
import wave
import uuid

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine
from hecos.core.audio.tts.process_registry import (
    register_tts_process,
    unregister_tts_process,
    reap_orphan_tts_processes,
    kill_process_tree_safe,
)

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


def _get_project_root():
    current_file = os.path.abspath(__file__)
    return os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
    )


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
        self._ipc_lock = threading.Lock()
        self._cli_semaphore = threading.Semaphore(2)
        self._preload_lock = threading.Lock()
        self._is_preloading = False

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

        atexit.register(self._atexit_stop)

    def _atexit_stop(self):
        try:
            self.unload()
        except Exception:
            pass

    def is_loaded(self) -> bool:
        return bool(self._proc is not None and self._proc.poll() is None and self._ready_event.is_set())

    def preload(self, delay: float = 1.0, blocking: bool = False):
        if self.is_loaded():
            return None
        if blocking:
            if delay > 0:
                time.sleep(delay)
            self._ensure_running()
            if self._proc is not None and self._proc.poll() is None:
                self._ready_event.wait(timeout=20.0)
            return None

        with self._preload_lock:
            if self._is_preloading:
                return None
            self._is_preloading = True

        def _bg():
            try:
                if delay > 0:
                    time.sleep(delay)
                self._ensure_running()
            finally:
                with self._preload_lock:
                    self._is_preloading = False

        t = threading.Thread(target=_bg, daemon=True, name="PiperDaemonPreload")
        t.start()
        return t

    def unload(self) -> bool:
        """Stops the persistent Piper IPC daemon process and frees its RAM."""
        self.stop()
        with self._lock:
            proc = self._proc
            self._proc = None
            self._ready_event.clear()
            self._daemon_model = None

        if proc is not None:
            pid = proc.pid
            logger.info("PIPER_DAEMON", f"Stopping Piper IPC daemon (PID {pid})...")
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception:
                pass
            kill_process_tree_safe(pid)
            unregister_tts_process("piper", pid)
        return True

    def get_runtime_status(self) -> dict:
        params = self._resolve_piper_params(None)
        installed = os.path.isfile(params["piper_path"]) and os.path.isfile(params["model_path"])
        proc = self._proc
        alive = bool(proc is not None and proc.poll() is None)
        pid = proc.pid if alive else None
        ram_mb = 0.0
        if pid:
            try:
                import psutil
                if psutil.pid_exists(pid):
                    ram_mb = round(psutil.Process(pid).memory_info().rss / (1024 * 1024), 1)
            except Exception:
                pass

        if alive and self._ready_event.is_set():
            state = "online"
        elif alive or self._is_preloading:
            state = "starting"
        else:
            state = "offline"

        model_label = os.path.basename(self._daemon_model or params["model_path"])
        return {
            "status": state,
            "loaded": state == "online",
            "installed": installed,
            "mode": "daemon",
            "pid": pid,
            "port": None,
            "device": "CPU (ONNX)",
            "ram_mb": ram_mb,
            "vram_mb": 0.0,
            "model": model_label,
        }

    def _ensure_running(self):
        with self._lock:
            try:
                params = self._resolve_piper_params(None)
                piper_path = params["piper_path"]
                model_path = params["model_path"]

                if not os.path.isfile(piper_path):
                    logger.warning("PIPER_DAEMON", f"Piper executable not found at {piper_path}. TTS daemon will not start.")
                    self._proc = None
                    return

                if not os.path.isfile(model_path):
                    logger.warning("PIPER_DAEMON", f"Piper ONNX model not found at {model_path}. TTS daemon will not start.")
                    self._proc = None
                    return

                from hecos.core.ext_deps import require
                if not require("vc_redist"):
                    logger.warning("PIPER_DAEMON", "VC Redist missing. Piper TTS daemon will not start.")
                    self._proc = None
                    return

                self._sample_rate = _get_sample_rate(model_path)
                self._length_scale = params["length_scale"]
                self._noise_scale = params["noise_scale"]
                self._noise_w = params["noise_w"]
                self._sentence_silence = params["sentence_silence"]

                norm_model = os.path.normcase(os.path.abspath(model_path))
                norm_daemon_model = os.path.normcase(os.path.abspath(self._daemon_model)) if self._daemon_model else None

                if self._proc is not None and self._proc.poll() is None:
                    if (
                        norm_daemon_model == norm_model
                        and self._daemon_length_scale == self._length_scale
                        and self._daemon_noise_scale == self._noise_scale
                        and self._daemon_noise_w == self._noise_w
                        and self._daemon_sentence_silence == self._sentence_silence
                    ):
                        return
                    logger.info("PIPER_DAEMON", "Piper settings changed — recycling IPC daemon...")
                    old_pid = self._proc.pid
                    kill_process_tree_safe(old_pid)
                    unregister_tts_process("piper", old_pid)
                    self._proc = None

                # Ensure no orphaned piper --json-input process is lingering
                reap_orphan_tts_processes("piper")

                logger.info(
                    "PIPER_DAEMON",
                    f"Booting background JSON IPC Daemon (model={os.path.basename(model_path)}, len_scale={self._length_scale})..."
                )

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
                    "cwd": os.path.dirname(piper_path),
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

                self._ready_event.clear()
                proc = subprocess.Popen(cmd, **kwargs)
                self._proc = proc
                register_tts_process("piper", proc.pid, name="piper.exe")

                self._daemon_model = model_path
                self._daemon_length_scale = self._length_scale
                self._daemon_noise_scale = self._noise_scale
                self._daemon_noise_w = self._noise_w
                self._daemon_sentence_silence = self._sentence_silence

                self._stderr_thread = threading.Thread(
                    target=self._read_stderr_loop, args=(proc,), daemon=True, name="PiperStderrReader"
                )
                self._stderr_thread.start()

                logger.info("PIPER_DAEMON", f"Eternal JSON Daemon booted (PID {proc.pid}) — waiting for model load...")

            except Exception as e:
                logger.error("PIPER_DAEMON", f"Failed to start JSON daemon: {e}")
                self._proc = None

    def _read_stderr_loop(self, proc):
        """Monitors Piper stderr. Sets ready/synth events at the right moments."""
        while proc and proc.poll() is None:
            try:
                line = proc.stderr.readline()
                if not line:
                    break
                txt = line.decode("utf-8", errors="ignore")
                if "Initialized piper" in txt:
                    self._ready_event.set()
                    logger.info("PIPER_DAEMON", "Eternal JSON Daemon ready.")
                elif "Real-time factor" in txt:
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

    def _can_use_daemon_for(self, params: dict) -> bool:
        """Returns True if requested parameters match global config so the warm IPC daemon can serve it."""
        base = self._resolve_piper_params(None)
        return (
            os.path.normcase(os.path.abspath(params["model_path"]))
            == os.path.normcase(os.path.abspath(base["model_path"]))
            and params["length_scale"] == base["length_scale"]
            and params["noise_scale"] == base["noise_scale"]
            and params["noise_w"] == base["noise_w"]
            and params["sentence_silence"] == base["sentence_silence"]
        )

    def _synthesize_via_daemon(self, clean_text: str, filepath: str, timeout: float = 30.0, volume: float = 1.0) -> bool:
        """Synthesizes WAV using the warm persistent `piper.exe --json-input` daemon."""
        abs_out = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)

        with self._ipc_lock:
            self._ensure_running()
            if self._proc is None or self._proc.poll() is not None:
                return False
            if not self._ready_event.wait(timeout=25.0):
                logger.warning("PIPER_DAEMON", "Daemon did not become ready within 25s; falling back to CLI.")
                return False

            try:
                if os.path.exists(abs_out):
                    os.remove(abs_out)
            except Exception:
                pass

            req = {"text": clean_text, "output_file": abs_out}
            self._synth_complete_event.clear()
            try:
                self._proc.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
                self._proc.stdin.flush()
            except Exception as exc:
                logger.warning("PIPER_DAEMON", f"IPC write error ({exc}); recycling daemon...")
                return False

            waited = self._synth_complete_event.wait(timeout=min(max(timeout, 10.0), 120.0))
            if not waited:
                logger.warning("PIPER_DAEMON", "IPC synthesis wait timed out; falling back to CLI.")
                return False

        success = os.path.isfile(abs_out) and os.path.getsize(abs_out) > 44
        if success and volume and abs(volume - 1.0) >= 0.01:
            self._adjust_volume(abs_out, volume)
        return success

    def generate_wav(self, text: str, filepath: str, session_overrides=None, **kwargs) -> bool:
        """
        Synthesizes audio to a WAV file. Uses the persistent in-RAM IPC daemon when
        parameters match global settings, falling back to capped CLI subprocesses for overrides.
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

        # Fast path: route through warm persistent IPC daemon
        if self._can_use_daemon_for(params):
            if self._synthesize_via_daemon(clean, filepath, timeout=params["timeout"], volume=params.get("volume", 1.0)):
                return True

        # Fallback path: one-shot CLI (capped by semaphore to prevent process storms)
        cmd = [
            piper_bin,
            "-m", model_file,
            "-f", filepath,
            "--length_scale", str(params["length_scale"]),
            "--noise_scale", str(params["noise_scale"]),
            "--noise_w", str(params["noise_w"]),
            "--sentence_silence", str(params["sentence_silence"]),
        ]

        logger.info(
            "PIPER_DAEMON",
            f"CLI synth (override): model={os.path.basename(model_file)}, len_scale={params['length_scale']}, "
            f"noise={params['noise_scale']}, noisew={params['noise_w']}, silence={params['sentence_silence']}"
        )

        kwargs_proc = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.PIPE,
            "cwd": os.path.dirname(piper_bin),
        }
        if sys.platform == "win32":
            kwargs_proc["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        with self._cli_semaphore:
            proc = None
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
                if proc:
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
        if not text:
            return
        self._ensure_running()
        if self._proc is None or self._proc.poll() is not None:
            return

        clean = text.replace('"', "").replace("\n", " ").strip()
        if not clean:
            return

        from hecos.core.audio.device_manager import get_audio_config
        audio_cfg = get_audio_config()

        import re
        raw = re.split(r'(?<=[.!?…])\s+|(?<=[—\-]{2})\s*', clean)
        sentences = [r.strip() for r in raw if r.strip()]

        self._is_speaking = True
        self._stop_flag = False
        if state:
            state.system_speaking = True

        def _should_stop():
            if self._stop_flag:
                return True
            if _run_id:
                try:
                    from hecos.modules.flows.engine import is_run_aborted
                    if is_run_aborted(_run_id):
                        return True
                except Exception:
                    pass
            if _timeout and _timeout > 0 and (time.time() - _start) > _timeout:
                return True
            return False

        if not self._ready_event.wait(timeout=30.0):
            logger.error("PIPER_DAEMON", "Piper not ready within 30s — aborting speak()")
            self._is_speaking = False
            if state:
                state.system_speaking = False
            return

        root = _get_project_root()
        temp_dir = os.path.join(root, "hecos", "media", "audio", "temp_tts")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            for s in sentences:
                if _should_stop():
                    break

                uid = uuid.uuid4().hex[:8]
                tmp_wav = os.path.join(temp_dir, f"chunk_{uid}.wav")

                synthesized = self._synthesize_via_daemon(s, tmp_wav, timeout=30.0, volume=1.0)
                if _should_stop():
                    try:
                        if os.path.exists(tmp_wav):
                            os.remove(tmp_wav)
                    except Exception:
                        pass
                    break

                if not synthesized:
                    logger.error("PIPER_DAEMON", "Timeout or failure waiting for TTS chunk synthesis.")
                    continue

                if SOUNDDEVICE_AVAILABLE and os.path.exists(tmp_wav) and os.path.getsize(tmp_wav) > 44:
                    try:
                        with wave.open(tmp_wav, "rb") as wf:
                            frames = wf.readframes(wf.getnframes())
                            import numpy as np
                            pcm = np.frombuffer(frames, dtype="int16")
                            vol = float(audio_cfg.get("volume", 1.0) or 1.0)
                            pcm_f = pcm.astype("float32") / 32768.0
                            if abs(vol - 1.0) >= 0.01:
                                pcm_f = np.clip(pcm_f * vol, -1.0, 1.0)
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

                try:
                    if os.path.exists(tmp_wav):
                        os.remove(tmp_wav)
                except Exception:
                    pass

        except Exception as e:
            logger.error("PIPER_DAEMON", f"speak error: {e}")
        finally:
            self._is_speaking = False
            if state:
                state.system_speaking = False

    def stop(self):
        logger.debug("PIPER_DAEMON", "Stopping TTS.")
        self._stop_flag = True
        self._is_speaking = False
        if SOUNDDEVICE_AVAILABLE:
            try:
                sd.stop()
            except Exception:
                pass
        try:
            import winsound as ws
            ws.PlaySound(None, ws.SND_PURGE)
        except Exception:
            pass

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
            voice_id = basename.replace(".onnx", "")
            voices[voice_id] = voice_id
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
