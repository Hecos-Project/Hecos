"""
MODULE: Ollama Lifecycle Manager
DESCRIPTION: Manages automatic startup and model pre-warming for the Ollama backend.
             - Auto-starts the Ollama server process if not running (configurable)
             - Pre-warms the configured default model into VRAM at boot (configurable)
             - All operations are non-blocking (daemon threads), fully safe on failure
             - Only activates when backend.type == 'ollama' OR when forced via config flag

Config keys (backend.ollama):
    auto_start_server  : bool  (default: False) — Launch 'ollama serve' if not already running
    warmup_model       : bool  (default: False) — Pre-load model into GPU at Hecos startup
    warmup_keep_alive  : str   (default: '120m') — keep_alive value sent during warm-up
"""

import os
import sys
import time
import shutil
import threading
import subprocess
from typing import Optional
from hecos.core.logging import logger


# ── Constants ────────────────────────────────────────────────────────────────

_OLLAMA_HEALTH_URL   = "/api/tags"          # GET — returns 200 when Ollama is up
_WARMUP_ENDPOINT     = "/api/generate"      # POST — empty-prompt trick to load model into VRAM
_DEFAULT_TIMEOUT     = 5                    # seconds for health check
_WARMUP_TIMEOUT      = 120                  # seconds to wait for model load
_RETRY_INTERVAL      = 0.5                  # seconds between health check retries
_SERVER_READY_TRIES  = 60                   # max retries (= 30 s) for server readiness


# ── Public helpers ────────────────────────────────────────────────────────────

def is_ollama_running(ollama_url: str, timeout: int = _DEFAULT_TIMEOUT) -> bool:
    """Returns True if the Ollama API is reachable and responding."""
    try:
        import urllib.request
        import urllib.error
        base = ollama_url.rstrip("/")
        # Check primary URL and 127.0.0.1 fallback (prevents IPv6 ::1 resolution timeouts on Windows)
        test_urls = [f"{base}{_OLLAMA_HEALTH_URL}"]
        if "localhost" in base:
            test_urls.append(base.replace("localhost", "127.0.0.1") + _OLLAMA_HEALTH_URL)
        for u in test_urls:
            try:
                req = urllib.request.Request(u, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def find_ollama_executable(preferred_path: Optional[str] = None) -> Optional[str]:
    """Locate the ollama binary or GUI app. Returns full path or None.
    If preferred_path is provided and points to a file or folder, it takes precedence.
    """
    if preferred_path and preferred_path.strip():
        p = preferred_path.strip().strip('"').strip("'")
        if os.path.isfile(p):
            return p
        if os.path.isdir(p):
            for candidate in ("ollama app.exe", "ollama.exe"):
                sub = os.path.join(p, candidate)
                if os.path.isfile(sub):
                    return sub

    # 1. System PATH
    found = shutil.which("ollama")
    if found:
        return found
    # 2. Default Windows installation paths (check both CLI and GUI app)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe"),
        os.path.join(local_app_data, "Programs", "Ollama", "ollama app.exe"),
        r"C:\Program Files\Ollama\ollama.exe",
        r"C:\Program Files\Ollama\ollama app.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    # 3. Linux/macOS common paths
    for c in ("/usr/local/bin/ollama", "/usr/bin/ollama", "/opt/homebrew/bin/ollama"):
        if os.path.isfile(c):
            return c
    return None


# ── Ollama Lifecycle Manager ──────────────────────────────────────────────────

class OllamaLifecycleManager:
    """
    Singleton that manages the Ollama server and model warm-up lifecycle.
    Thread-safe, non-blocking, fully fire-and-forget.
    """

    _instance: Optional["OllamaLifecycleManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._server_proc: Optional[subprocess.Popen] = None
        self._started_by_us = False

    @classmethod
    def get_instance(cls) -> "OllamaLifecycleManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    # ── Auto-start server ─────────────────────────────────────────────────────

    def maybe_auto_start_server(self, config: dict):
        """
        If backend.ollama.auto_start_server is True and Ollama is not already
        running, launch 'ollama serve' in the background.
        Returns immediately — actual startup happens in a daemon thread.
        """
        ollama_cfg  = config.get("backend", {}).get("ollama", {})
        if not ollama_cfg.get("auto_start_server", False):
            return  # Feature disabled

        ollama_url = ollama_cfg.get("url", "http://localhost:11434")

        if is_ollama_running(ollama_url):
            logger.info("[OllamaLifecycle] Server already running — skipping auto-start.")
            return

        user_pref = ollama_cfg.get("binary_path", "")
        exe = find_ollama_executable(user_pref)
        if not exe:
            logger.warning("[OllamaLifecycle] auto_start_server=True but Ollama executable not found. Configure path in Backend settings.")
            return

        is_gui_app = "ollama app.exe" in exe.lower()
        mode_label = "GUI app" if is_gui_app else "daemon"
        logger.info(f"[OllamaLifecycle] Ollama not running. Auto-starting '{exe}' ({mode_label}) in background...")
        t = threading.Thread(target=self._start_server_bg, args=(exe, ollama_url), daemon=True,
                             name="OllamaAutoStart")
        t.start()

    def _start_server_bg(self, exe: str, ollama_url: str):
        """Background thread: spawns Ollama (daemon or GUI app) and waits for readiness."""
        try:
            exe_lower = exe.lower()
            is_gui_app = "ollama app.exe" in exe_lower

            # If user selected 'ollama app.exe', launch it directly without arguments.
            # If CLI binary 'ollama.exe', launch with 'serve' argument.
            cmd = [exe] if is_gui_app else [exe, "serve"]

            kwargs = dict(
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # On Windows:
            # - For GUI app: CREATE_NEW_PROCESS_GROUP so it stays detached
            # - For CLI daemon: CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW (no console flash)
            if os.name == "nt":
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                if is_gui_app:
                    kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
                else:
                    CREATE_NO_WINDOW = 0x08000000
                    kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
            else:
                kwargs["close_fds"] = True

            self._server_proc = subprocess.Popen(cmd, **kwargs)
            self._started_by_us = True
            logger.info(f"[OllamaLifecycle] 'ollama serve' spawned (PID {self._server_proc.pid}).")

            # Wait until the API responds
            for attempt in range(_SERVER_READY_TRIES):
                time.sleep(_RETRY_INTERVAL)
                if is_ollama_running(ollama_url, timeout=2):
                    logger.info(f"[OllamaLifecycle] ✅ Ollama server ready after {(attempt+1)*_RETRY_INTERVAL:.1f}s.")
                    return
            logger.warning("[OllamaLifecycle] Ollama did not become ready within expected time.")
        except Exception as e:
            logger.error(f"[OllamaLifecycle] Failed to auto-start Ollama: {e}")

    # ── Model warm-up ─────────────────────────────────────────────────────────

    def maybe_warmup_model(self, config: dict, delay: float = 3.0):
        """
        If backend.ollama.warmup_model is True, send an empty-prompt request
        to Ollama to force the configured model into VRAM immediately.
        Returns immediately — actual loading happens in a daemon thread.

        The delay (seconds) gives the server time to start if auto_start_server
        was also enabled.
        """
        ollama_cfg = config.get("backend", {}).get("ollama", {})
        if not ollama_cfg.get("warmup_model", False):
            return  # Feature disabled

        model      = ollama_cfg.get("model", "").strip()
        ollama_url = ollama_cfg.get("url", "http://localhost:11434")
        keep_alive = ollama_cfg.get("warmup_keep_alive",
                                    ollama_cfg.get("keep_alive", "120m"))

        if not model:
            logger.warning("[OllamaLifecycle] warmup_model=True but no model configured.")
            return

        logger.info(f"[OllamaLifecycle] Scheduling model warm-up for '{model}' (delay={delay}s)...")
        t = threading.Thread(
            target=self._warmup_bg,
            args=(ollama_url, model, keep_alive, delay),
            daemon=True,
            name="OllamaModelWarmUp"
        )
        t.start()

    def _warmup_bg(self, ollama_url: str, model: str, keep_alive: str, delay: float):
        """Background thread: sends an empty-prompt request to load the model into GPU VRAM."""
        try:
            time.sleep(delay)  # Give server time to come up if auto-started

            # Ensure the server is actually reachable before sending the warm-up
            for attempt in range(_SERVER_READY_TRIES):
                if is_ollama_running(ollama_url, timeout=2):
                    break
                time.sleep(_RETRY_INTERVAL)
            else:
                logger.warning("[OllamaLifecycle] Warm-up aborted: server not reachable.")
                return

            import json
            import urllib.request

            payload = json.dumps({
                "model":      model,
                "prompt":     "",        # Empty prompt = just load, don't generate
                "keep_alive": keep_alive,
                "stream":     True,
            }).encode()

            base = ollama_url.rstrip("/")
            req  = urllib.request.Request(
                f"{base}{_WARMUP_ENDPOINT}",
                data    = payload,
                headers = {"Content-Type": "application/json"},
                method  = "POST",
            )

            t_start = time.time()
            logger.info(f"[OllamaLifecycle] 🔥 Warming up '{model}' (keep_alive={keep_alive})…")

            with urllib.request.urlopen(req, timeout=_WARMUP_TIMEOUT) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    if data.get("done"):
                        elapsed = time.time() - t_start
                        load_ns = data.get("load_duration", 0)
                        load_s  = load_ns / 1e9 if load_ns else elapsed
                        logger.info(
                            f"[OllamaLifecycle] ✅ Model '{model}' loaded into VRAM in "
                            f"{load_s:.1f}s — first response will be instant."
                        )
                        return

            logger.warning(f"[OllamaLifecycle] Warm-up stream ended without 'done' signal.")

        except Exception as e:
            logger.warning(f"[OllamaLifecycle] Model warm-up error (non-fatal): {e}")


# ── Module-level convenience functions ───────────────────────────────────────

def run_ollama_startup_sequence(config: dict):
    """
    Entry point called from the bootstrapper.
    Handles both auto-start and warm-up in the correct order, non-blocking.
    Only runs if backend.type == 'ollama' (or if the flags are explicitly set
    on the ollama sub-config regardless of active backend type).
    """
    backend_type = config.get("backend", {}).get("type", "")
    ollama_cfg   = config.get("backend", {}).get("ollama", {})

    auto_start = ollama_cfg.get("auto_start_server", False)
    warmup     = ollama_cfg.get("warmup_model", False)

    if not (auto_start or warmup):
        return  # Nothing to do

    if backend_type != "ollama" and not (auto_start or warmup):
        return  # Don't touch Ollama if it's not the active backend

    mgr = OllamaLifecycleManager.get_instance()

    if auto_start:
        mgr.maybe_auto_start_server(config)

    if warmup:
        # Delay warm-up by 4s to give auto-start a head start
        warmup_delay = 4.0 if auto_start else 1.5
        mgr.maybe_warmup_model(config, delay=warmup_delay)

