"""
llama_cpp/server.py
────────────────────────────────────────────────────────────────────────────
Hecos — Llama CPP Backend Server Manager

Hecos manages GGUF models COMPLETELY INDEPENDENTLY from Ollama.
Ollama does NOT need to be installed or running.

Strategy for locating the llama-server binary (in order of priority):
  1. Hecos' own bundled binary:  C:\\Hecos\\bin\\llama-server.exe
  2. Any llama-server found in PATH (if user installed llama.cpp manually)
  3. Ollama's bundled binary (opportunistically reused if Ollama happens to be installed)
  4. Auto-download the official llama.cpp release from GitHub into C:\\Hecos\\bin\\
  5. Fall back to `python -m llama_cpp.server` (requires llama-cpp-python package)

This means Hecos works in ALL scenarios:
  - Fresh PC with nothing installed  → auto-downloads the binary
  - PC with Ollama installed          → reuses the binary without opening Ollama
  - PC with llama.cpp in PATH         → uses it directly
────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import shutil
import platform
import subprocess
import time
import socket
import psutil
from hecos.core.logging import logger
from .discovery import get_model_path

# Where Hecos stores its own copy of the llama-server binary
_HECOS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_BIN_DIR = os.path.join(_HECOS_ROOT, "bin")
_LOCAL_BIN = os.path.join(_BIN_DIR, "llama-server.exe" if os.name == "nt" else "llama-server")

# GitHub release to download from if no binary is found
# Using a known stable release of llama.cpp
_LLAMACPP_RELEASE_URL = (
    "https://github.com/ggerganov/llama.cpp/releases/download/b11020/"
    "llama-b11020-bin-win-cuda-12.4-x64.zip"
)
_LLAMACPP_RELEASE_URL_NOCUDA = (
    "https://github.com/ggerganov/llama.cpp/releases/download/b11020/"
    "llama-b11020-bin-win-cpu-x64.zip"
)


def _find_llama_server() -> str | None:
    """
    Locate the llama-server executable.
    Returns the absolute path, or None if not found anywhere.
    """

    # 1. Hecos' own bundled binary (highest priority — fully self-contained)
    if os.path.isfile(_LOCAL_BIN):
        logger.info(f"[LlamaCPP] Using Hecos bundled binary: {_LOCAL_BIN}")
        return _LOCAL_BIN

    # 2. Any llama-server in the system PATH
    for exe_name in ("llama-server", "llama-server.exe"):
        found = shutil.which(exe_name)
        if found:
            logger.info(f"[LlamaCPP] Found llama-server in PATH: {found}")
            return found

    # 3. [REMOVED] We no longer reuse Ollama's binary because it relies on dynamic 
    #    backend loading from cuda_v12/v13 folders which fails when executed standalone,
    #    causing silent fallback to CPU-only inference.
    # ollama_bin = os.path.expandvars(
    #     r"%LOCALAPPDATA%\Programs\Ollama\lib\ollama\llama-server.exe"
    # )
    # if os.path.isfile(ollama_bin):
    #     logger.info(f"[LlamaCPP] Reusing Ollama bundled binary (Ollama does NOT need to run): {ollama_bin}")
    #     return ollama_bin

    # 4. Inside the llama_cpp Python package (some builds ship a binary)
    try:
        import importlib.util
        spec = importlib.util.find_spec("llama_cpp")
        if spec and spec.origin:
            pkg_dir = os.path.dirname(spec.origin)
            for fname in ("llama-server.exe", "llama-server", "server.exe"):
                candidate = os.path.join(pkg_dir, fname)
                if os.path.isfile(candidate):
                    logger.info(f"[LlamaCPP] Found binary in llama_cpp package: {candidate}")
                    return candidate
    except Exception:
        pass

    return None


def _auto_download_llama_server() -> str | None:
    """
    Download the official llama.cpp llama-server binary from GitHub releases
    and save it to C:\\Hecos\\bin\\llama-server.exe.
    Returns the path on success, or None on failure.
    """
    import urllib.request
    import zipfile
    import io

    os.makedirs(_BIN_DIR, exist_ok=True)

    # Try CUDA build first, fall back to CPU-only
    for url, label in [
        (_LLAMACPP_RELEASE_URL, "CUDA 12.4"),
        (_LLAMACPP_RELEASE_URL_NOCUDA, "CPU-only AVX2"),
    ]:
        try:
            logger.info(f"[LlamaCPP] Downloading llama.cpp binary ({label}) from GitHub...")
            with urllib.request.urlopen(url, timeout=120) as response:
                zip_data = response.read()

            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # Find the llama-server executable inside the zip
                exe_names = [n for n in zf.namelist() if "llama-server" in n and not n.endswith("/")]
                if not exe_names:
                    logger.warning(f"[LlamaCPP] llama-server not found in zip from {url}")
                    continue

                # Extract all DLLs and the binary to _BIN_DIR
                for member in zf.namelist():
                    basename = os.path.basename(member)
                    if not basename:
                        continue
                    if basename.endswith(".exe") or basename.endswith(".dll"):
                        dest = os.path.join(_BIN_DIR, basename)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            dst.write(src.read())

                target = os.path.join(_BIN_DIR, "llama-server.exe" if os.name == "nt" else "llama-server")
                if os.path.isfile(target):
                    logger.info(f"[LlamaCPP] Download successful ({label}): {target}")
                    return target

        except Exception as e:
            logger.warning(f"[LlamaCPP] Download failed ({label}): {e}")
            continue

    return None


def _build_env_with_cuda():
    """Return an os.environ copy that includes CUDA DLL paths from common locations."""
    env = os.environ.copy()
    search_dirs = [
        _BIN_DIR,  # Hecos' own bin dir (may contain DLLs from the zip)
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\lib\ollama"),
        os.path.expandvars(r"%PROGRAMFILES%\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin"),
        os.path.expandvars(r"%PROGRAMFILES%\NVIDIA GPU Computing Toolkit\CUDA\v12.2\bin"),
    ]
    for d in search_dirs:
        if os.path.exists(d):
            env["PATH"] = d + os.pathsep + env.get("PATH", "")
    return env


class LlamaCppServerManager:
    def __init__(self):
        self.process = None
        self.current_model = None
        self.port = 8080
        self.host = "127.0.0.1"

    # ── Port utilities ─────────────────────────────────────────────────────
    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def is_server_ready(self, port: int) -> bool:
        if not self.is_port_in_use(port):
            return False
        import urllib.request
        import json
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get("status") == "ok":
                        return True
        except Exception:
            pass
        return False

    def _kill_process_on_port(self, port: int):
        for conn in psutil.net_connections():
            if conn.laddr and conn.laddr.port == port and conn.pid:
                try:
                    psutil.Process(conn.pid).kill()
                    logger.info(f"[LlamaCPP] Killed orphan process {conn.pid} on port {port}")
                except Exception:
                    pass

    # ── Server control ─────────────────────────────────────────────────────
    def start_server(
        self,
        model_filename: str,
        n_gpu_layers: int = -1,
        n_ctx: int = 4096,
        threads: int = 4,
    ) -> bool:
        """
        Start the llama-server in a background subprocess.
        Hecos manages the process lifecycle completely — no Ollama needed.
        """
        if self.process and self.current_model == model_filename:
            logger.info(f"[LlamaCPP] Server already running with model {model_filename}")
            return True

        if self.process:
            self.stop_server()

        model_path = get_model_path(model_filename)
        if not model_path:
            logger.error(f"[LlamaCPP] Model '{model_filename}' not found in models/gguf/")
            return False

        # Kill any stale process on our port
        if self.is_port_in_use(self.port):
            logger.warning(f"[LlamaCPP] Port {self.port} already in use — killing orphan…")
            self._kill_process_on_port(self.port)
            time.sleep(1)

        # ── Find or auto-download the binary ──────────────────────────────
        llama_server_bin = _find_llama_server()
        if not llama_server_bin:
            logger.warning("[LlamaCPP] No llama-server binary found. Attempting auto-download from GitHub...")
            llama_server_bin = _auto_download_llama_server()

        env = _build_env_with_cuda()

        if llama_server_bin:
            # Native llama-server binary path
            cmd = [
                llama_server_bin,
                "--model", model_path,
                "--host", self.host,
                "--port", str(self.port),
                "--ctx-size", str(n_ctx),
                "--n-gpu-layers", str(n_gpu_layers),
                "--threads", str(threads),
            ]
        else:
            # Last resort: python -m llama_cpp.server
            logger.warning("[LlamaCPP] Auto-download failed. Falling back to Python module (requires llama-cpp-python).")
            cmd = [
                sys.executable, "-m", "llama_cpp.server",
                "--model", model_path,
                "--host", self.host,
                "--port", str(self.port),
                "--n_ctx", str(n_ctx),
                "--n_gpu_layers", str(n_gpu_layers),
                "--n_threads", str(threads),
            ]

        logger.info(f"[LlamaCPP] Starting server: {cmd[0]} --model {model_path} ...")

        try:
            log_file = open("C:\\Hecos\\hecos\\logs\\llama_server.log", "w")
            self.process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.current_model = model_filename

            # Wait up to 120 seconds for the server to become ready
            for _ in range(120):
                if self.is_server_ready(self.port):
                    logger.info(f"[LlamaCPP] Server ready on port {self.port} — model: {model_filename}")
                    return True
                time.sleep(1)

            logger.error("[LlamaCPP] Server failed to become ready within 120 s.")
            self.stop_server()
            return False

        except Exception as exc:
            logger.error(f"[LlamaCPP] Exception starting server: {exc}")
            return False

    def stop_server(self):
        """Terminate the running server process tree."""
        if self.process:
            logger.info("[LlamaCPP] Stopping server…")
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except Exception as exc:
                logger.warning(f"[LlamaCPP] Error stopping server: {exc}")
            self.process = None
            self.current_model = None


# Singleton used by client.py
server_manager = LlamaCppServerManager()
