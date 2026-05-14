import os
import sys
import subprocess
import socket
import webbrowser
from hecos.tray.config import SYSTEM_YAML, PLUGINS_YAML, load_settings, HECOS_PORT
from hecos.tray.network_utils import get_scheme, get_urls

# ── Cached CDP status ─────────────────────────────────────────────────────────
_CDP_ALIVE: bool = False

def set_cdp_alive(value: bool) -> None:
    global _CDP_ALIVE
    _CDP_ALIVE = value

def get_cdp_alive() -> bool:
    return _CDP_ALIVE
# ──────────────────────────────────────────────────────────────────────────────

def _get_cdp_port() -> int:
    """Read the CDP port from plugins.yaml or system.yaml (fallback 9222)."""
    for yaml_path in [PLUGINS_YAML, SYSTEM_YAML]:
        if not os.path.exists(yaml_path):
            continue
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = f.read()
            in_browser = False
            for line in content.splitlines():
                stripped = line.strip()
                if "BROWSER:" in stripped:
                    in_browser = True
                if in_browser and "cdp_port:" in stripped:
                    return int(stripped.split(":", 1)[1].strip())
        except Exception:
            continue
    return 9222

def is_ai_ready_browser_running(cdp_port: int = 9222) -> bool:
    """Check if Chrome/Edge is already listening on the CDP debug port."""
    try:
        with socket.create_connection(("localhost", cdp_port), timeout=1):
            return True
    except OSError:
        return False

def discover_browsers() -> list:
    """Scan common install paths for major browsers and the bundled Playwright Chromium binary."""
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
    seen_names = set()
    for name, path in candidates:
        if os.path.isfile(path) and name not in seen_names:
            found.append({"name": name, "path": path})
            seen_names.add(name)

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

def launch_ai_ready_browser(cdp_port: int = 9222, startup_url: str = "") -> bool:
    """Launch Chrome (or Edge) with --remote-debugging-port."""
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
        return True
    except Exception as e:
        print(f"[TRAY] Failed to launch AI-Ready Browser: {e}")
        return False

def intelligent_open_webui(icon, item):
    """Intelligently opens or refreshes the Hecos WebUI via CDP."""
    chat_url, _ = get_urls()
    cdp_port = _get_cdp_port()
    
    if is_ai_ready_browser_running(cdp_port):
        try:
            from hecos.modules.browser import engine
            if not engine.is_running():
                engine.launch(mode="cdp_mode", cdp_port=cdp_port)
            
            tabs = engine.list_tabs()
            found_any = False
            for tab in tabs:
                if f":{HECOS_PORT}" in tab.get("url", ""):
                    try:
                        page_obj = None
                        for ctx in engine._BROWSER.contexts:
                            for p in ctx.pages:
                                if p.url() == tab["url"]:
                                    page_obj = p
                                    break
                        if page_obj:
                            page_obj.reload(wait_until="domcontentloaded")
                            page_obj.bring_to_front()
                            found_any = True
                    except Exception:
                        continue
            
            if not found_any:
                engine.new_tab(chat_url)
            return
        except Exception as e:
            print(f"[TRAY] Intelligent refresh error: {e}")

    webbrowser.open(chat_url)

def intelligent_open_ai_browser(icon, item):
    """Specific helper for the AI Playwright browser."""
    try:
        from hecos.modules.browser import engine
        s = load_settings()
        headless    = s.get("browser_headless", False)
        startup_url = s.get("browser_startup_url", "")
        mode        = s.get("browser_engine_mode", "app_mode")
        cdp_port    = _get_cdp_port()
        
        if not engine.is_running():
            engine.launch(headless=headless, mode=mode, cdp_port=cdp_port)
        
        if startup_url:
            if startup_url == "http://localhost:7070":
                scheme = get_scheme()
                startup_url = f"{scheme}://localhost:{HECOS_PORT}"
            elif not startup_url.startswith(("http://", "https://", "file://", "about:")):
                startup_url = "https://" + startup_url
            
            tabs = engine.list_tabs()
            for tab in tabs:
                if tab.get("url") == startup_url:
                    page = engine.get_page()
                    if page:
                        page.reload(wait_until="domcontentloaded")
                        page.bring_to_front()
                    return

            page = engine.get_page()
            if page:
                page.goto(startup_url, wait_until="domcontentloaded")
    except Exception as e:
        print(f"[TRAY] AI Browser launch error: {e}")

def open_ai_browser(icon, item):
    """Menu wrapper for AI browser."""
    intelligent_open_ai_browser(icon, item)

def close_ai_browser(icon, item):
    try:
        from hecos.modules.browser import engine
        engine.close()
    except Exception as e:
        print(f"[TRAY] AI Browser close error: {e}")
