"""
MODULE: Fish Speech Local Server Daemon Manager
DESCRIPTION: Manages the lifecycle of the local Fish Speech FastAPI inference server.
             Starts the server automatically in the background on-demand with zero user
             friction, monitors its health (/v1/health), captures logs, and handles clean shutdown.
"""

import os
import sys
import time
import socket
import atexit
import threading
import subprocess
from typing import Tuple, Optional
import urllib.request
import json

from hecos.core.logging import logger


def _get_project_root() -> str:
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(current_file, "..", "..", "..", "..", ".."))


def _resolve_python_executable() -> str:
    root = _get_project_root()
    env_python = os.path.join(root, "python_env", "python.exe")
    if os.path.isfile(env_python):
        return env_python
    venv_python = os.path.join(root, "venv", "Scripts", "python.exe")
    if os.path.isfile(venv_python):
        return venv_python
    return sys.executable


class FishSpeechDaemon:
    """
    Singleton process manager for the local Fish Speech server.
    """

    _instance: Optional["FishSpeechDaemon"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._log_file_handle = None
        self._last_error: str = ""
        self._host: str = "127.0.0.1"
        self._port: int = 8080
        self._log_path: str = os.path.join(_get_project_root(), "hecos", "logs", "fish_speech_server.log")
        self._spawned_by_me = False
        self._is_starting: bool = False
        self._start_thread: Optional[threading.Thread] = None
        # Auto-shutdown child server on exit ONLY if this Python instance spawned it
        atexit.register(self._atexit_stop)

    def _atexit_stop(self):
        """Cleanly stops server process on exit ONLY if spawned by this process."""
        if self._spawned_by_me and self._proc:
            self.stop(force_all=False)

    def is_starting(self) -> bool:
        """Returns True if a background startup thread is currently active."""
        return self._is_starting

    @classmethod
    def get_instance(cls) -> "FishSpeechDaemon":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = FishSpeechDaemon()
            return cls._instance

    def _resolve_target(self) -> Tuple[str, int]:
        """Resolves target host and port from audio.yaml configuration."""
        try:
            from hecos.core.audio.device_manager import get_audio_config
            cfg = get_audio_config().get("fish_speech", {})
            api_url = cfg.get("api_url", "http://127.0.0.1:8080/v1/tts").strip()
            from urllib.parse import urlparse
            parsed = urlparse(api_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 8080
            return host, port
        except Exception:
            return "127.0.0.1", 8080

    def is_local_target(self) -> bool:
        """Returns True if the configured api_url points to localhost/127.0.0.1."""
        host, _ = self._resolve_target()
        return host in ("127.0.0.1", "localhost", "0.0.0.0")

    def is_port_listening(self, host: str = "127.0.0.1", port: int = 8080) -> bool:
        """Fast non-blocking socket test to check if the port is accepting connections."""
        try:
            with socket.create_connection((host, port), timeout=0.15):
                return True
        except Exception:
            return False

    def is_healthy(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 2.0) -> bool:
        """Checks if the local server health endpoint returns ready."""
        url = f"http://{host}:{port}/v1/health"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hecos-Daemon"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return data.get("ok", False) and data.get("status") == "ready"
        except Exception:
            pass
        return False

    def check_preconditions(self) -> Tuple[bool, str]:
        """
        Validates all prerequisites needed to launch the local Fish Speech server.
        Returns (True, "OK") or (False, detailed_error_message).
        """
        root = _get_project_root()
        engine_dir = os.path.join(root, "hecos", "engines", "fish_speech")
        server_script = os.path.join(root, "hecos", "core", "audio", "tts", "fish_speech_server.py")
        s2_ckpt_dir = os.path.join(engine_dir, "checkpoints", "s2-pro")
        legacy_ckpt_dir = os.path.join(engine_dir, "checkpoints", "fish-speech-1.5")

        if not os.path.isfile(server_script):
            return False, f"Server script missing: {server_script}"

        repo_ok = (
            os.path.isfile(os.path.join(engine_dir, "fish_speech", "inference_engine", "__init__.py")) or
            os.path.isfile(os.path.join(engine_dir, "tools", "inference_engine", "__init__.py"))
        )
        if not os.path.isdir(engine_dir) or not repo_ok:
            return False, "Fish Speech engine repository missing or incomplete at hecos/engines/fish_speech."

        # Check model checkpoints: prefer S2-Pro, fallback to 1.5
        s2_weights = ["codec.pth", "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors", "config.json"]
        s2_missing = [f for f in s2_weights if not os.path.exists(os.path.join(s2_ckpt_dir, f)) or os.path.getsize(os.path.join(s2_ckpt_dir, f)) < 100]

        legacy_weights = [("model.pth", 100_000_000), ("firefly-gan-vq-fsq-8x1024-21hz-generator.pth", 50_000_000)]
        legacy_missing = [f for f, min_size in legacy_weights if not os.path.exists(os.path.join(legacy_ckpt_dir, f)) or os.path.getsize(os.path.join(legacy_ckpt_dir, f)) < min_size]

        if s2_missing and legacy_missing:
            return False, f"Missing model weights in checkpoints/s2-pro: {', '.join(s2_missing)}. Run engine installer from Central Hub."

        # Check critical Python modules
        missing_pkgs = []
        py_exe = _resolve_python_executable()
        for pkg in ["torch", "torchaudio", "soundfile", "fastapi", "uvicorn", "ormsgpack", "cachetools", "safetensors"]:
            try:
                __import__(pkg)
            except ImportError:
                if py_exe != sys.executable:
                    res = subprocess.run([py_exe, "-c", f"import {pkg}"], capture_output=True)
                    if res.returncode != 0:
                        missing_pkgs.append(pkg)
                else:
                    missing_pkgs.append(pkg)

        if missing_pkgs:
            return False, f"Missing required Python packages: {', '.join(missing_pkgs)}. Install dependencies via Central Hub."

        return True, "Preconditions satisfied."

    def preload(self, delay: float = 1.0, timeout: float = 240.0) -> Optional[threading.Thread]:
        """
        Starts the Fish Speech daemon asynchronously in the background.
        Non-blocking. If already healthy or currently starting, returns immediately.
        """
        host, port = self._resolve_target()
        if not self.is_local_target():
            return None

        if self.is_healthy(host, port, timeout=1.0):
            logger.info("FISH_SPEECH_DAEMON", f"Local Fish Speech server is already running and healthy on {host}:{port}.")
            return None

        with self._lock:
            if self._is_starting:
                logger.info("FISH_SPEECH_DAEMON", "Fish Speech server startup is already in progress in background.")
                return self._start_thread

            self._is_starting = True

            def _bg_run():
                try:
                    if delay > 0:
                        time.sleep(delay)
                    logger.info("FISH_SPEECH_DAEMON", f"🚀 Background auto-start: launching Fish Speech server on {host}:{port}...")
                    ok, msg = self.ensure_running(timeout=timeout)
                    if ok:
                        logger.info("FISH_SPEECH_DAEMON", f"✅ Fish Speech server background auto-startup complete ({host}:{port})!")
                    else:
                        logger.warning("FISH_SPEECH_DAEMON", f"⚠️ Fish Speech background auto-startup notice: {msg}")
                except Exception as e:
                    logger.error("FISH_SPEECH_DAEMON", f"Fish Speech background auto-startup exception: {e}")
                finally:
                    with self._lock:
                        self._is_starting = False

            t = threading.Thread(target=_bg_run, daemon=True, name="FishSpeechAutoStartThread")
            self._start_thread = t
            t.start()
            return t

    def ensure_running(self, timeout: float = 240.0) -> Tuple[bool, str]:
        """
        Ensures that the local Fish Speech server is up and responding.
        If already healthy, returns immediately.
        If not, validates preconditions, launches the server process, and waits until ready.
        """
        host, port = self._resolve_target()

        if not self.is_local_target():
            return True, f"Configured for remote/cloud API at {host}:{port}"

        # Fast path: already running and healthy or port is listening
        if self.is_healthy(host, port, timeout=1.5):
            return True, "Server is running and healthy."

        with self._lock:
            # Double-check inside lock
            if self.is_healthy(host, port, timeout=1.5):
                return True, "Server is running and healthy."

            # If our spawned process is still running, it's alive (possibly processing a heavy request)
            if self._proc and self._proc.poll() is None:
                return True, "Server process is active."

            # If port is listening, check if it responds
            if self.is_port_listening(host, port):
                time.sleep(1.0)
                if self.is_healthy(host, port, timeout=2.0) or (self._proc and self._proc.poll() is None):
                    return True, "Server is ready."
                logger.info("FISH_SPEECH_DAEMON", f"Port {port} is active; assuming server is handling requests.")
                return True, "Server is active."

            # Verify preconditions
            ok, msg = self.check_preconditions()
            if not ok:
                self._last_error = msg
                logger.error("FISH_SPEECH_DAEMON", f"Cannot start local server: {msg}")
                return False, msg

            # Start server process
            root = _get_project_root()
            server_script = os.path.join(root, "hecos", "core", "audio", "tts", "fish_speech_server.py")
            os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

            logger.info("FISH_SPEECH_DAEMON", f"🚀 Starting local Fish Speech server on {host}:{port}...")

            # Resolve configured checkpoint
            ckpt_name = "s2-pro"
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config().get("fish_speech", {})
                ckpt_name = cfg.get("model_checkpoint", "s2-pro") or "s2-pro"
            except Exception:
                pass

            engine_dir = os.path.join(root, "hecos", "engines", "fish_speech")
            target_ckpt_dir = os.path.join(engine_dir, "checkpoints", ckpt_name)
            if not os.path.isdir(target_ckpt_dir):
                target_ckpt_dir = os.path.join(engine_dir, "checkpoints", "s2-pro")

            cmd = [
                _resolve_python_executable(),
                server_script,
                "--host", host,
                "--port", str(port),
                "--device", "auto",
                "--checkpoint-dir", target_ckpt_dir,
                "--max-seq-len", "1024",
            ]

            kwargs = {
                "cwd": root,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

            try:
                # Open log file to append output
                log_file = open(self._log_path, "a", encoding="utf-8", errors="replace")
                log_file.write(f"\n--- Starting Fish Speech Server at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                log_file.flush()

                creationflags = 0
                if sys.platform == "win32":
                    # CREATE_NO_WINDOW only (0x08000000). DO NOT use DETACHED_PROCESS (0x00000008),
                    # so that when the parent process exits or is killed, the child does not remain an orphaned zombie.
                    creationflags = 0x08000000

                self._proc = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=root,
                    creationflags=creationflags,
                )
                self._spawned_by_me = True
                self._log_file_handle = log_file

            except Exception as launch_err:
                self._last_error = f"Failed to spawn server process: {launch_err}"
                logger.error("FISH_SPEECH_DAEMON", self._last_error)
                return False, self._last_error

            # Poll for health readiness
            start_wait = time.time()
            logger.info("FISH_SPEECH_DAEMON", f"Waiting for Fish Speech server to initialize (up to {timeout:.0f}s)...")

            while time.time() - start_wait < timeout:
                # Check if process crashed prematurely
                if self._proc.poll() is not None:
                    exit_code = self._proc.poll()
                    err_details = self._read_recent_log_lines()
                    self._last_error = f"Server exited unexpectedly (exit code {exit_code}): {err_details}"
                    logger.error("FISH_SPEECH_DAEMON", self._last_error)
                    return False, self._last_error

                if self.is_healthy(host, port):
                    elapsed = time.time() - start_wait
                    logger.info("FISH_SPEECH_DAEMON", f"✅ Fish Speech local server ready on {host}:{port} (booted in {elapsed:.1f}s)!")
                    return True, "Server ready."

                time.sleep(0.5)

            # Timeout reached
            err_details = self._read_recent_log_lines()
            self._last_error = f"Server startup timed out after {timeout:.0f}s. Last log: {err_details}"
            logger.error("FISH_SPEECH_DAEMON", self._last_error)
            return False, self._last_error

    def _read_recent_log_lines(self, num_lines: int = 10) -> str:
        """Reads recent lines from the server log file for diagnostics."""
        try:
            if not os.path.exists(self._log_path):
                return "No log file found."
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                recent = [l.strip() for l in lines[-num_lines:] if l.strip()]
                return " | ".join(recent)
        except Exception as e:
            return f"Could not read log: {e}"

    def stop(self, force_all: bool = False):
        """Stops the local server process if running."""
        with self._lock:
            was_spawned_by_me = self._spawned_by_me
            self._spawned_by_me = False
            if self._proc and self._proc.poll() is None:
                logger.info("FISH_SPEECH_DAEMON", "Stopping local Fish Speech server...")
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._proc.pid)], capture_output=True, timeout=5)
                    else:
                        self._proc.terminate()
                        self._proc.wait(timeout=3.0)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
                self._proc = None

            # Only scan and terminate lingering processes if force_all is requested or if we were the owner
            if force_all or was_spawned_by_me:
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            cmdline = " ".join(proc.info.get('cmdline') or [])
                            if 'fish_speech_server.py' in cmdline and proc.pid != os.getpid():
                                logger.info("FISH_SPEECH_DAEMON", f"Terminating process {proc.pid} running fish_speech_server.py...")
                                if sys.platform == "win32":
                                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=5)
                                else:
                                    proc.kill()
                        except Exception:
                            pass
                except Exception:
                    pass

            if self._log_file_handle:
                try:
                    self._log_file_handle.close()
                except Exception:
                    pass
                self._log_file_handle = None
            logger.info("FISH_SPEECH_DAEMON", "Local Fish Speech server stopped.")

    def restart(self, timeout: float = 90.0) -> Tuple[bool, str]:
        """Restarts the local Fish Speech server cleanly."""
        self.stop()
        time.sleep(1.0)
        return self.ensure_running(timeout=timeout)

    def get_last_error(self) -> str:
        return self._last_error
