"""
MODULE: Fish Speech Local Server Daemon Manager
DESCRIPTION: Manages the lifecycle of the local Fish Speech FastAPI inference server.
             Starts the server automatically in the background with single-instance locking,
             Windows Job Object binding, non-blocking health polling (/v1/health),
             port-identity verification, and clean shutdown.
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
from hecos.core.audio.tts.process_registry import (
    DEFAULT_FISH_PORT,
    DEFAULT_FISH_URL,
    register_tts_process,
    unregister_tts_process,
    reap_orphan_tts_processes,
    kill_process_tree_safe,
)


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
        self._last_error: str = ""
        self._host: str = "127.0.0.1"
        self._port: int = DEFAULT_FISH_PORT
        self._log_path: str = os.path.join(_get_project_root(), "hecos", "logs", "fish_speech_server.log")
        self._spawned_by_me = False
        self._is_starting: bool = False
        self._cancel_start: bool = False
        self._ready_event = threading.Event()
        self._start_thread: Optional[threading.Thread] = None
        atexit.register(self._atexit_stop)

    def _atexit_stop(self):
        """Cleanly stops server process on exit."""
        if self._spawned_by_me or self._proc is not None:
            self.stop(force_all=False)

    def is_starting(self) -> bool:
        """Returns True if a startup is currently initializing the model."""
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
            api_url = (cfg.get("api_url") or DEFAULT_FISH_URL).strip()
            from urllib.parse import urlparse
            parsed = urlparse(api_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or DEFAULT_FISH_PORT
            return host, port
        except Exception:
            return "127.0.0.1", DEFAULT_FISH_PORT

    def is_local_target(self) -> bool:
        """Returns True if the configured api_url points to localhost/127.0.0.1."""
        host, _ = self._resolve_target()
        return host in ("127.0.0.1", "localhost", "0.0.0.0")

    def is_port_listening(self, host: str = "127.0.0.1", port: int = DEFAULT_FISH_PORT) -> bool:
        """Fast non-blocking socket test to check if the port is accepting connections."""
        probe_host = "127.0.0.1" if host in ("localhost", "0.0.0.0") else host
        try:
            with socket.create_connection((probe_host, port), timeout=0.08):
                return True
        except Exception:
            return False

    def probe_health(self, host: str = "127.0.0.1", port: int = DEFAULT_FISH_PORT, timeout: float = 1.5) -> Optional[dict]:
        """Queries /v1/health and verifies that the responder is genuinely Hecos Fish Speech."""
        probe_host = "127.0.0.1" if host in ("localhost", "0.0.0.0") else host
        url = f"http://{probe_host}:{port}/v1/health"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hecos-Daemon"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if isinstance(data, dict) and data.get("ok"):
                        is_fish = (
                            data.get("service") == "hecos-fish-speech"
                            or str(data.get("engine", "")).startswith("fish_speech")
                        )
                        if is_fish:
                            return data
        except Exception:
            pass
        return None

    def is_healthy(self, host: str = "127.0.0.1", port: int = DEFAULT_FISH_PORT, timeout: float = 1.5) -> bool:
        """Checks if the local Fish Speech server health endpoint returns ready."""
        data = self.probe_health(host, port, timeout=timeout)
        return bool(data and data.get("status") == "ready")

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

        s2_weights = ["codec.pth", "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors", "config.json"]
        s2_missing = [f for f in s2_weights if not os.path.exists(os.path.join(s2_ckpt_dir, f)) or os.path.getsize(os.path.join(s2_ckpt_dir, f)) < 100]

        legacy_weights = [("model.pth", 100_000_000), ("firefly-gan-vq-fsq-8x1024-21hz-generator.pth", 50_000_000)]
        legacy_missing = [f for f, min_size in legacy_weights if not os.path.exists(os.path.join(legacy_ckpt_dir, f)) or os.path.getsize(os.path.join(legacy_ckpt_dir, f)) < min_size]

        if s2_missing and legacy_missing:
            return False, f"Missing model weights in checkpoints/s2-pro: {', '.join(s2_missing)}. Run engine installer from Central Hub."

        missing_pkgs = []
        py_exe = _resolve_python_executable()
        for pkg in ["torch", "torchaudio", "soundfile", "fastapi", "uvicorn", "ormsgpack", "cachetools", "safetensors"]:
            try:
                __import__(pkg)
            except ImportError:
                if py_exe != sys.executable:
                    res = subprocess.run(
                        [py_exe, "-c", f"import {pkg}"],
                        capture_output=True,
                        creationflags=0x08000000 if sys.platform == "win32" else 0,
                    )
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
            if self._is_starting or (self._start_thread and self._start_thread.is_alive()):
                logger.info("FISH_SPEECH_DAEMON", "Fish Speech server startup is already in progress in background.")
                return self._start_thread

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

            t = threading.Thread(target=_bg_run, daemon=True, name="FishSpeechAutoStartThread")
            self._start_thread = t
            t.start()
            return t

    def ensure_running(self, timeout: float = 240.0) -> Tuple[bool, str]:
        """
        Ensures that the local Fish Speech server is up and responding.
        Never holds self._lock during the readiness polling wait so stop() and status
        queries remain instant and duplicate spawns are impossible.
        """
        host, port = self._resolve_target()

        if not self.is_local_target():
            return True, f"Configured for remote/cloud API at {host}:{port}"

        if self.is_healthy(host, port, timeout=1.5):
            return True, "Server is running and healthy."

        wait_existing_event = None
        proc = None

        with self._lock:
            if self.is_healthy(host, port, timeout=1.5):
                return True, "Server is running and healthy."

            if self._is_starting:
                wait_existing_event = self._ready_event
            elif self._proc and self._proc.poll() is None:
                # Process is already alive (either handling a heavy request or finishing init)
                return True, "Server process is active."
            else:
                # Check if port is already bound by an existing Fish server or a foreign process
                if self.is_port_listening(host, port):
                    health = self.probe_health(host, port, timeout=2.0)
                    if health:
                        if health.get("status") == "ready":
                            return True, "Server is ready."
                        # Fish server is initializing
                        self._is_starting = True
                        self._cancel_start = False
                        self._ready_event.clear()
                    else:
                        msg = (
                            f"Port {port} is already occupied by another non-Fish application. "
                            f"Change the Fish Speech port in Voice Settings."
                        )
                        self._last_error = msg
                        logger.error("FISH_SPEECH_DAEMON", msg)
                        return False, msg

                if not self._is_starting:
                    # Clean up any stale orphaned fish_speech_server.py before spawning
                    reap_orphan_tts_processes("fish_speech")

                    ok, msg = self.check_preconditions()
                    if not ok:
                        self._last_error = msg
                        logger.error("FISH_SPEECH_DAEMON", f"Cannot start local server: {msg}")
                        return False, msg

                    root = _get_project_root()
                    server_script = os.path.join(root, "hecos", "core", "audio", "tts", "fish_speech_server.py")
                    os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

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

                    bind_host = "127.0.0.1" if host == "localhost" else host
                    cmd = [
                        _resolve_python_executable(),
                        server_script,
                        "--host", bind_host,
                        "--port", str(port),
                        "--device", "auto",
                        "--checkpoint-dir", target_ckpt_dir,
                        "--max-seq-len", "1024",
                    ]

                    logger.info("FISH_SPEECH_DAEMON", f"🚀 Starting local Fish Speech server on {bind_host}:{port}...")
                    try:
                        log_file = open(self._log_path, "a", encoding="utf-8", errors="replace")
                        log_file.write(f"\n--- Starting Fish Speech Server at {time.strftime('%Y-%m-%d %H:%M:%S')} (port {port}) ---\n")
                        log_file.flush()
                        creationflags = 0x08000000 if sys.platform == "win32" else 0
                        try:
                            proc = subprocess.Popen(
                                cmd,
                                stdout=log_file,
                                stderr=subprocess.STDOUT,
                                cwd=root,
                                creationflags=creationflags,
                            )
                        finally:
                            try:
                                log_file.close()
                            except Exception:
                                pass

                        self._proc = proc
                        self._spawned_by_me = True
                        self._is_starting = True
                        self._cancel_start = False
                        self._ready_event.clear()
                        register_tts_process("fish_speech", proc.pid, name="fish_speech_server", port=port)
                    except Exception as launch_err:
                        self._last_error = f"Failed to spawn server process: {launch_err}"
                        logger.error("FISH_SPEECH_DAEMON", self._last_error)
                        return False, self._last_error

        # If another caller was already starting the server, wait on its event without duplicating
        if wait_existing_event is not None:
            wait_existing_event.wait(timeout=timeout)
            if self.is_healthy(host, port, timeout=1.5):
                return True, "Server ready."
            return False, self._last_error or "Startup cancelled or timed out."

        # Poll readiness OUTSIDE self._lock so stop() and status calls never block
        start_wait = time.time()
        logger.info("FISH_SPEECH_DAEMON", f"Waiting for Fish Speech server to initialize (up to {timeout:.0f}s)...")
        try:
            while time.time() - start_wait < timeout:
                if self._cancel_start:
                    return False, "Server startup cancelled by user."

                cur_proc = self._proc
                if proc is not None and (cur_proc is None or cur_proc.poll() is not None):
                    exit_code = proc.poll()
                    err_details = self._read_recent_log_lines()
                    self._last_error = f"Server exited unexpectedly (exit code {exit_code}): {err_details}"
                    logger.error("FISH_SPEECH_DAEMON", self._last_error)
                    unregister_tts_process("fish_speech", proc.pid)
                    return False, self._last_error

                if self.is_healthy(host, port, timeout=1.5):
                    elapsed = time.time() - start_wait
                    self._last_error = ""
                    logger.info("FISH_SPEECH_DAEMON", f"✅ Fish Speech local server ready on {host}:{port} (booted in {elapsed:.1f}s)!")
                    return True, "Server ready."

                time.sleep(0.5)

            err_details = self._read_recent_log_lines()
            self._last_error = f"Server startup timed out after {timeout:.0f}s. Last log: {err_details}"
            logger.error("FISH_SPEECH_DAEMON", self._last_error)
            return False, self._last_error
        finally:
            with self._lock:
                self._is_starting = False
                self._ready_event.set()

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

    def stop(self, force_all: bool = True):
        """Stops the local server process if running and releases GPU VRAM."""
        with self._lock:
            self._cancel_start = True
            self._is_starting = False
            self._ready_event.set()
            was_spawned_by_me = self._spawned_by_me
            self._spawned_by_me = False
            proc = self._proc
            self._proc = None

        if proc is not None:
            logger.info("FISH_SPEECH_DAEMON", f"Stopping local Fish Speech server (PID {proc.pid})...")
            kill_process_tree_safe(proc.pid)
            unregister_tts_process("fish_speech", proc.pid)

        if force_all:
            reap_orphan_tts_processes("fish_speech", force_all=True)
        elif was_spawned_by_me:
            reap_orphan_tts_processes("fish_speech", force_all=False, include_own=True)

        logger.info("FISH_SPEECH_DAEMON", "Local Fish Speech server stopped.")

    def restart(self, timeout: float = 90.0) -> Tuple[bool, str]:
        """Restarts the local Fish Speech server cleanly."""
        self.stop(force_all=True)
        time.sleep(0.8)
        return self.ensure_running(timeout=timeout)

    def get_last_error(self) -> str:
        return self._last_error

    def get_runtime_status(self) -> dict:
        """Returns comprehensive runtime diagnostics for UI and Tray Process Manager."""
        host, port = self._resolve_target()
        is_local = self.is_local_target()
        listening = self.is_port_listening(host, port) if is_local else False
        health = self.probe_health(host, port, timeout=0.6) if (is_local and listening) else None
        healthy = bool(health and health.get("status") == "ready")

        pid = None
        ram_mb = 0.0
        vram_mb = float(health.get("vram_mb") or 0.0) if health else 0.0
        device = (health.get("device") or "cuda").upper() if health else "—"

        if self._proc and self._proc.poll() is None:
            pid = self._proc.pid
        elif health and health.get("pid"):
            pid = int(health["pid"])

        try:
            import psutil
            if not pid and is_local and (listening or self._is_starting):
                for p in psutil.process_iter(["pid", "cmdline"]):
                    try:
                        cmd = " ".join(p.info.get("cmdline") or [])
                        if "fish_speech_server.py" in cmd:
                            pid = p.info["pid"]
                            break
                    except Exception:
                        pass
            if pid and psutil.pid_exists(pid):
                ram_mb = round(psutil.Process(pid).memory_info().rss / (1024 * 1024), 1)
        except Exception:
            pass

        ckpt = "s2-pro"
        try:
            from hecos.core.audio.device_manager import get_audio_config
            ckpt = get_audio_config().get("fish_speech", {}).get("model_checkpoint", "s2-pro") or "s2-pro"
        except Exception:
            pass

        if not is_local:
            state = "cloud"
        elif healthy:
            state = "online"
        elif self._is_starting or (health and health.get("status") == "initializing"):
            state = "starting"
        else:
            state = "offline"

        return {
            "status": state,
            "loaded": healthy,
            "is_local": is_local,
            "host": host,
            "port": port,
            "listening": listening,
            "healthy": healthy,
            "pid": pid,
            "ram_mb": ram_mb,
            "vram_mb": vram_mb,
            "device": device,
            "mode": "daemon" if is_local else "cloud",
            "model": f"Fish Speech ({ckpt})",
            "last_error": self._last_error,
        }
