import sys
import os
import time
import subprocess
from hecos.tray.config import SYSTEM_YAML, HECOS_PORT, VERSION_FILE, _ROOT

# Global list of Popen objects for tracked console windows
_managed_consoles = []

# ── Cached CDP status ─────────────────────────────────────────────────────────
# Written asynchonously by tray_app._monitor_status so build_menu() never
# blocks on a socket call during menu popup rendering.
_CDP_ALIVE: bool = False

def set_cdp_alive(value: bool) -> None:
    global _CDP_ALIVE
    _CDP_ALIVE = value

def get_cdp_alive() -> bool:
    return _CDP_ALIVE
# ──────────────────────────────────────────────────────────────────────────────


def get_scheme() -> str:
    """Reads system.yaml to detect if HTTPS is enabled."""
    try:
        with open(SYSTEM_YAML, "r", encoding="utf-8") as f:
            content = f.read()
        in_webui = False
        for line in content.splitlines():
            stripped = line.strip()
            if "WEB_UI:" in stripped:
                in_webui = True
            if in_webui and "https_enabled:" in stripped:
                value = stripped.split(":", 1)[1].strip().lower()
                if value in ("true", "yes", "1"):
                    return "https"
                break
    except Exception:
        pass
    return "http"


def play_beep(freq: int, duration_ms: int):
    """Universal cross-platform audio helper for system beeps/cues."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(int(freq), int(duration_ms))
        except Exception:
            pass
    else:
        try:
            subprocess.run(["beep", "-f", str(freq), "-l", str(duration_ms)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print('\a', end='', flush=True)


def get_urls():
    scheme = get_scheme()
    base = f"{scheme}://localhost:{HECOS_PORT}"
    return f"{base}/chat", f"{base}/hecos/config/ui"


def get_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "0.19.2"


def is_hecos_online():
    """Checks if the Hecos backend is responding on port 7070."""
    import socket
    try:
        with socket.create_connection(("localhost", HECOS_PORT), timeout=2):
            return True
    except OSError:
        return False


def get_lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def launch_console(script_path: str):
    """Launches a script in a new tracked console window."""
    global _managed_consoles
    _managed_consoles = [p for p in _managed_consoles if p.poll() is None]
    try:
        if sys.platform == "win32":
            p = subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                creationflags=0x00000010,  # CREATE_NEW_CONSOLE
                cwd=_ROOT
            )
            _managed_consoles.append(p)
        else:
            p = subprocess.Popen(["x-terminal-emulator", "-e", script_path], cwd=_ROOT)
            _managed_consoles.append(p)
    except Exception as e:
        print(f"[TRAY] Failed to launch console: {e}")


def terminate_consoles():
    """Closes all console windows tracked by the Tray App."""
    global _managed_consoles
    for p in _managed_consoles:
        if p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    _managed_consoles = []


def is_ai_ready_browser_running(cdp_port: int = 9222) -> bool:
    """Check if Chrome/Edge is already listening on the CDP debug port."""
    import socket
    try:
        with socket.create_connection(("localhost", cdp_port), timeout=1):
            return True
    except OSError:
        return False


# ── Browser Discovery ─────────────────────────────────────────────────────────

def discover_browsers() -> list:
    """
    Scan common install paths for major browsers and the bundled Playwright
    Chromium binary. Returns a list of {"name": str, "path": str} dicts.
    Each browser is deduplicated by name so the menu stays compact.
    """
    local      = os.environ.get("LOCALAPPDATA",     "")
    prog64     = os.environ.get("PROGRAMFILES",      r"C:\Program Files")
    prog32     = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")

    candidates = [
        ("Google Chrome",   os.path.join(prog64, "Google", "Chrome", "Application", "chrome.exe")),
        ("Google Chrome",   os.path.join(prog32, "Google", "Chrome", "Application", "chrome.exe")),
        ("Google Chrome",   os.path.join(local,  "Google", "Chrome", "Application", "chrome.exe")),
        ("Microsoft Edge",  os.path.join(prog64, "Microsoft", "Edge", "Application", "msedge.exe")),
        ("Microsoft Edge",  os.path.join(prog32, "Microsoft", "Edge", "Application", "msedge.exe")),
        ("Mozilla Firefox", os.path.join(prog64, "Mozilla Firefox", "firefox.exe")),
        ("Mozilla Firefox", os.path.join(prog32, "Mozilla Firefox", "firefox.exe")),
        ("Brave Browser",   os.path.join(prog64, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")),
        ("Brave Browser",   os.path.join(local,  "BraveSoftware", "Brave-Browser", "Application", "brave.exe")),
        ("Opera",           os.path.join(local,  "Programs", "Opera", "opera.exe")),
        ("Vivaldi",         os.path.join(local,  "Vivaldi", "Application", "vivaldi.exe")),
    ]

    found = []
    seen_names: set = set()
    for name, path in candidates:
        if os.path.isfile(path) and name not in seen_names:
            found.append({"name": name, "path": path})
            seen_names.add(name)

    # Detect bundled Playwright Chromium binary (runs headlessly without extra install)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            ch_path = pw.chromium.executable_path
            if ch_path and os.path.isfile(ch_path):
                found.append({"name": "Playwright Chromium (built-in)", "path": ch_path})
    except Exception:
        pass

    return found


def launch_browser(path: str, url: str = "") -> bool:
    """Open any browser normally (no CDP/debug flags)."""
    try:
        cmd = [path]
        if url:
            cmd.append(url)
        if sys.platform == "win32":
            subprocess.Popen(
                cmd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            subprocess.Popen(cmd, start_new_session=True)
        return True
    except Exception as e:
        print(f"[TRAY] Failed to launch browser '{path}': {e}")
        return False


# ── AI-Ready Browser (CDP) ────────────────────────────────────────────────────

def launch_ai_ready_browser(cdp_port: int = 9222, startup_url: str = "") -> bool:
    """
    Launch Chrome (or Edge) with --remote-debugging-port so Hecos can
    connect via CDP and control the browser. Returns True on success.
    """
    import shutil

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    browser_path = None
    for path in chrome_paths:
        if os.path.isfile(path):
            browser_path = path
            break

    if browser_path is None:
        browser_path = shutil.which("chrome") or shutil.which("msedge") or shutil.which("google-chrome")

    if browser_path is None:
        print("[TRAY] Could not find Chrome or Edge to launch in AI-Ready mode.")
        return False

    user_data = os.path.join(
        os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", ".")),
        "Google", "Chrome", "HecosAIProfile"
    )
    os.makedirs(user_data, exist_ok=True)

    cmd = [
        browser_path,
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
    ]
    if startup_url:
        cmd.append(startup_url)

    try:
        if sys.platform == "win32":
            subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen(cmd, start_new_session=True)
        print(f"[TRAY] AI-Ready Browser launched: {browser_path}")
        return True
    except Exception as e:
        print(f"[TRAY] Failed to launch AI-Ready Browser: {e}")
        return False
