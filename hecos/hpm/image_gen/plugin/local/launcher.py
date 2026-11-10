"""
SwarmUI Process & Lifecycle Manager (launcher.py)
Handles installation detection, automatic background startup, health polling,
and real-time trace emission for Hecos chat and WebUI.
"""

import os
import sys
import time
import socket
import logging
import threading
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

from .health import check_backend_status, STATUS_ONLINE, STATUS_AUTH_REQUIRED

try:
    from hecos_sdk import LOGS_DIR
except ImportError:
    # Fallback to local logs directory under hecos/logs
    LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs"))

logger = logging.getLogger("IMAGE_GEN.SwarmUILauncher")


def log_info(msg: str) -> None:
    logger.info(f"[SwarmUILauncher] {msg}")


def log_debug(msg: str) -> None:
    logger.debug(f"[SwarmUILauncher] {msg}")


def log_warn(msg: str) -> None:
    logger.warning(f"[SwarmUILauncher] {msg}")


def log_error(msg: str) -> None:
    logger.error(f"[SwarmUILauncher] {msg}")


def _emit_trace(msg: str, level: str = "info") -> None:
    """
    Emit real-time status to the agent tracer (visible in Hecos UI thought/trace box).
    Fails silently if AgentTracer is unavailable.
    """
    try:
        from hecos.core.agent.traces import AgentTracer
        # AgentTracer.emit accepts (source, message, level)
        AgentTracer.emit(None, msg, level=level)
    except Exception:
        pass


def _emit_action_box(title: str, command: str, output: str) -> None:
    """Emit an Action Box in the chat trajectory traces."""
    try:
        from hecos.core.agent.traces import AgentTracer
        AgentTracer.action_box(
            source=None,
            title=title,
            command=command,
            output=output,
        )
    except Exception:
        pass


# ── Typed Exceptions for UI & Retry Blocking ──────────────────────────────────

class SwarmUIBackendFailure(RuntimeError):
    """Base exception for non-retriable SwarmUI lifecycle/connectivity failures."""
    def __init__(self, message: str, status_code: str = "ERROR", user_notice: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.user_notice = user_notice or message


class SwarmUINotInstalledError(SwarmUIBackendFailure):
    """Raised when SwarmUI is not running and no local installation is found."""
    pass


class SwarmUINotRunningError(SwarmUIBackendFailure):
    """Raised when SwarmUI is installed locally but is offline and auto-start is disabled."""
    pass


class SwarmUIStartupError(SwarmUIBackendFailure):
    """Raised when auto-start was attempted but failed (timeout, bad exit code, etc.)."""
    pass


# ── Installation Discovery ───────────────────────────────────────────────────

def _is_valid_swarm_dir(path: Path) -> bool:
    """Return True if `path` looks like a valid SwarmUI installation root."""
    if not path.is_dir():
        return False

    # Signature 1: launch script
    if sys.platform == "win32":
        if (path / "launch-windows.bat").is_file():
            return True
    else:
        if (path / "launch-linux.sh").is_file() or (path / "launch-macos.sh").is_file():
            return True

    # Signature 2: compiled binaries or entry point
    exe_candidates = [
        path / "src" / "bin" / "live_release" / "SwarmUI.exe",
        path / "src" / "bin" / "live_release" / "SwarmUI",
        path / "SwarmUI.exe",
    ]
    for exe in exe_candidates:
        if exe.is_file():
            return True

    # Signature 3: SwarmUI core structure (src/Core + Data or Models)
    if (path / "src" / "Core").is_dir() and ((path / "Data").is_dir() or (path / "Models").is_dir()):
        return True

    return False


def _get_search_roots() -> list[Path]:
    """Return ordered list of candidate SwarmUI installation directories."""
    candidates = []

    # 1. Standard Windows root drives
    if sys.platform == "win32":
        for drive in ("C", "D", "E", "F"):
            candidates.append(Path(f"{drive}:/SwarmUI"))
            candidates.append(Path(f"{drive}:/AI/SwarmUI"))
            candidates.append(Path(f"{drive}:/StableDiffusion/SwarmUI"))

        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            up = Path(user_profile)
            candidates.append(up / "SwarmUI")
            candidates.append(up / "Desktop" / "SwarmUI")
            candidates.append(up / "Downloads" / "SwarmUI")
            candidates.append(up / "AppData" / "Local" / "SwarmUI")

        prog_files = os.environ.get("ProgramFiles")
        if prog_files:
            candidates.append(Path(prog_files) / "SwarmUI")

    else:
        home = Path.home()
        candidates.extend([
            home / "SwarmUI",
            home / "swarmui",
            home / "ai" / "SwarmUI",
            Path("/opt/SwarmUI"),
            Path("/opt/swarmui"),
            Path("/usr/local/SwarmUI"),
        ])

    # 2. Workspace / Hecos sibling search
    try:
        hecos_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        candidates.append(hecos_root / "SwarmUI")
        candidates.append(hecos_root.parent / "SwarmUI")
    except Exception:
        pass

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        norm = str(c.resolve()) if c.exists() else str(c)
        if norm.lower() not in seen:
            seen.add(norm.lower())
            unique.append(c)

    return unique


def find_swarmui_installation(configured_path: str = "") -> Optional[str]:
    """
    Locate the SwarmUI installation directory on disk.
    Priority:
      1. Explicit `install_path` configured in image_gen.toml
      2. Environment variable SWARMUI_PATH / SWARMUI_DIR
      3. Standard well-known paths on disk (C:\SwarmUI, User Profile, etc.)
    Returns the absolute path string if found, or None.
    """
    # 1. Explicit configured path
    if configured_path and configured_path.strip():
        p = Path(configured_path.strip()).expanduser().resolve()
        if _is_valid_swarm_dir(p):
            log_debug(f"Found SwarmUI at configured path: {p}")
            return str(p)
        else:
            log_warn(f"Configured SwarmUI path is invalid: '{configured_path}'")

    # 2. Environment variables
    for env_var in ("SWARMUI_PATH", "SWARMUI_DIR", "SWARM_DIR"):
        val = os.environ.get(env_var, "").strip()
        if val:
            p = Path(val).expanduser().resolve()
            if _is_valid_swarm_dir(p):
                log_debug(f"Found SwarmUI via env var {env_var}: {p}")
                return str(p)

    # 3. Standard search roots
    for candidate in _get_search_roots():
        try:
            if candidate.is_dir() and _is_valid_swarm_dir(candidate):
                log_info(f"Auto-discovered SwarmUI installation at: {candidate}")
                return str(candidate.resolve())
        except Exception:
            continue

    return None


def _build_launch_command(install_dir: str, port: int = 7801) -> Tuple[Optional[list[str]], str]:
    """
    Build the subprocess command list and display string for launching SwarmUI.
    Uses launch-windows.bat (or direct executable) on Windows, launch-linux.sh on Linux.
    """
    root = Path(install_dir)

    if sys.platform == "win32":
        bat_path = root / "launch-windows.bat"
        exe_path = root / "src" / "bin" / "live_release" / "SwarmUI.exe"

        # If batch file exists, use cmd.exe /c
        if bat_path.is_file():
            # Pass --launch_mode none so SwarmUI does not open browser tabs
            cmd = ["cmd.exe", "/c", str(bat_path), "--launch_mode", "none", "--port", str(port)]
            return cmd, f"{bat_path} --launch_mode none --port {port}"

        if exe_path.is_file():
            cmd = [str(exe_path), "--launch_mode", "none", "--port", str(port)]
            return cmd, f"{exe_path} --launch_mode none --port {port}"

    else:
        exe_linux = root / "src" / "bin" / "live_release" / "SwarmUI"
        sh_path = root / "launch-linux.sh"
        mac_path = root / "launch-macos.sh"

        if exe_linux.is_file():
            cmd = [str(exe_linux), "--launch_mode", "none", "--port", str(port)]
            return cmd, f"{exe_linux} --launch_mode none --port {port}"
        if sh_path.is_file():
            cmd = ["bash", str(sh_path), "--launch_mode", "none", "--port", str(port)]
            return cmd, f"bash {sh_path} --launch_mode none --port {port}"
        if mac_path.is_file():
            cmd = ["bash", str(mac_path), "--launch_mode", "none", "--port", str(port)]
            return cmd, f"bash {mac_path} --launch_mode none --port {port}"

    return None, "No executable or startup script found in SwarmUI directory."


# ── Lifecycle Manager Singleton ───────────────────────────────────────────────

class SwarmUILauncher:
    """
    Singleton process manager that checks if SwarmUI is installed & running,
    and automatically starts it on-demand when needed.
    """
    _instance: Optional["SwarmUILauncher"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._is_starting: bool = False
        self._last_error: str = ""
        self._log_path: str = os.path.join(LOGS_DIR, "swarmui_autostart.log")

    @classmethod
    def get_instance(cls) -> "SwarmUILauncher":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = SwarmUILauncher()
        return cls._instance

    find_swarmui_installation = staticmethod(find_swarmui_installation)

    @staticmethod
    def _parse_url(local_cfg: dict) -> Tuple[str, str, int]:
        raw_url = local_cfg.get("url", "http://localhost:7801")
        parsed = urlparse(raw_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 7801)
        clean_url = f"{parsed.scheme or 'http'}://{host}:{port}"
        return clean_url, host, port

    @staticmethod
    def _is_local_host(host: str) -> bool:
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return True
        try:
            return socket.gethostbyname(host) == "127.0.0.1"
        except Exception:
            return False

    def check_status(self, local_cfg: Optional[dict] = None) -> dict:
        """
        Return full diagnostic status dictionary for UI and health checks:
        {
            "ok": bool,
            "running": bool,
            "starting": bool,
            "installed": bool,
            "install_path": str,
            "auto_start": bool,
            "url": str,
            "version": str,
            "latency_ms": int,
            "status_code": "ONLINE" | "STARTING" | "OFFLINE_INSTALLED" | "NOT_INSTALLED" | "AUTH_REQUIRED",
            "status_text": str,
            "error": str | None
        }
        """
        if local_cfg is None:
            local_cfg = {}

        url, host, port = self._parse_url(local_cfg)
        configured_path = local_cfg.get("install_path", "")
        auto_start = bool(local_cfg.get("auto_start", True))

        install_dir = find_swarmui_installation(configured_path)
        installed = install_dir is not None

        health = check_backend_status(url, timeout=4)
        status = health.get("status")

        if status == STATUS_ONLINE:
            return {
                "ok": True,
                "running": True,
                "starting": False,
                "installed": True,
                "install_path": install_dir or configured_path or "(External instance active)",
                "auto_start": auto_start,
                "url": url,
                "version": health.get("version") or "Online",
                "latency_ms": health.get("latency_ms", 0),
                "status_code": "ONLINE",
                "status_text": "SwarmUI Online",
                "error": None,
            }

        if status == STATUS_AUTH_REQUIRED:
            return {
                "ok": False,
                "running": True,
                "starting": False,
                "installed": True,
                "install_path": install_dir or configured_path,
                "auto_start": auto_start,
                "url": url,
                "version": "",
                "latency_ms": health.get("latency_ms", 0),
                "status_code": "AUTH_REQUIRED",
                "status_text": "SwarmUI requires authentication (auth_token)",
                "error": health.get("error"),
            }

        if self._is_starting:
            return {
                "ok": False,
                "running": False,
                "starting": True,
                "installed": installed,
                "install_path": install_dir or configured_path,
                "auto_start": auto_start,
                "url": url,
                "version": "",
                "latency_ms": 0,
                "status_code": "STARTING",
                "status_text": "SwarmUI startup in progress...",
                "error": None,
            }

        if not installed:
            searched_hint = configured_path if configured_path else "C:\SwarmUI"
            return {
                "ok": False,
                "running": False,
                "starting": False,
                "installed": False,
                "install_path": "",
                "auto_start": auto_start,
                "url": url,
                "version": "",
                "latency_ms": 0,
                "status_code": "NOT_INSTALLED",
                "status_text": "SwarmUI not installed / not found",
                "error": (
                    f"SwarmUI is not active on {url} and no local installation was found "
                    f"(checked path: '{searched_hint}'). Install SwarmUI or configure the correct path."
                ),
            }

        return {
            "ok": False,
            "running": False,
            "starting": False,
            "installed": True,
            "install_path": install_dir,
            "auto_start": auto_start,
            "url": url,
            "version": "",
            "latency_ms": 0,
            "status_code": "OFFLINE_INSTALLED",
            "status_text": f"SwarmUI offline (installed at {install_dir})",
            "error": (
                f"SwarmUI is installed at '{install_dir}' but is currently offline ({url} is not responding). "
                + ("It will be automatically launched on the next generation." if auto_start else "Auto-start is disabled: open it manually or enable Auto-Start.")
            ),
        }

    def ensure_running(self, local_cfg: Optional[dict] = None, force_start: bool = False) -> Tuple[bool, str, str]:
        """
        Ensure SwarmUI is running and reachable on `url`.
        If offline:
          - Checks if SwarmUI is installed locally.
          - If installed and auto_start=True (or force_start=True), launches it and waits until ready.
          - Emits clear real-time traces via AgentTracer and debug log at every step.

        Returns:
            Tuple (ok: bool, status_code: str, diagnostic_message: str)
        """
        if local_cfg is None:
            local_cfg = {}

        url, host, port = self._parse_url(local_cfg)
        configured_path = local_cfg.get("install_path", "")
        auto_start = bool(local_cfg.get("auto_start", True))
        startup_timeout = int(local_cfg.get("startup_timeout", 90) or 90)

        # 1. Quick check if already online
        _emit_trace(f"🔍 Checking SwarmUI status on {url}...", level="info")
        health = check_backend_status(url, timeout=4)
        if health.get("status") == STATUS_ONLINE:
            ver = health.get("version")
            ver_str = f" (v{ver})" if ver else ""
            _emit_trace(f"✅ SwarmUI active on {url}{ver_str} ({health.get('latency_ms', 0)}ms).", level="info")
            return True, "ONLINE", f"SwarmUI active on {url}{ver_str}."

        if health.get("status") == STATUS_AUTH_REQUIRED:
            msg = (
                f"⚠️ **SwarmUI requires authentication** on `{url}`.\n"
                "Set a valid `auth_token` in the `[image_gen.local]` section of `image_gen.toml`."
            )
            _emit_trace(msg, level="error")
            return False, "AUTH_REQUIRED", msg

        # 2. If pointing to a remote machine (not localhost), we cannot auto-launch it locally
        if not self._is_local_host(host):
            msg = (
                f"❌ **Remote SwarmUI unreachable** on `{url}`.\n"
                "Verify that the remote SwarmUI server is powered on and accessible over the network."
            )
            _emit_trace(msg, level="error")
            return False, "REMOTE_OFFLINE", msg

        # 3. Check local installation on disk
        install_dir = find_swarmui_installation(configured_path)
        if not install_dir:
            searched_info = f"configured path `{configured_path}`" if configured_path else "`C:\\SwarmUI`, `D:\\SwarmUI`, `%USERPROFILE%\\SwarmUI`"
            msg = (
                f"❌ **SwarmUI is neither installed nor active** (`{url}` is not responding).\n"
                f"- **Checked paths:** {searched_info}\n"
                f"- **Resolution:** Install SwarmUI (e.g. in `C:\\SwarmUI`), configure the correct path in the **Image Gen → SwarmUI Local Backend** panel, or enable Cloud providers in Image Gen settings."
            )
            _emit_trace(
                f"SwarmUI is not active on {url} and not found on disk ({searched_info}).",
                level="error",
            )
            _emit_action_box(
                "IMAGE_GEN — SwarmUI Check",
                f"check_installation({configured_path or 'auto'})",
                f"ERROR: SwarmUI is not running on {url} and no installation was found in {searched_info}.",
            )
            return False, "NOT_INSTALLED", msg

        # 4. SwarmUI IS installed, check if auto_start is enabled
        if not auto_start and not force_start:
            msg = (
                f"⚠️ **SwarmUI is offline** (`{url}` unreachable).\n"
                f"- **Detected installation:** `{install_dir}`\n"
                f"- **Status:** The local server is closed and **Auto-Start SwarmUI** is disabled.\n"
                f"- **Resolution:** Start SwarmUI manually, click **Start SwarmUI** in the Image Gen settings panel, or enable auto-start."
            )
            _emit_trace(
                f"SwarmUI is installed at '{install_dir}' but is offline (Auto-Start disabled).",
                level="error",
            )
            _emit_action_box(
                "IMAGE_GEN — SwarmUI Offline",
                f"connect({url})",
                f"WARNING: SwarmUI found at '{install_dir}' but server is not running and auto_start=False.",
            )
            return False, "OFFLINE_CLOSED", msg

        # 5. Auto-Start SwarmUI in background and wait for readiness
        with self._lock:
            # Double-check inside lock in case another thread just started it
            health_recheck = check_backend_status(url, timeout=3)
            if health_recheck.get("status") == STATUS_ONLINE:
                return True, "ONLINE", f"SwarmUI active on {url}."

            cmd, cmd_display = _build_launch_command(install_dir, port=port)
            if not cmd:
                msg = (
                    f"❌ **Cannot launch SwarmUI from `{install_dir}`**.\n"
                    f"- **Details:** {cmd_display}\n"
                    f"- **Resolution:** Verify that the SwarmUI installation at `{install_dir}` is complete (`launch-windows.bat` or `src\\bin\\live_release\\SwarmUI.exe`)."
                )
                _emit_trace(f"Cannot launch SwarmUI: {cmd_display}", level="error")
                return False, "START_FAILED", msg

            self._is_starting = True
            try:
                _emit_trace(
                    f"🚀 SwarmUI is offline. Auto-launching from '{install_dir}' on {url}...",
                    level="tool",
                )
                os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

                # Prepare environment (ensure dotnet is in PATH on Windows as launch-windows.bat does)
                env = os.environ.copy()
                if sys.platform == "win32":
                    dotnet_dir = r"C:\Program Files\dotnet"
                    if os.path.isdir(dotnet_dir) and dotnet_dir.lower() not in env.get("PATH", "").lower():
                        env["PATH"] = f"{dotnet_dir};{env.get('PATH', '')}"
                env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
                env["ASPNETCORE_ENVIRONMENT"] = "Production"
                env["DOTNET_CLI_UI_LANGUAGE"] = "en"

                # Spawn only if we don't already have a live child process starting up
                if self._proc is None or self._proc.poll() is not None:
                    log_file = open(self._log_path, "a", encoding="utf-8", errors="replace")
                    log_file.write(
                        f"\n{'='*60}\n"
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting SwarmUI: {cmd_display}\n"
                        f"Working directory: {install_dir}\n"
                        f"{'='*60}\n"
                    )
                    log_file.flush()

                    creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
                    self._proc = subprocess.Popen(
                        cmd,
                        cwd=install_dir,
                        env=env,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        creationflags=creationflags,
                    )

                start_ts = time.time()
                last_progress_log = start_ts

                while (time.time() - start_ts) < startup_timeout:
                    time.sleep(2.0)
                    elapsed = int(time.time() - start_ts)

                    # Check if the server is now responding
                    poll_health = check_backend_status(url, timeout=3)
                    if poll_health.get("status") == STATUS_ONLINE:
                        ver = poll_health.get("version")
                        ver_str = f" (v{ver})" if ver else ""
                        success_msg = f"✨ SwarmUI automatically started and ready on {url}{ver_str} (in {elapsed}s)!"
                        _emit_trace(success_msg, level="success")
                        _emit_action_box(
                            "IMAGE_GEN — SwarmUI Auto-Start",
                            cmd_display,
                            f"SUCCESS: SwarmUI started from '{install_dir}' and is listening on {url} after {elapsed}s.",
                        )
                        return True, "STARTED", success_msg

                    # Check if the spawned process crashed/exited prematurely
                    if self._proc is not None and self._proc.poll() is not None:
                        exit_code = self._proc.returncode
                        # Wait 1s and check port one last time in case launcher spawned a detached child
                        time.sleep(1.0)
                        if check_backend_status(url, timeout=2).get("status") == STATUS_ONLINE:
                            _emit_trace(f"✨ SwarmUI started and ready on {url}!", level="success")
                            return True, "STARTED", f"SwarmUI active on {url}."

                        tail = self._read_log_tail(10)
                        tail_block = f"\n- **Last log lines (`swarmui_autostart.log`):**\n```\n{tail}\n```" if tail else ""
                        msg = (
                            f"❌ **SwarmUI failed to launch: process exited during startup** (exit code: `{exit_code}`).\n"
                            f"- **Path:** `{install_dir}`\n"
                            f"- **Expected URL:** `{url}`"
                            f"{tail_block}\n"
                            f"- **Resolution:** Try launching `{install_dir}\\launch-windows.bat` manually to check for .NET or GPU driver errors."
                        )
                        self._last_error = msg
                        _emit_trace(
                            f"SwarmUI terminated prematurely during startup (exit code {exit_code}).",
                            level="error",
                        )
                        _emit_action_box(
                            "IMAGE_GEN — SwarmUI Startup Failed",
                            cmd_display,
                            f"Process exited with code {exit_code}.\n{tail}",
                        )
                        return False, "START_FAILED", msg

                    # Emit periodic progress every 6 seconds
                    if (time.time() - last_progress_log) >= 6.0:
                        last_progress_log = time.time()
                        _emit_trace(
                            f"⏳ Waiting for SwarmUI to start on {url}... ({elapsed}s / {startup_timeout}s)",
                            level="info",
                        )

                # Timeout reached
                tail = self._read_log_tail(10)
                tail_block = f"\n- **Last log lines (`swarmui_autostart.log`):**\n```\n{tail}\n```" if tail else ""
                msg = (
                    f"❌ **SwarmUI startup timeout:** the process was launched from `{install_dir}`, "
                    f"but did not respond on `{url}` within **{startup_timeout} seconds**.\n"
                    f"{tail_block}\n"
                    f"- **Resolution:** SwarmUI may need additional time to compile or initialize backends on first run. "
                    f"Check `hecos/logs/swarmui_autostart.log` or try again shortly."
                )
                self._last_error = msg
                _emit_trace(
                    f"Timeout ({startup_timeout}s) waiting for SwarmUI on {url}.",
                    level="error",
                )
                _emit_action_box(
                    "IMAGE_GEN — SwarmUI Startup Timeout",
                    cmd_display,
                    f"Timed out after {startup_timeout}s waiting for {url}.\n{tail}",
                )
                return False, "START_TIMEOUT", msg

            except Exception as exc:
                msg = (
                    f"❌ **Critical error while launching SwarmUI** from `{install_dir}`: `{exc}`.\n"
                    f"- **Resolution:** Launch SwarmUI manually from `{install_dir}\\launch-windows.bat`."
                )
                self._last_error = msg
                _emit_trace(f"Error starting SwarmUI: {exc}", level="error")
                return False, "START_FAILED", msg
            finally:
                self._is_starting = False


    def stop(self) -> dict:
        """
        Stop the SwarmUI process managed by this launcher.
        Also kills any SwarmUI.exe / dotnet+SwarmUI processes on Windows as fallback.
        Returns: { ok: bool, message: str, killed_pids: list[int] }
        """
        killed_pids = []

        # 1. Kill the subprocess we spawned directly
        with self._lock:
            proc = self._proc
            self._proc = None
            self._is_starting = False

        if proc is not None:
            try:
                if sys.platform == 'win32':
                    subprocess.call(
                        ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                else:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                killed_pids.append(proc.pid)
                log_info(f'Stopped managed SwarmUI process PID={proc.pid}')
            except Exception as exc:
                log_warn(f'Error terminating managed process: {exc}')

        # 2. Fallback: kill any remaining SwarmUI processes by name
        if sys.platform == 'win32':
            try:
                import psutil
                for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        pname = (p.info.get('name') or '').lower()
                        cmdline = ' '.join(p.info.get('cmdline') or []).lower()
                        if 'swarmui' in pname or ('dotnet' in pname and 'swarmui' in cmdline):
                            p.kill()
                            killed_pids.append(p.pid)
                            log_info(f'Force-killed SwarmUI process PID={p.pid} name={p.info["name"]}')
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except ImportError:
                # psutil not available: use taskkill by image name
                for img in ('SwarmUI.exe',):
                    try:
                        subprocess.call(
                            ['taskkill', '/F', '/IM', img],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                    except Exception:
                        pass

        if killed_pids:
            msg = f'SwarmUI stopped. Killed PIDs: {killed_pids}'
            _emit_trace(f'SwarmUI stopped (PIDs: {killed_pids})', level='info')
            return {'ok': True, 'message': msg, 'killed_pids': killed_pids}
        else:
            msg = 'SwarmUI was not running (no managed process found).'
            return {'ok': True, 'message': msg, 'killed_pids': []}

    def get_ram_usage_mb(self) -> dict:
        """Return total RAM (MB) used by SwarmUI-related processes via psutil."""
        result = {'ram_mb': 0, 'pid_count': 0, 'pids': []}
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
                try:
                    pname = (p.info.get('name') or '').lower()
                    cmdline = ' '.join(p.info.get('cmdline') or []).lower()
                    if 'swarmui' in pname or ('dotnet' in pname and 'swarmui' in cmdline):
                        mem = p.info.get('memory_info')
                        if mem:
                            result['ram_mb'] += round(mem.rss / (1024 * 1024))
                        result['pids'].append(p.pid)
                        result['pid_count'] += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            pass
        return result

    def _read_log_tail(self, max_lines: int = 10) -> str:
        """Read the last `max_lines` from the swarmui autostart log file."""
        if not os.path.isfile(self._log_path):
            return ""
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return "".join(lines[-max_lines:]).strip()
        except Exception:
            return ""
