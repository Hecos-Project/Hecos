"""
MODULE: Ollama Lifecycle Manager
DESCRIPTION: Manages automatic startup, model pre-warming, and clean shutdown for the Ollama backend.
             - Auto-starts the Ollama server process if not running (configurable)
             - Pre-warms the configured default model into VRAM at boot (configurable)
             - Gracefully unloads all models and stops the server on Hecos exit (configurable)
             - All operations are non-blocking (daemon threads), fully safe on failure
             - Only activates when backend.type == 'ollama' OR when forced via config flag

Config keys (backend.ollama):
    auto_start_server  : bool  (default: False) — Launch 'ollama serve' if not already running
    warmup_model       : bool  (default: False) — Pre-load model into GPU at Hecos startup
    warmup_keep_alive  : str   (default: '120m') — keep_alive value sent during warm-up
    auto_stop_server   : bool  (default: True)  — Stop Ollama server when Hecos exits
"""

import atexit
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

def _normalize_ollama_base(ollama_url: str) -> str:
    """Returns base URL using 127.0.0.1 instead of localhost to avoid IPv6 ::1 delays on Windows."""
    base = (ollama_url or "http://127.0.0.1:11434").rstrip("/")
    if "localhost" in base:
        return base.replace("localhost", "127.0.0.1")
    return base


def _is_ollama_process(proc) -> bool:
    """
    Returns True if a psutil.Process belongs to Ollama (server, GUI app, or GPU runner).
    Modern Ollama (>= 0.6 / 0.34+) uses 'llama-server.exe' under '.../Ollama/lib/ollama/'
    instead of 'ollama_llama_server.exe'. We verify 'ollama' is in exe/cmdline before matching
    'llama-server' so standalone llama.cpp servers are never touched.
    """
    try:
        pname = (proc.info.get("name") if hasattr(proc, "info") and proc.info else proc.name()) or ""
        pname_l = pname.lower()
        if pname_l in {"ollama.exe", "ollama_llama_server.exe", "ollama app.exe", "ollama"}:
            return True
        if pname_l in {"llama-server.exe", "llama-server"}:
            exe_l = ""
            cmd_l = ""
            try:
                exe_l = (proc.exe() or "").lower()
            except Exception:
                pass
            try:
                cmd_l = " ".join(proc.cmdline() or []).lower()
            except Exception:
                pass
            if "ollama" in exe_l or ".ollama" in cmd_l:
                return True
    except Exception:
        pass
    return False


def reap_orphan_ollama_runners() -> int:
    """
    Terminates orphaned Ollama GPU runner processes ('ollama_llama_server.exe' or
    Ollama's 'llama-server.exe') whose parent 'ollama.exe' process no longer exists.
    Prevents zombie runners from holding GPU VRAM and causing HTTP 500 on next boot.
    """
    reaped = 0
    try:
        import psutil
        for p in psutil.process_iter(["pid", "ppid", "name"]):
            try:
                pname_l = (p.info.get("name") or "").lower()
                if pname_l not in {"ollama_llama_server.exe", "llama-server.exe", "llama-server"}:
                    continue
                if not _is_ollama_process(p):
                    continue
                ppid = p.info.get("ppid") or 0
                parent_alive = False
                if ppid > 0:
                    try:
                        parent = psutil.Process(ppid)
                        parent_name = (parent.name() or "").lower()
                        if parent.is_running() and "ollama" in parent_name:
                            parent_alive = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        parent_alive = False
                if not parent_alive:
                    logger.warning(
                        f"[OllamaLifecycle] Reaping orphaned Ollama GPU runner "
                        f"'{p.info.get('name')}' (PID {p.info['pid']}, dead PPID {ppid})..."
                    )
                    p.kill()
                    reaped += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.debug(f"[OllamaLifecycle] reap_orphan_ollama_runners skipped: {e}")
    return reaped


def resolve_effective_ollama_target(config: dict, session_id: Optional[str] = None) -> tuple:
    """
    Resolves (effective_backend, effective_model, effective_ollama_cfg) by applying
    the active Global Preset (Soul) and ModelManager fallback rules — matching the
    exact model and runner parameters (num_ctx, num_gpu) used by chat inference.
    """
    base_cfg = config or {}
    merged_cfg = base_cfg
    try:
        from hecos.config.session_config_manager import merge_session_config
        merged_cfg = merge_session_config(base_cfg, session_id=session_id) or base_cfg
    except Exception as e:
        logger.debug(f"[OllamaLifecycle] Soul merge skipped during target resolution: {e}")

    base_ollama = base_cfg.get("backend", {}).get("ollama", {}) or {}
    merged_ollama = dict(merged_cfg.get("backend", {}).get("ollama", {}) or {})
    # Preserve lifecycle flags from base config if absent in merged copy
    for flag_key in ("auto_start_server", "auto_stop_server", "warmup_model", "warmup_keep_alive", "binary_path", "url", "keep_alive"):
        if flag_key not in merged_ollama and flag_key in base_ollama:
            merged_ollama[flag_key] = base_ollama[flag_key]

    effective_backend = merged_cfg.get("backend", {}).get("type", "ollama")
    effective_model = merged_ollama.get("model", "")
    try:
        from hecos.app.model_manager import ModelManager
        eb, em = ModelManager.get_effective_model_info(merged_cfg)
        if eb:
            effective_backend = eb
        if eb == "ollama" and em and em != "N/D":
            effective_model = em
    except Exception as e:
        logger.debug(f"[OllamaLifecycle] ModelManager resolution fallback: {e}")
        if effective_backend == "hybrid":
            src = merged_cfg.get("backend", {}).get("active_model_source", "cloud")
            effective_backend = "ollama" if src == "ollama" else src

    return effective_backend, (effective_model or "").strip(), merged_ollama


def _build_warmup_options(ollama_cfg: dict) -> dict:
    """
    Extracts runner-level options (num_gpu, num_ctx) matching params_builder.py.
    Passing identical num_ctx and num_gpu during warm-up prevents Ollama from
    evicting and reloading the runner on the first chat request.
    """
    opts = {}
    for opt_key in ("num_gpu", "num_ctx"):
        val = ollama_cfg.get(opt_key)
        if val is not None and val != "":
            try:
                opts[opt_key] = int(val)
            except (TypeError, ValueError):
                pass
    return opts


def get_loaded_model_status(ollama_url: str, model: str, timeout: float = 2.0) -> Optional[dict]:
    """
    Checks Ollama /api/ps to verify whether `model` is currently resident in memory.
    Returns the matching /api/ps entry dict, or None if not loaded.
    """
    if not model:
        return None
    try:
        import json
        import urllib.request
        base_4 = _normalize_ollama_base(ollama_url)
        req = urllib.request.Request(f"{base_4}/api/ps", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        m_clean = model.replace("ollama/", "", 1).strip()
        m_WithLatest = f"{m_clean}:latest" if ":" not in m_clean else m_clean
        for pm in data.get("models", []):
            pm_name = (pm.get("name") or pm.get("model") or "").strip()
            if pm_name in (m_clean, m_WithLatest):
                return pm
    except Exception:
        pass
    return None


def is_ollama_running(ollama_url: str, timeout: int = _DEFAULT_TIMEOUT) -> bool:
    """Returns True if the Ollama API is reachable and responding."""
    try:
        import urllib.request
        import urllib.error
        base = (ollama_url or "http://127.0.0.1:11434").rstrip("/")
        # Check 127.0.0.1 first to avoid 2s IPv6 ::1 resolution timeouts on Windows
        test_urls = []
        if "localhost" in base:
            test_urls.append(base.replace("localhost", "127.0.0.1") + _OLLAMA_HEALTH_URL)
        test_urls.append(f"{base}{_OLLAMA_HEALTH_URL}")
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
    Emits a clear warning when preferred_path is a directory but contains no Ollama binary.
    """
    if preferred_path and preferred_path.strip():
        p = preferred_path.strip().strip('"').strip("'")
        if os.path.isfile(p):
            return p
        if os.path.isdir(p):
            for candidate in ("ollama app.exe", "ollama.exe"):
                sub = os.path.join(p, candidate)
                if os.path.isfile(sub):
                    logger.info(f"[OllamaLifecycle] Found Ollama in directory: {sub}")
                    return sub
            # Directory exists but no Ollama binary inside — log a clear hint
            logger.warning(
                f"[OllamaLifecycle] ⚠️  binary_path '{p}' is a directory but contains no ollama.exe. "
                f"Please set the FULL PATH to the executable (e.g. C:\\Users\\...\\AppData\\Local\\Programs\\Ollama\\ollama.exe). "
                f"Falling back to auto-detection."
            )
        elif p:
            # Path specified but neither file nor directory — may be a shortcut or broken path
            logger.warning(
                f"[OllamaLifecycle] ⚠️  binary_path '{p}' does not exist. "
                f"Falling back to auto-detection."
            )

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
            logger.info(f"[OllamaLifecycle] Auto-detected Ollama at: {c}")
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
        self._server_stopped = False
        self._warmup_lock = threading.Lock()
        self._warmup_generation = 0
        self._active_warmup_key: Optional[tuple] = None

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
            reap_orphan_ollama_runners()
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
            # Clean up any orphaned GPU runners from a prior killed session before spawning
            reap_orphan_ollama_runners()

            exe_lower = exe.lower()
            is_gui_app = "ollama app.exe" in exe_lower

            # If user selected 'ollama app.exe', launch it directly without arguments.
            # If CLI binary 'ollama.exe', launch with 'serve' argument.
            cmd = [exe] if is_gui_app else [exe, "serve"]

            kwargs = dict(
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            # On Windows:
            # - For GUI app: CREATE_NEW_PROCESS_GROUP
            # - For CLI daemon: CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW (no console flash)
            # NOTE: Never combine DETACHED_PROCESS with CREATE_NO_WINDOW, as Windows
            # explicitly ignores CREATE_NO_WINDOW when DETACHED_PROCESS is set.
            if os.name == "nt":
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                CREATE_NO_WINDOW = 0x08000000
                if is_gui_app:
                    kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
                else:
                    kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
            else:
                kwargs["close_fds"] = True

            self._server_proc = subprocess.Popen(cmd, **kwargs)
            self._started_by_us = True
            self._server_stopped = False
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

    def maybe_warmup_model(
        self,
        config: dict,
        delay: float = 3.0,
        session_id: Optional[str] = None,
        force_model: Optional[str] = None,
    ):
        """
        If backend.ollama.warmup_model is True, send an empty-prompt request
        to Ollama to force the effective configured model (including active Global Preset / Soul
        overrides and runner options num_ctx + num_gpu) into VRAM immediately.
        Returns immediately — actual loading happens in a daemon thread.
        """
        effective_backend, resolved_model, ollama_cfg = resolve_effective_ollama_target(
            config, session_id=session_id
        )
        if not ollama_cfg.get("warmup_model", False) and not force_model:
            return  # Feature disabled

        if effective_backend != "ollama" and not force_model:
            logger.info(
                f"[OllamaLifecycle] Effective backend is '{effective_backend}' — skipping Ollama model warm-up."
            )
            return

        model = (force_model or resolved_model or ollama_cfg.get("model", "")).strip()
        ollama_url = ollama_cfg.get("url", "http://localhost:11434")
        keep_alive = ollama_cfg.get("warmup_keep_alive", ollama_cfg.get("keep_alive", "120m"))
        warmup_options = _build_warmup_options(ollama_cfg)

        if not model:
            logger.warning("[OllamaLifecycle] warmup_model=True but no model configured.")
            return

        warmup_key = (model, warmup_options.get("num_ctx"), warmup_options.get("num_gpu"))
        with self._warmup_lock:
            if self._active_warmup_key == warmup_key:
                logger.debug(f"[OllamaLifecycle] Warm-up already in progress for {warmup_key} — skipping duplicate.")
                return
            self._warmup_generation += 1
            gen_id = self._warmup_generation
            self._active_warmup_key = warmup_key

        logger.info(
            f"[OllamaLifecycle] Scheduling model warm-up for '{model}' "
            f"(options={warmup_options}, delay={delay}s)..."
        )
        t = threading.Thread(
            target=self._warmup_bg,
            args=(ollama_url, model, keep_alive, warmup_options, delay, gen_id, warmup_key),
            daemon=True,
            name="OllamaModelWarmUp"
        )
        t.start()

    # ── Graceful shutdown ──────────────────────────────────────────────────────

    def unload_all_models(self, ollama_url: str, timeout: int = 10):
        """
        Asks Ollama to evict every loaded model from GPU VRAM by sending
        keep_alive=0 to /api/generate for each model currently listed by /api/ps.

        This is a best-effort call: any failure is silently logged.
        """
        try:
            import json
            import urllib.request
            import urllib.error

            base = (ollama_url or "http://127.0.0.1:11434").rstrip("/")
            base_4 = _normalize_ollama_base(base)
            candidates = [base_4] if base_4 == base else [base_4, base]

            # Retrieve currently-loaded models from /api/ps
            loaded_models = []
            for ps_base in candidates:
                try:
                    req = urllib.request.Request(f"{ps_base}/api/ps", method="GET")
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        data = json.loads(resp.read())
                        loaded_models = [m["name"] for m in data.get("models", [])]
                    break
                except Exception:
                    pass

            if not loaded_models:
                logger.info("[OllamaLifecycle] No models loaded in VRAM — nothing to unload.")
                return

            logger.info(f"[OllamaLifecycle] Unloading {len(loaded_models)} model(s) from VRAM: {loaded_models}")

            for model in loaded_models:
                payload = json.dumps({
                    "model":      model,
                    "prompt":     "",
                    "keep_alive": 0,     # 0 = unload immediately
                    "stream":     False,
                }).encode()
                for gen_base in candidates:
                    try:
                        req = urllib.request.Request(
                            f"{gen_base}/api/generate",
                            data    = payload,
                            headers = {"Content-Type": "application/json"},
                            method  = "POST",
                        )
                        with urllib.request.urlopen(req, timeout=timeout) as _:
                            pass
                        logger.info(f"[OllamaLifecycle] ✅ Model '{model}' unloaded from VRAM.")
                        break
                    except Exception as e:
                        logger.debug(f"[OllamaLifecycle] Could not unload '{model}' via {gen_base}: {e}")

        except Exception as e:
            logger.warning(f"[OllamaLifecycle] unload_all_models error (non-fatal): {e}")

    def stop_server(self):
        """
        Terminates the Ollama server process and all child GPU runners ('ollama_llama_server.exe'
        and modern Ollama 'llama-server.exe'), ensuring GPU VRAM is completely released.
        """
        if getattr(self, "_server_stopped", False):
            return
        self._server_stopped = True
        with self._warmup_lock:
            self._warmup_generation += 1
            self._active_warmup_key = None
        try:
            # 1. Pure-Python psutil termination (fast, silent, catches renamed llama-server.exe too)
            killed_psutil = 0
            try:
                import psutil
                procs_to_wait = []
                for p in psutil.process_iter(["pid", "name"]):
                    try:
                        if _is_ollama_process(p):
                            p.kill()
                            procs_to_wait.append(p)
                            killed_psutil += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if procs_to_wait:
                    psutil.wait_procs(procs_to_wait, timeout=3)
                if killed_psutil > 0:
                    logger.info(f"[OllamaLifecycle] ✅ Terminated {killed_psutil} Ollama process(es) silently via psutil.")
            except ImportError:
                pass

            if os.name == "nt":
                # Fallback on Windows if any named Ollama executables remain: taskkill /F /T with CREATE_NO_WINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
                for exe_name in ("ollama.exe", "ollama_llama_server.exe", "ollama app.exe"):
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/IM", exe_name],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=5,
                            creationflags=creationflags,
                        )
                    except Exception:
                        pass
                logger.info("[OllamaLifecycle] ✅ Ollama cleanup confirmed.")
            else:
                # POSIX fallback: terminate the process we spawned
                if self._server_proc and self._server_proc.poll() is None:
                    self._server_proc.terminate()
                    try:
                        self._server_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._server_proc.kill()
                    logger.info("[OllamaLifecycle] ✅ Ollama process terminated (POSIX).")
                else:
                    logger.info("[OllamaLifecycle] Ollama process already gone or was not started by us.")
        except Exception as e:
            logger.warning(f"[OllamaLifecycle] stop_server error (non-fatal): {e}")

    def on_application_exit(self, config: Optional[dict] = None):
        """
        Called at Hecos shutdown to cleanly stop Ollama.
        Respects the auto_stop_server config flag (default: True).
        Steps:
          1. Unload all models from VRAM via keep_alive=0
          2. Kill the Ollama process tree
        """
        try:
            cfg = config or {}
            ollama_cfg = cfg.get("backend", {}).get("ollama", {})
            auto_stop  = ollama_cfg.get("auto_stop_server", True)

            if not auto_stop:
                logger.info("[OllamaLifecycle] auto_stop_server=False — leaving Ollama running.")
                return

            ollama_url = ollama_cfg.get("url", "http://localhost:11434")

            # Only act if Ollama was started by us OR is actually reachable
            if not self._started_by_us and not is_ollama_running(ollama_url, timeout=2):
                reap_orphan_ollama_runners()
                logger.info("[OllamaLifecycle] Ollama was not started by Hecos and is not running — nothing to stop.")
                return

            logger.info("[OllamaLifecycle] Hecos shutting down — unloading models and stopping Ollama...")
            self.unload_all_models(ollama_url, timeout=8)
            self.stop_server()

        except Exception as e:
            logger.warning(f"[OllamaLifecycle] on_application_exit error (non-fatal): {e}")


    def _warmup_bg(
        self,
        ollama_url: str,
        model: str,
        keep_alive: str,
        warmup_options: dict,
        delay: float,
        gen_id: int,
        warmup_key: tuple,
    ):
        """
        Background thread: loads the effective Ollama model into GPU VRAM/RAM with
        identical runner options (num_ctx, num_gpu) used by chat inference, retries on
        transient startup HTTP 500 / CUDA contention, and verifies residency via /api/ps.
        """
        try:
            if delay > 0:
                time.sleep(delay)

            with self._warmup_lock:
                if gen_id != self._warmup_generation:
                    return

            # Ensure the server is actually reachable before sending the warm-up
            for _ in range(_SERVER_READY_TRIES):
                with self._warmup_lock:
                    if gen_id != self._warmup_generation:
                        return
                if is_ollama_running(ollama_url, timeout=2):
                    break
                time.sleep(_RETRY_INTERVAL)
            else:
                logger.warning("[OllamaLifecycle] Warm-up aborted: server not reachable.")
                return

            import json
            import urllib.request
            import urllib.error

            base_4 = _normalize_ollama_base(ollama_url)
            expected_ctx = warmup_options.get("num_ctx")

            # Fast check: if already resident in /api/ps with matching context_length, just refresh keep_alive
            existing = get_loaded_model_status(base_4, model, timeout=2.0)
            if existing and (not expected_ctx or existing.get("context_length") == expected_ctx):
                sz_mb = (existing.get("size") or 0) / (1024 * 1024)
                vr_mb = (existing.get("size_vram") or 0) / (1024 * 1024)
                pct = (vr_mb / sz_mb * 100) if sz_mb > 0 else 0
                logger.info(
                    f"[OllamaLifecycle] ✅ Model '{model}' already resident in memory "
                    f"(VRAM: {vr_mb:.0f}/{sz_mb:.0f} MB [{pct:.0f}%], ctx={existing.get('context_length')}) "
                    f"— refreshing keep_alive={keep_alive}."
                )

            req_body = {
                "model":      model,
                "prompt":     "",        # Empty prompt = load model runner without generating tokens
                "keep_alive": keep_alive,
                "stream":     False,
            }
            if warmup_options:
                req_body["options"] = warmup_options
            payload = json.dumps(req_body).encode("utf-8")

            max_attempts = 3
            retry_delays = (3.0, 5.0)
            for attempt_idx in range(max_attempts):
                with self._warmup_lock:
                    if gen_id != self._warmup_generation:
                        return

                reap_orphan_ollama_runners()
                req = urllib.request.Request(
                    f"{base_4}{_WARMUP_ENDPOINT}",
                    data    = payload,
                    headers = {"Content-Type": "application/json"},
                    method  = "POST",
                )

                t_start = time.time()
                attempt_tag = f" (attempt {attempt_idx + 1}/{max_attempts})" if attempt_idx > 0 else ""
                logger.info(
                    f"[OllamaLifecycle] 🔥 Warming up '{model}' "
                    f"(keep_alive={keep_alive}, options={warmup_options}){attempt_tag}…"
                )

                try:
                    with urllib.request.urlopen(req, timeout=_WARMUP_TIMEOUT) as resp:
                        raw = resp.read().decode("utf-8", errors="replace").strip()
                    data = json.loads(raw) if raw else {}
                    elapsed = time.time() - t_start
                    load_ns = data.get("load_duration", 0)
                    load_s  = load_ns / 1e9 if load_ns else elapsed

                    ps_entry = get_loaded_model_status(base_4, model, timeout=2.5)
                    if ps_entry:
                        sz_mb = (ps_entry.get("size") or 0) / (1024 * 1024)
                        vr_mb = (ps_entry.get("size_vram") or 0) / (1024 * 1024)
                        pct = (vr_mb / sz_mb * 100) if sz_mb > 0 else 0
                        ctx_len = ps_entry.get("context_length", expected_ctx or "default")
                        logger.info(
                            f"[OllamaLifecycle] ✅ Model '{model}' preloaded in {load_s:.1f}s — "
                            f"resident VRAM: {vr_mb:.0f}/{sz_mb:.0f} MB ({pct:.0f}%), ctx={ctx_len}. "
                            f"First response will be instant."
                        )
                        return

                    # /api/generate returned 200 but /api/ps did not show the model yet — retry if attempts remain
                    if attempt_idx + 1 < max_attempts:
                        logger.warning(
                            f"[OllamaLifecycle] Warm-up call returned OK for '{model}' but /api/ps did not confirm "
                            f"residency yet; retrying in {retry_delays[attempt_idx]:.1f}s..."
                        )
                        time.sleep(retry_delays[attempt_idx])
                        continue
                    logger.info(
                        f"[OllamaLifecycle] ✅ Warm-up call completed for '{model}' in {load_s:.1f}s."
                    )
                    return

                except Exception as req_err:
                    err_detail = str(req_err)
                    if isinstance(req_err, urllib.error.HTTPError):
                        try:
                            err_body = req_err.read().decode("utf-8", errors="replace").strip()
                            if err_body:
                                err_detail = f"{req_err} — {err_body[:240]}"
                        except Exception:
                            pass
                    if attempt_idx + 1 < max_attempts:
                        wait_s = retry_delays[attempt_idx]
                        logger.warning(
                            f"[OllamaLifecycle] Warm-up transient error on attempt {attempt_idx + 1}/{max_attempts}: "
                            f"{err_detail}. Retrying in {wait_s:.1f}s..."
                        )
                        time.sleep(wait_s)
                    else:
                        logger.warning(
                            f"[OllamaLifecycle] Model warm-up failed after {max_attempts} attempts (non-fatal): {err_detail}"
                        )
        except Exception as e:
            logger.warning(f"[OllamaLifecycle] Model warm-up error (non-fatal): {e}")
        finally:
            with self._warmup_lock:
                if self._active_warmup_key == warmup_key:
                    self._active_warmup_key = None


# ── Module-level convenience functions ───────────────────────────────────────

def run_ollama_startup_sequence(config: dict):
    """
    Entry point called from the bootstrapper and standalone WebUI server.
    Resolves the effective backend and model (including active Global Preset / Soul)
    and handles auto-start + GPU model warm-up non-blockingly when Ollama is active.
    """
    effective_backend, effective_model, ollama_cfg = resolve_effective_ollama_target(config)

    auto_start = ollama_cfg.get("auto_start_server", False)
    warmup     = ollama_cfg.get("warmup_model", False)

    if not (auto_start or warmup):
        return  # Nothing to do

    if effective_backend != "ollama":
        logger.info(
            f"[OllamaLifecycle] Active effective backend is '{effective_backend}' "
            f"— skipping Ollama boot auto-start/warm-up."
        )
        return

    mgr = OllamaLifecycleManager.get_instance()
    ollama_url = ollama_cfg.get("url", "http://localhost:11434")
    already_up = is_ollama_running(ollama_url, timeout=2)

    if auto_start and not already_up:
        mgr.maybe_auto_start_server(config)

    if warmup:
        # Stagger slightly after TTS CUDA init (2s) when auto-starting so GPU allocators don't collide
        warmup_delay = 4.5 if (auto_start and not already_up) else 2.5
        logger.info(
            f"[OllamaLifecycle] Boot sequence: effective model='{effective_model}', "
            f"server_already_up={already_up}, warmup_delay={warmup_delay}s."
        )
        mgr.maybe_warmup_model(config, delay=warmup_delay)


