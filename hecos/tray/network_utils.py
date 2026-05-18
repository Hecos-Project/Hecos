import os
import socket
from hecos.tray.config import SYSTEM_YAML, PLUGINS_YAML, HECOS_PORT

def get_scheme() -> str:
    # Priority: plugins.yaml (modular), then system.yaml (monolithic/legacy)
    for yaml_path in [PLUGINS_YAML, SYSTEM_YAML]:
        if not os.path.exists(yaml_path):
            continue
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = f.read()
            in_webui = False
            for line in content.splitlines():
                stripped = line.strip()
                if "WEB_UI:" in stripped:
                    in_webui = True
                if in_webui and "https_enabled:" in stripped:
                    value = stripped.split(":", 1)[1].strip().lower()
                    if value.startswith("true") or value.startswith("yes") or value.startswith("1"):
                        return "https"
                    return "http"
        except Exception:
            continue
    return "http"

def get_urls():
    scheme = get_scheme()
    base = f"{scheme}://localhost:{HECOS_PORT}"
    return f"{base}/chat", f"{base}/hecos/config/ui"

def is_hecos_online():
    """Checks if the Hecos backend is responding on port 7070."""
    try:
        with socket.create_connection(("localhost", HECOS_PORT), timeout=2):
            return True
    except OSError:
        return False

def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"
