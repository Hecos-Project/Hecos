"""
Hecos Setup - Unified Installer Orchestrator (100% Python stdlib)
Manages end-to-end installation of:
  - Hecos Core + Hecos Tray (Full System)
  - Hecos Core only
  - Hecos Tray only

Works both when launched from inside an existing Hecos folder AND when launched
standalone on a completely empty PC via INSTALL_HECOS_WINDOWS.bat / INSTALL_HECOS_LINUX.sh.
Streams structured progress and live logs to the Web App-Mode Wizard via SSE.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import queue
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any, Callable, Dict, List, Optional, Tuple

from .install_registry import (
    default_core_dir,
    default_tray_dir,
    find_tray_dir,
    is_valid_core_dir,
    is_valid_tray_dir,
    read_registry,
    update_registry,
    validate_install_path,
)

CORE_REPO = ("Hecos-Project", "Hecos")
TRAY_REPO = ("Hecos-Project", "Hecos-Tray")

PBS_RELEASE = "20261110"
PBS_VERSION = "3.11.18"
PBS_BASE_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}"

TRAY_SAFE_DEPS = [
    "pystray>=0.19,<1.0",
    "pillow>=10.0,<14.0",
    "tomli-w>=1.0,<2.0",
    "packaging>=23.0,<28.0",
    "psutil>=5.9,<8.0",
    "pyyaml>=6.0,<7.0",
    "customtkinter>=5.2,<7.0",
    "qrcode>=7.4,<9.0",
]
if os.name == "nt":
    TRAY_SAFE_DEPS.append("pywin32>=306")

# Paths preserved when updating an existing Core or Tray directory in place
CORE_PRESERVE_TOP = {
    "python_env",
    "venv",
    "bin",
    "logs",
    "data",
    "certs",
    "workspace",
    "temp",
    ".env",
    "hecos.db",
    "packages.db",
}
TRAY_PRESERVE_TOP = {"python_env", "venv", "logs"}


def _get_pbs_triple() -> Optional[str]:
    sys_name = platform.system()
    mach = platform.machine().lower()
    if sys_name == "Windows":
        if mach in ("amd64", "x86_64", "x64"):
            return "x86_64-pc-windows-msvc"
    elif sys_name == "Linux":
        if mach in ("x86_64", "amd64"):
            return "x86_64-unknown-linux-gnu"
        if mach in ("aarch64", "arm64"):
            return "aarch64-unknown-linux-gnu"
    elif sys_name == "Darwin":
        if mach in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        if mach in ("x86_64", "amd64"):
            return "x86_64-apple-darwin"
    return None


def get_free_disk_gb(path: str) -> Optional[float]:
    """Return free disk space in GB for the drive/mount containing `path`."""
    try:
        probe = os.path.abspath(path)
        while probe and not os.path.exists(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        if probe and os.path.exists(probe):
            usage = shutil.disk_usage(probe)
            return round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass
    return None


def detect_environment_status(local_core_hint: Optional[str] = None) -> Dict[str, Any]:
    """Inspect existing Core, Tray, Registry, and Python on this machine."""
    reg = read_registry()

    # Locate Core
    core_dir: Optional[str] = None
    for cand in (
        local_core_hint,
        reg.get("core_path"),
        default_core_dir(),
        "/opt/hecos" if os.name != "nt" else None,
    ):
        if cand and is_valid_core_dir(cand):
            core_dir = os.path.normpath(os.path.abspath(cand))
            break

    core_ver: Optional[str] = None
    if core_dir:
        try:
            core_ver = open(
                os.path.join(core_dir, "hecos", "core", "version"), "r", encoding="utf-8"
            ).read().strip()
        except Exception:
            core_ver = "unknown"

    # Locate Tray
    tray_dir, tray_versioned = find_tray_dir(
        core_dir or default_core_dir(),
        override=os.environ.get("HECOS_TRAY_DIR"),
    )
    tray_ver: Optional[str] = None
    if tray_dir:
        try:
            tray_ver = open(
                os.path.join(tray_dir, "tray", "version"), "r", encoding="utf-8"
            ).read().strip()
        except Exception:
            tray_ver = "unknown"

    suggested_core = core_dir or default_core_dir()
    suggested_tray = tray_dir or default_tray_dir(suggested_core)

    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "core_installed": bool(core_dir),
        "core_path": core_dir or suggested_core,
        "core_version": core_ver,
        "tray_installed": bool(tray_dir),
        "tray_path": tray_dir or suggested_tray,
        "tray_version": tray_ver,
        "tray_versioned_folder": tray_versioned,
        "default_core_path": suggested_core,
        "default_tray_path": suggested_tray,
        "free_gb": get_free_disk_gb(suggested_core),
    }


def pick_folder_dialog(initial_dir: str = "") -> Optional[str]:
    """Open a native OS folder browser dialog and return the selected path or None."""
    try:
        if os.name == "nt":
            env = os.environ.copy()
            env["HECOS_INIT_DIR"] = initial_dir if os.path.isdir(initial_dir) else ""
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$f.Description = 'Select Hecos installation folder'; "
                "$f.ShowNewFolderButton = $true; "
                "if ($env:HECOS_INIT_DIR -and (Test-Path $env:HECOS_INIT_DIR)) { $f.SelectedPath = $env:HECOS_INIT_DIR }; "
                "$owner = New-Object System.Windows.Forms.Form; "
                "$owner.TopMost = $true; "
                "if ($f.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", ps_script],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            chosen = res.stdout.strip()
            return chosen or None
        elif sys.platform == "darwin":
            res = subprocess.run(
                ["osascript", "-e", 'POSIX path of (choose folder with prompt "Select Hecos folder")'],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return res.stdout.strip().rstrip("/") or None
        else:
            if shutil.which("zenity"):
                cmd = ["zenity", "--file-selection", "--directory", "--title=Select Hecos Folder"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                return res.stdout.strip() or None
            if shutil.which("kdialog"):
                res = subprocess.run(
                    ["kdialog", "--getexistingdirectory", initial_dir or os.path.expanduser("~")],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return res.stdout.strip() or None
    except Exception:
        pass
    return None


def fetch_github_zipball(owner: str, repo: str) -> Tuple[str, str]:
    """Resolve latest GitHub release zipball URL, with automatic fallback to `main` branch."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = {"User-Agent": "HecosUnifiedInstaller/2.0", "Accept": "application/vnd.github+json"}
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        zip_url = data.get("zipball_url")
        tag = data.get("tag_name") or "latest"
        if zip_url:
            return zip_url, tag
    except Exception:
        pass
    # Graceful fallback to main branch archive (if repo has no published release or API rate-limited)
    fallback_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    return fallback_url, "main"


def _stream_download(
    url: str,
    dest_path: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    timeout: int = 60,
) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "HecosUnifiedInstaller/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.info().get("Content-Length", "-1") or -1)
        done = 0
        last_report = 0.0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(128 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                now = time.monotonic()
                if on_progress and (now - last_report >= 0.25 or (total > 0 and done >= total)):
                    last_report = now
                    on_progress(done, total)


def _merge_extracted_tree(
    source_dir: str,
    target_dir: str,
    preserve_top: set[str],
    preserve_subpaths: Optional[List[str]] = None,
) -> None:
    """Copy extracted repo files into target_dir while preserving user data & envs."""
    os.makedirs(target_dir, exist_ok=True)
    preserve_sub_norm = {
        os.path.normcase(os.path.normpath(p)) for p in (preserve_subpaths or [])
    }

    for root, dirs, files in os.walk(source_dir):
        rel_root = os.path.relpath(root, source_dir)
        rel_root = "" if rel_root == "." else rel_root

        # Skip preserved top-level folders if they already exist in target
        if rel_root == "":
            dirs[:] = [
                d for d in dirs
                if not (d in preserve_top and os.path.exists(os.path.join(target_dir, d)))
            ]
        else:
            norm_rel = os.path.normcase(os.path.normpath(rel_root))
            if norm_rel in preserve_sub_norm and os.path.exists(os.path.join(target_dir, rel_root)):
                dirs[:] = []
                continue

        dst_root = os.path.join(target_dir, rel_root) if rel_root else target_dir
        os.makedirs(dst_root, exist_ok=True)

        for fn in files:
            rel_file = os.path.join(rel_root, fn) if rel_root else fn
            dst_file = os.path.join(target_dir, rel_file)
            if (
                os.path.normcase(os.path.normpath(rel_file)) in preserve_sub_norm
                and os.path.exists(dst_file)
            ):
                continue
            if rel_root == "" and fn in preserve_top and os.path.exists(dst_file):
                continue
            src_file = os.path.join(root, fn)
            shutil.copy2(src_file, dst_file)
            if os.name != "nt" and fn.endswith(".sh"):
                try:
                    os.chmod(dst_file, 0o755)
                except OSError:
                    pass


def _write_tray_core_path(tray_dir: str, core_dir: str) -> None:
    """Ensure tray/tray_settings.toml records core_path cleanly using TOML literal strings."""
    settings_path = os.path.join(tray_dir, "tray", "tray_settings.toml")
    if not os.path.isdir(os.path.dirname(settings_path)):
        return
    norm_core = os.path.normpath(os.path.abspath(core_dir))
    line_val = f"core_path = '{norm_core}'" if "'" not in norm_core else f'core_path = "{norm_core.replace(chr(92), chr(92)*2)}"'

    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            replaced = False
            new_lines = []
            for ln in lines:
                if ln.strip().startswith("core_path") and "=" in ln:
                    new_lines.append(line_val)
                    replaced = True
                else:
                    new_lines.append(ln)
            if not replaced:
                new_lines.append("")
                new_lines.append(line_val)
            with open(settings_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
            return
        except Exception:
            pass
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(f"# Hecos Tray Settings\n{line_val}\n")
    except Exception:
        pass


def create_desktop_shortcut(core_dir: Optional[str], tray_dir: Optional[str]) -> Tuple[bool, str]:
    """Create a Desktop shortcut pointing to Tray (preferred) or Core Global Launcher."""
    if os.name == "nt":
        if tray_dir and os.path.isfile(os.path.join(tray_dir, "START_HECOS_TRAY_WIN.bat")):
            target = os.path.join(tray_dir, "START_HECOS_TRAY_WIN.bat")
            workdir = tray_dir
            icon = os.path.join(tray_dir, "assets", "Hecos_Logo_SQR_NBG_LogoOnly.ico")
            desc = "Launch Hecos (System Tray & Dashboard)"
            win_style = 7
        elif core_dir and os.path.isfile(os.path.join(core_dir, "HECOS GLOBAL LAUNCHER.bat")):
            target = os.path.join(core_dir, "HECOS GLOBAL LAUNCHER.bat")
            workdir = core_dir
            icon = os.path.join(core_dir, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.ico")
            desc = "Launch Hecos Core"
            win_style = 1
        else:
            return False, "No launcher found for Desktop shortcut."

        env = os.environ.copy()
        env["HECOS_SC_TARGET"] = target
        env["HECOS_SC_DIR"] = workdir
        env["HECOS_SC_ICON"] = icon if os.path.isfile(icon) else ""
        env["HECOS_SC_DESC"] = desc
        env["HECOS_SC_STYLE"] = str(win_style)
        ps = (
            "$ws = New-Object -ComObject WScript.Shell; "
            "$desk = [Environment]::GetFolderPath('Desktop'); "
            "$s = $ws.CreateShortcut((Join-Path $desk 'Hecos.lnk')); "
            "$s.TargetPath = $env:HECOS_SC_TARGET; "
            "$s.WorkingDirectory = $env:HECOS_SC_DIR; "
            "$s.WindowStyle = [int]$env:HECOS_SC_STYLE; "
            "if ($env:HECOS_SC_ICON) { $s.IconLocation = ($env:HECOS_SC_ICON + ',0') }; "
            "$s.Description = $env:HECOS_SC_DESC; "
            "$s.Save()"
        )
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], env=env, capture_output=True, text=True)
        return (res.returncode == 0), ("Desktop shortcut created (Hecos.lnk)" if res.returncode == 0 else res.stderr.strip())
    else:
        desktop_dir = os.path.expanduser("~/Desktop")
        if not os.path.isdir(desktop_dir):
            return False, "~/Desktop directory not found."
        if tray_dir and os.path.isfile(os.path.join(tray_dir, "START_HECOS_TRAY_LINUX.sh")):
            exec_cmd = f'bash "{os.path.join(tray_dir, "START_HECOS_TRAY_LINUX.sh")}"'
            workdir = tray_dir
            icon = os.path.join(tray_dir, "assets", "Hecos_Logo_SQR_NBG_LogoOnly.png")
            terminal = "false"
        elif core_dir and os.path.isfile(os.path.join(core_dir, "HECOS GLOBAL LAUNCHER.sh")):
            exec_cmd = f'bash "{os.path.join(core_dir, "HECOS GLOBAL LAUNCHER.sh")}"'
            workdir = core_dir
            icon = os.path.join(core_dir, "hecos", "assets", "Hecos_Core_Logo_NBG.png")
            terminal = "true"
        else:
            return False, "No launcher found for Desktop shortcut."

        fpath = os.path.join(desktop_dir, "Hecos.desktop")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(
                f"[Desktop Entry]\nType=Application\nName=Hecos\n"
                f"Comment=Helping Companion System\nExec={exec_cmd}\n"
                f"Path={workdir}\nIcon={icon}\nTerminal={terminal}\n"
            )
        os.chmod(fpath, 0o755)
        return True, f"Desktop shortcut created ({fpath})"


def launch_hecos_now(core_dir: Optional[str], tray_dir: Optional[str]) -> Tuple[bool, str]:
    """Launch Hecos Tray (preferred) or Core WebUI detached."""
    if tray_dir:
        if os.name == "nt":
            runner = os.path.join(tray_dir, "START_HECOS_TRAY_WIN.bat")
            if os.path.isfile(runner):
                subprocess.Popen(["cmd.exe", "/c", "start", "", runner, "--silent"], cwd=tray_dir)
                return True, f"Launched Hecos Tray ({runner})"
        else:
            runner = os.path.join(tray_dir, "START_HECOS_TRAY_LINUX.sh")
            if os.path.isfile(runner):
                subprocess.Popen(["bash", runner], cwd=tray_dir, start_new_session=True)
                return True, f"Launched Hecos Tray ({runner})"

    if core_dir:
        if os.name == "nt":
            runner = os.path.join(core_dir, "scripts", "windows", "run", "HECOS_WEBUI_RUN_WIN.bat")
            if os.path.isfile(runner):
                subprocess.Popen(["cmd.exe", "/c", "start", "", runner], cwd=core_dir)
                return True, f"Launched Hecos WebUI ({runner})"
        else:
            runner = os.path.join(core_dir, "scripts", "linux", "run", "HECOS_WEBUI_RUN_LINUX.sh")
            if os.path.isfile(runner):
                subprocess.Popen(["bash", runner], cwd=core_dir, start_new_session=True)
                return True, f"Launched Hecos WebUI ({runner})"

    return False, "Could not locate a Hecos launcher script."


class InstallJob:
    """Thread-safe background installation job with replayable SSE event stream."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.events: List[Dict[str, Any]] = []
        self._cond = threading.Condition()
        self.finished = False
        self.result: Dict[str, Any] = {}
        self._thread: Optional[threading.Thread] = None

    def emit(self, event_type: str, **payload: Any) -> None:
        ev = {"type": event_type, "ts": time.time(), **payload}
        with self._cond:
            self.events.append(ev)
            self._cond.notify_all()

    def log(self, message: str, level: str = "info") -> None:
        self.emit("log", message=message, level=level)

    def progress(self, percent: int, phase: str, detail: str = "") -> None:
        self.emit("progress", percent=max(0, min(100, int(percent))), phase=phase, detail=detail)

    def step_state(self, step_id: str, status: str, detail: str = "") -> None:
        self.emit("step", id=step_id, status=status, detail=detail)

    def stream_events(self, start_index: int = 0):
        idx = start_index
        while True:
            with self._cond:
                while idx >= len(self.events) and not self.finished:
                    self._cond.wait(timeout=1.0)
                    if idx >= len(self.events) and not self.finished:
                        yield {"type": "ping"}
                batch = self.events[idx:]
                idx = len(self.events)
                is_done = self.finished
            for ev in batch:
                yield ev
            if is_done and idx >= len(self.events):
                break

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ── Subprocess streaming helper ──────────────────────────────────────────

    def _run_cmd_stream(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> int:
        run_env = os.environ.copy()
        run_env["PYTHONUNBUFFERED"] = "1"
        run_env["PYTHONIOENCODING"] = "utf-8"
        if env:
            run_env.update(env)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            if line:
                lvl = "info"
                low = line.lower()
                if "[fail]" in low or "error:" in low or "traceback" in low:
                    lvl = "error"
                elif "[warn]" in low or "warning:" in low:
                    lvl = "warn"
                elif "[ ok ]" in low or "successfully installed" in low:
                    lvl = "ok"
                self.log(line, lvl)
        return proc.wait()

    # ── Shared standalone Python archive (downloaded ONCE for Core + Tray) ──

    def _ensure_pbs_archive(self, tmp_root: str) -> Optional[str]:
        triple = _get_pbs_triple()
        if not triple:
            self.log(f"[WARN] Standalone Python not available for {platform.system()}/{platform.machine()}", "warn")
            return None

        asset = f"cpython-{PBS_VERSION}+{PBS_RELEASE}-{triple}-install_only.tar.gz"
        url = f"{PBS_BASE_URL}/cpython-{PBS_VERSION}%2B{PBS_RELEASE}-{triple}-install_only.tar.gz"
        sums_url = f"{PBS_BASE_URL}/SHA256SUMS"
        archive_path = os.path.join(tmp_root, asset)

        if os.path.isfile(archive_path):
            return archive_path

        self.log(f"[ .. ] Downloading Portable Python {PBS_VERSION} ({triple}, ~47 MB)...")

        def _on_dl(done: int, total: int):
            mb = done / (1024 * 1024)
            if total > 0:
                tot_mb = total / (1024 * 1024)
                pct = int(done * 100 / total)
                self.log(f"       Python download: {mb:.1f} / {tot_mb:.1f} MB ({pct}%)")

        try:
            _stream_download(url, archive_path, on_progress=_on_dl, timeout=120)
        except Exception as e:
            self.log(f"[FAIL] Could not download Portable Python: {e}", "error")
            return None

        # Verify SHA256 against SHA256SUMS
        self.log("[ .. ] Verifying SHA256 checksum...")
        try:
            sums_req = urllib.request.Request(sums_url, headers={"User-Agent": "HecosUnifiedInstaller/2.0"})
            with urllib.request.urlopen(sums_req, timeout=20) as resp:
                sums_text = resp.read().decode("utf-8", errors="replace")
            expected = None
            for line in sums_text.splitlines():
                if asset in line:
                    expected = line.split()[0].strip().lower()
                    break
            if expected:
                h = hashlib.sha256()
                with open(archive_path, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                actual = h.hexdigest().lower()
                if actual != expected:
                    self.log("[FAIL] SHA256 checksum MISMATCH! Deleting corrupt archive.", "error")
                    os.remove(archive_path)
                    return None
                self.log("[ OK ] SHA256 checksum verified.", "ok")
            else:
                self.log("[WARN] Asset hash not found in SHA256SUMS; continuing.", "warn")
        except Exception as e:
            self.log(f"[WARN] Could not fetch SHA256SUMS ({e}); continuing.", "warn")

        return archive_path

    def _extract_pbs_into(self, archive_path: str, target_py_dir: str) -> Optional[str]:
        self.log(f"[ .. ] Extracting Portable Python into {target_py_dir} ...")
        extract_tmp = tempfile.mkdtemp(prefix="hecos_py_ext_")
        try:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(extract_tmp)
            src_py = os.path.join(extract_tmp, "python")
            if not os.path.isdir(src_py):
                return None
            if os.path.isdir(target_py_dir):
                shutil.rmtree(target_py_dir, ignore_errors=True)
            shutil.move(src_py, target_py_dir)
        except Exception as e:
            self.log(f"[FAIL] Python extraction error: {e}", "error")
            return None
        finally:
            shutil.rmtree(extract_tmp, ignore_errors=True)

        exe = os.path.join(target_py_dir, "python.exe" if os.name == "nt" else os.path.join("bin", "python3"))
        if os.path.isfile(exe):
            self.log(f"[ OK ] Portable Python ready: {exe}", "ok")
            return exe
        return None

    def _download_repo_into(
        self,
        owner: str,
        repo: str,
        target_dir: str,
        preserve_top: set[str],
        preserve_subpaths: Optional[List[str]] = None,
    ) -> bool:
        zip_url, tag = fetch_github_zipball(owner, repo)
        self.log(f"[ .. ] Downloading {owner}/{repo} ({tag})...")
        dl_tmp = tempfile.mkdtemp(prefix=f"hecos_dl_{repo}_")
        zip_path = os.path.join(dl_tmp, f"{repo}.zip")
        extract_dir = os.path.join(dl_tmp, "extract")
        try:
            def _on_dl(done: int, total: int):
                mb = done / (1024 * 1024)
                if total > 0:
                    self.log(f"       {repo}: {mb:.1f} / {total / (1024 * 1024):.1f} MB ({int(done * 100 / total)}%)")
                else:
                    self.log(f"       {repo}: {mb:.1f} MB downloaded...")

            _stream_download(zip_url, zip_path, on_progress=_on_dl, timeout=120)
            self.log(f"[ .. ] Extracting {repo} into {target_dir} ...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            items = os.listdir(extract_dir)
            src_root = (
                os.path.join(extract_dir, items[0])
                if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0]))
                else extract_dir
            )
            _merge_extracted_tree(src_root, target_dir, preserve_top, preserve_subpaths)
            self.log(f"[ OK ] {repo} files installed at {target_dir}", "ok")
            return True
        except Exception as e:
            self.log(f"[FAIL] Failed to download/extract {repo}: {e}", "error")
            return False
        finally:
            shutil.rmtree(dl_tmp, ignore_errors=True)

    # ── Main unified installation flow ───────────────────────────────────────

    def _run(self) -> None:
        cfg = self.config
        mode = cfg.get("mode", "full")  # full | core | tray
        want_core = mode in ("full", "core")
        want_tray = mode in ("full", "tray")

        core_dir = os.path.normpath(os.path.abspath(cfg.get("core_path") or default_core_dir()))
        tray_dir = os.path.normpath(os.path.abspath(cfg.get("tray_path") or default_tray_dir(core_dir)))
        redownload = bool(cfg.get("redownload", False))
        system_lang = cfg.get("system_lang", "en")
        install_piper = bool(cfg.get("install_piper", True))
        enable_autostart = bool(cfg.get("enable_autostart", True))
        create_shortcut = bool(cfg.get("create_shortcut", True))
        force_deps = bool(cfg.get("force_deps", False))

        components: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []
        errors: List[str] = []
        shared_tmp = tempfile.mkdtemp(prefix="hecos_unified_")
        pbs_archive: Optional[str] = None
        core_py: Optional[str] = None
        tray_py: Optional[str] = None

        try:
            # ── 1. Validate paths ────────────────────────────────────────────
            self.progress(5, "Validating paths", "Checking destination folders...")
            self.step_state("paths", "active")
            if want_core:
                ok, errs, warns = validate_install_path(core_dir)
                if not ok:
                    raise RuntimeError(f"Unsafe Core path ({core_dir}): {'; '.join(errs)}")
                for w in warns:
                    self.log(f"[WARN] Core path: {w}", "warn")
            if want_tray:
                ok, errs, warns = validate_install_path(tray_dir)
                if not ok:
                    raise RuntimeError(f"Unsafe Tray path ({tray_dir}): {'; '.join(errs)}")
                for w in warns:
                    self.log(f"[WARN] Tray path: {w}", "warn")
            self.step_state("paths", "ok", "Paths validated")

            # ── 2. Download / Verify Files ───────────────────────────────────
            self.progress(12, "Downloading components", "Checking Core & Tray files...")
            self.step_state("download", "active")

            core_files_ok = False
            if want_core:
                if is_valid_core_dir(core_dir) and not redownload:
                    self.log(f"[ OK ] Hecos Core already present at {core_dir} (keeping local files).", "ok")
                    core_files_ok = True
                else:
                    core_files_ok = self._download_repo_into(
                        CORE_REPO[0],
                        CORE_REPO[1],
                        core_dir,
                        preserve_top=CORE_PRESERVE_TOP,
                        preserve_subpaths=["hecos/config/data", "hecos/data"],
                    )
                    if not core_files_ok:
                        errors.append("Failed to download Hecos Core from GitHub.")

            tray_files_ok = False
            if want_tray:
                if is_valid_tray_dir(tray_dir) and not redownload:
                    self.log(f"[ OK ] Hecos Tray already present at {tray_dir} (keeping local files).", "ok")
                    tray_files_ok = True
                else:
                    tray_files_ok = self._download_repo_into(
                        TRAY_REPO[0],
                        TRAY_REPO[1],
                        tray_dir,
                        preserve_top=TRAY_PRESERVE_TOP,
                        preserve_subpaths=["tray/tray_settings.toml", "tray/update_sources.toml"],
                    )
                    if not tray_files_ok:
                        warnings.append("Failed to download Hecos Tray from GitHub.")

            self.step_state(
                "download",
                "fail" if (want_core and not core_files_ok) else ("warn" if (want_tray and not tray_files_ok) else "ok"),
            )

            # ── 3. Python Runtime Provisioning (downloads ONCE if both need it)
            self.progress(30, "Python runtime", "Preparing isolated Python environments...")
            self.step_state("python", "active")

            if want_core and core_files_ok:
                cand_py = os.path.join(core_dir, "python_env", "python.exe" if os.name == "nt" else os.path.join("bin", "python3"))
                cand_venv = os.path.join(core_dir, "venv", "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python3")
                if os.path.isfile(cand_py):
                    core_py = cand_py
                    self.log(f"[ OK ] Core Python found: {core_py}", "ok")
                elif os.path.isfile(cand_venv):
                    core_py = cand_venv
                    self.log(f"[ OK ] Core venv Python found: {core_py}", "ok")
                else:
                    pbs_archive = self._ensure_pbs_archive(shared_tmp)
                    if pbs_archive:
                        core_py = self._extract_pbs_into(pbs_archive, os.path.join(core_dir, "python_env"))
                    if not core_py:
                        errors.append("Failed to provision Core Python environment.")

            if want_tray and tray_files_ok:
                cand_tray_py = os.path.join(tray_dir, "python_env", "python.exe" if os.name == "nt" else os.path.join("bin", "python3"))
                if os.path.isfile(cand_tray_py):
                    # Verify tkinter works
                    chk = subprocess.run([cand_tray_py, "-c", "import tkinter"], capture_output=True)
                    if chk.returncode == 0:
                        tray_py = cand_tray_py
                        self.log(f"[ OK ] Tray Python (with tkinter) found: {tray_py}", "ok")
                if not tray_py:
                    # Check if a clean system Python with tkinter exists when user already uses it,
                    # OR prefer standalone so Tray is 100% self-contained!
                    if not pbs_archive:
                        pbs_archive = self._ensure_pbs_archive(shared_tmp)
                    if pbs_archive:
                        tray_py = self._extract_pbs_into(pbs_archive, os.path.join(tray_dir, "python_env"))
                    if not tray_py:
                        # Last resort: current interpreter if it has tkinter
                        chk = subprocess.run([sys.executable, "-c", "import tkinter"], capture_output=True)
                        if chk.returncode == 0:
                            tray_py = sys.executable
                            self.log(f"[WARN] Using current Python for Tray: {tray_py}", "warn")
                        else:
                            warnings.append("Could not provision a Python runtime with tkinter for Tray.")

            self.step_state(
                "python",
                "fail" if (want_core and not core_py) else ("warn" if (want_tray and not tray_py) else "ok"),
            )

            # ── 4. Core Dependencies & Configuration ─────────────────────────
            if want_core:
                self.progress(50, "Installing Hecos Core", "Syncing Python packages & Piper TTS...")
                self.step_state("core", "active")
                if core_files_ok and core_py:
                    deps_cmd = [core_py, os.path.join(core_dir, "hecos", "setup_wizard.py"), "--install-deps"]
                    if force_deps:
                        deps_cmd.append("--force")
                    rc = self._run_cmd_stream(deps_cmd, cwd=core_dir)
                    if rc != 0:
                        errors.append("Core essential Python dependencies failed to install.")
                        components["core"] = {"status": "fail", "detail": "Dependency install failed"}
                        self.step_state("core", "fail")
                    else:
                        # Language, Piper TTS, path fixes
                        self.progress(68, "Configuring Hecos Core", "Applying language & audio setup...")
                        post_code = (
                            "import sys; sys.path.insert(0, sys.argv[1]); "
                            "from hecos.setup.setup_env import set_system_language, auto_fix_piper_path; "
                            "from hecos.setup.setup_piper import download_piper_engine; "
                            "set_system_language(sys.argv[2]); "
                            "(download_piper_engine() if sys.argv[3]=='1' else print('[ .. ] Skipping Piper TTS')); "
                            "auto_fix_piper_path()"
                        )
                        self._run_cmd_stream(
                            [core_py, "-c", post_code, core_dir, system_lang, "1" if install_piper else "0"],
                            cwd=core_dir,
                        )
                        components["core"] = {"status": "ok", "detail": f"Ready at {core_dir}"}
                        self.step_state("core", "ok", "Core ready")
                else:
                    components["core"] = {"status": "fail", "detail": "Core files or Python missing"}
                    self.step_state("core", "fail")
            else:
                self.step_state("core", "skip", "Not selected")

            # ── 5. Tray Dependencies (independent — never blocks Core!) ──────
            if want_tray:
                self.progress(78, "Installing Hecos Tray", "Checking Tray GUI dependencies...")
                self.step_state("tray", "active")
                if tray_files_ok and tray_py:
                    chk = subprocess.run(
                        [tray_py, "-c", "import tomli_w, pystray, PIL, customtkinter, qrcode, yaml, psutil, packaging"],
                        capture_output=True,
                    )
                    if chk.returncode == 0 and not force_deps:
                        self.log("[ OK ] All Tray dependencies already satisfied (skipping pip).", "ok")
                        tray_deps_ok = True
                    else:
                        self.log("[ .. ] Installing Tray dependencies...")
                        rc = self._run_cmd_stream(
                            [tray_py, "-m", "pip", "install", "--quiet"] + TRAY_SAFE_DEPS,
                            cwd=tray_dir,
                        )
                        tray_deps_ok = rc == 0

                    if tray_deps_ok:
                        if is_valid_core_dir(core_dir):
                            _write_tray_core_path(tray_dir, core_dir)
                        components["tray"] = {"status": "ok", "detail": f"Ready at {tray_dir}"}
                        self.step_state("tray", "ok", "Tray ready")
                    else:
                        warnings.append("Tray dependencies failed to install (Core is unaffected).")
                        components["tray"] = {"status": "warn", "detail": "Tray pip install failed"}
                        self.step_state("tray", "warn", "Tray warning")
                else:
                    components["tray"] = {"status": "warn", "detail": "Tray files or Python unavailable"}
                    self.step_state("tray", "warn")
            else:
                self.step_state("tray", "skip", "Not selected")

            # ── 6. Finalize: Registry, Autostart, Shortcut, Doctor ───────────
            self.progress(90, "Finalizing", "Updating install registry, autostart & diagnostics...")
            self.step_state("finalize", "active")

            reg_fields: Dict[str, Optional[str]] = {}
            if is_valid_core_dir(core_dir):
                reg_fields["core_path"] = core_dir
            if core_py:
                reg_fields["core_python"] = core_py
            if is_valid_tray_dir(tray_dir):
                reg_fields["tray_path"] = tray_dir
            if tray_py:
                pyw = os.path.join(os.path.dirname(tray_py), "pythonw.exe")
                reg_fields["tray_python"] = pyw if os.path.isfile(pyw) else tray_py
            if reg_fields:
                reg_path = update_registry(**reg_fields)
                self.log(f"[ OK ] Shared registry updated: {reg_path}", "ok")

            if enable_autostart and is_valid_core_dir(core_dir) and is_valid_tray_dir(tray_dir):
                if os.name == "nt":
                    auto_script = os.path.join(core_dir, "scripts", "windows", "setup", "ENABLE_TRAY_AUTOSTART.bat")
                    if os.path.isfile(auto_script):
                        rc = self._run_cmd_stream(
                            ["cmd.exe", "/c", auto_script, "--silent"],
                            cwd=core_dir,
                            env={"HECOS_TRAY_DIR": tray_dir},
                        )
                        if rc != 0:
                            warnings.append("Autostart shortcut could not be configured.")
                else:
                    auto_script = os.path.join(core_dir, "scripts", "linux", "setup", "ENABLE_TRAY_AUTOSTART.sh")
                    if os.path.isfile(auto_script):
                        rc = self._run_cmd_stream(
                            ["bash", auto_script, "--silent"],
                            cwd=core_dir,
                            env={"HECOS_TRAY_DIR": tray_dir},
                        )
                        if rc != 0:
                            warnings.append("Linux autostart entry could not be configured.")

            if create_shortcut:
                sc_ok, sc_msg = create_desktop_shortcut(
                    core_dir if is_valid_core_dir(core_dir) else None,
                    tray_dir if is_valid_tray_dir(tray_dir) else None,
                )
                self.log(f"[{' OK ' if sc_ok else 'WARN'}] {sc_msg}", "ok" if sc_ok else "warn")

            # Run Doctor report via Core Python if available
            doctor_checks: List[Dict[str, str]] = []
            if core_py and is_valid_core_dir(core_dir):
                try:
                    out = subprocess.check_output(
                        [
                            core_py,
                            "-c",
                            "import json, sys; sys.path.insert(0, sys.argv[1]); "
                            "from hecos.setup.setup_env import run_doctor; print(json.dumps(run_doctor()))",
                            core_dir,
                        ],
                        cwd=core_dir,
                        env={**os.environ, "HECOS_TRAY_DIR": tray_dir if is_valid_tray_dir(tray_dir) else ""},
                        text=True,
                        timeout=30,
                    )
                    doctor_checks = json.loads(out.strip()).get("checks", [])
                except Exception as e:
                    self.log(f"[WARN] Could not run final doctor check: {e}", "warn")

            self.step_state("finalize", "warn" if warnings else "ok")
            self.progress(100, "Complete", "Installation finished")

            overall_ok = len(errors) == 0
            self.result = {
                "ok": overall_ok,
                "mode": mode,
                "core_path": core_dir if is_valid_core_dir(core_dir) else None,
                "tray_path": tray_dir if is_valid_tray_dir(tray_dir) else None,
                "components": components,
                "warnings": warnings,
                "errors": errors,
                "doctor": doctor_checks,
            }
            self.emit("done", **self.result)

        except Exception as exc:
            self.log(f"[FAIL] {exc}", "error")
            self.result = {
                "ok": False,
                "mode": mode,
                "core_path": core_dir if is_valid_core_dir(core_dir) else None,
                "tray_path": tray_dir if is_valid_tray_dir(tray_dir) else None,
                "components": components,
                "warnings": warnings,
                "errors": errors + [str(exc)],
                "doctor": [],
            }
            self.emit("done", **self.result)
        finally:
            shutil.rmtree(shared_tmp, ignore_errors=True)
            with self._cond:
                self.finished = True
                self._cond.notify_all()
