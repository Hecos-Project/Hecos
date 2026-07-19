import os
import socket
import urllib.request
import urllib.error
import json
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

def get_public_ip(timeout: int = 5) -> str:
    """
    Fetches the current public/WAN IP address.
    Tries multiple providers in sequence for resilience.
    Returns the IP string or raises an exception on failure.
    """
    providers = [
        "https://api.ipify.org",
        "https://api4.my-ip.io/ip",
        "https://ipv4.icanhazip.com",
    ]
    last_exc = None
    for url in providers:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                ip = r.read().decode().strip()
            if ip and len(ip) < 40:   # sanity: must look like an IP
                return ip
        except Exception as exc:
            last_exc = exc
            continue
    raise ConnectionError(f"All public-IP providers failed. Last error: {last_exc}")


# ─── WAN Port Reachability ───────────────────────────────────────────────────

_PORT_CHECK_RESULT = {}   # cache: {(ip, port): ("open"|"closed"|"error", ts)}

def check_wan_port(ip: str, port: int = HECOS_PORT, timeout: int = 8) -> dict:
    """
    Checks whether `port` on `ip` is reachable from the public internet.

    Strategy (multi-layer, first success wins):
      1. portchecker.co JSON API (external SaaS, no auth required)
      2. Direct TCP connect attempt (works only if caller is *outside* the LAN —
         from inside it tests only local reachability, but still useful)
      3. Returns a structured dict:
            {
              "status":  "open" | "closed" | "timeout" | "error",
              "method":  "portchecker" | "direct" | "unknown",
              "detail":  <human readable string>,
            }
    """
    import time
    cache_key = (ip, port)
    cached = _PORT_CHECK_RESULT.get(cache_key)
    if cached and (time.time() - cached["_ts"] < 60):
        return {k: v for k, v in cached.items() if k != "_ts"}

    result = _do_check_wan_port(ip, port, timeout)
    result["_ts"] = time.time()
    _PORT_CHECK_RESULT[cache_key] = result
    clean = {k: v for k, v in result.items() if k != "_ts"}
    return clean


def _do_check_wan_port(ip: str, port: int, timeout: int) -> dict:
    # ── Method 1: portchecker.co API ─────────────────────────────────────────
    try:
        payload = json.dumps({"host": ip, "ports": [port]}).encode()
        req = urllib.request.Request(
            "https://portchecker.co/api/v1/query",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Hecos/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        # Response: {"check": [{"port": 7070, "status": true/false}]}
        checks = data.get("check", [])
        if checks:
            is_open = checks[0].get("status", False)
            return {
                "status": "open" if is_open else "closed",
                "method": "portchecker.co",
                "detail": f"Port {port} is {'open ✅' if is_open else 'closed 🔴'} (verified externally via portchecker.co)",
            }
    except Exception as e1:
        pass  # fall through to next method

    # ── Method 2: Direct TCP connect (from inside LAN — indicates local bind) ─
    try:
        with socket.create_connection((ip, port), timeout=min(timeout, 4)):
            return {
                "status": "open",
                "method": "direct-tcp",
                "detail": f"Port {port} responds to direct TCP connect (local network reachability confirmed)",
            }
    except socket.timeout:
        return {
            "status": "timeout",
            "method": "direct-tcp",
            "detail": f"Port {port} timed out — router may be blocking or port-forwarding not configured",
        }
    except ConnectionRefusedError:
        return {
            "status": "closed",
            "method": "direct-tcp",
            "detail": f"Port {port} refused connection — Hecos may be bound to 127.0.0.1 only",
        }
    except Exception as e2:
        return {
            "status": "error",
            "method": "unknown",
            "detail": f"Check failed: {e2}",
        }
