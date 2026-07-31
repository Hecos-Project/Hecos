"""
MODULE: System Diagnostics - Hecos
DESCRIPTION: Pre-flight checks and hardware status.

Boot behaviour (post-refactor):
  - Default: silent boot, zero output, non-blocking.
  - ESC held at startup: activates the full diagnostic sequence.
  - /diagnosi slash command: runs full diagnostics on-demand at any time.
"""

import os
import time
import threading
import json
import msvcrt
import psutil
from hecos.core.logging import logger
from hecos.core.audio import voice
from hecos.ui import interface
from hecos.core.system.version import VERSION, COPYRIGHT, get_version_string
from hecos.core.i18n import translator
from hecos.core.constants import LOGS_DIR, SNAPSHOTS_DIR, HECOS_DIR

VERDE  = '\033[92m'
ROSSO  = '\033[91m'
CIANO  = '\033[96m'
GIALLO = '\033[93m'
RESET  = '\033[0m'
BOLD   = '\033[1m'

# Set when the diagnostic sequence starts
_BOOT_START_TIME: float = 0.0

# ── ESC detection ─────────────────────────────────────────────────────────────

def _esc_is_held(window_ms: int = 120) -> bool:
    """
    Returns True if ESC is found in the keyboard buffer within `window_ms` ms.
    Non-blocking: drains any other queued keys and only reacts to ESC (0x1b).
    """
    try:
        deadline = time.monotonic() + window_ms / 1000.0
        while time.monotonic() < deadline:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':
                    # Drain remaining buffer
                    while msvcrt.kbhit():
                        msvcrt.getch()
                    return True
            time.sleep(0.01)
    except Exception:
        pass
    return False


def _flush_kb():
    """Drain any keys left in the keyboard buffer."""
    try:
        while msvcrt.kbhit():
            msvcrt.getch()
    except Exception:
        pass

# ── Public entry points ───────────────────────────────────────────────────────

def run_if_requested(config) -> bool:
    """
    Primary boot entry point.

    Normal boot  → instant, silent (only async backend check in background).
    ESC held     → activates the full interactive diagnostic sequence.

    Returns True always (False only on critical folder-structure failure).
    """
    # Always start the async backend check — it's non-blocking
    check_backend_async(config)

    # Quick ESC poll (120 ms window — imperceptible during normal boot)
    if _esc_is_held(window_ms=120):
        logger.info("[DIAG] ESC detected at boot — running full diagnostics.")
        return run_full_diagnostics(config)

    # Silent path: just log timing, nothing printed to console
    logger.debug("[DIAG] Silent boot — skipping diagnostic sequence.")
    return True


# Keep backward-compatible alias so any external callers don't break
def run_initial_check(config) -> bool:
    return run_if_requested(config)


# ── Full diagnostic sequence (ESC / on-demand) ───────────────────────────────

def run_full_diagnostics(config) -> bool:
    """
    Full interactive boot diagnostics. Called when:
      - ESC is held at startup
      - The /diagnosi slash command is invoked
    Returns False only if a critical folder structure error is detected.
    """
    global _BOOT_START_TIME
    _BOOT_START_TIME = time.time()
    _ts = time.strftime("%d/%m/%Y %H:%M:%S")

    os.system('cls' if os.name == 'nt' else 'clear')

    # ── Boot Banner ──────────────────────────────────────────────────────────
    print(f"{CIANO}{BOLD}")
    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║   🔍 HECOS DIAGNOSTICS  —  {_ts:<24}║")
    print(f"║   {get_version_string():<51}║")
    print(f"╚══════════════════════════════════════════════════════╝{RESET}")
    print()
    logger.info(f"[DIAG] === HECOS DIAGNOSTICS [{_ts}] ===")

    print(f"{CIANO}{COPYRIGHT}{RESET}")
    print(f"{CIANO}{'─' * 55}{RESET}\n")

    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}  {translator.t('welcome', version=VERSION)}{RESET}")
    print(f"{CIANO}  {translator.t('boot_sequence')}{RESET}")
    print(f"{CIANO}==================================================={RESET}\n")

    # ── Folder structure ─────────────────────────────────────────────────────
    missing = check_folders()
    if missing:
        print(f"   [-] {ROSSO}{translator.t('diag_error_dirs', dirs=', '.join(missing))}{RESET}")
        time.sleep(2)
        return False
    print(f"   [+] {VERDE}{translator.t('diag_structure_ok')}{RESET}")

    # ── Hardware ─────────────────────────────────────────────────────────────
    print(check_hardware())

    # ── Voice / Mic ──────────────────────────────────────────────────────────
    print(f"   [+] {VERDE}{translator.t('diag_voice_ok')}{RESET}")
    energy_threshold = config.get('listening', {}).get('energy_threshold', 'N/D')
    print(f"   [+] {VERDE}{translator.t('diag_mic_ready', soglia=energy_threshold)}{RESET}")

    # ── Plugin scan ──────────────────────────────────────────────────────────
    results = scan_plugins_fast(config)
    for res in results[:5]:
        print(res)

    print(f"\n{CIANO}==================================================={RESET}")

    # ── Greeting ─────────────────────────────────────────────────────────────
    from hecos.core.system.greeting import get_spoken_greeting, get_ui_greeting
    intro_greeting_voc = get_spoken_greeting(config)
    intro_greeting_ui  = get_ui_greeting(config)
    print_and_speak(f"{CIANO}[SYSTEM] {RESET}" + intro_greeting_ui, intro_greeting_voc)

    _flush_kb()

    elapsed = time.time() - _BOOT_START_TIME
    logger.info(f"[DIAG] === Hecos ready in {elapsed:.1f}s ===")
    print(f"{CIANO}{'─' * 55}{RESET}")
    print(f"{CIANO}   ✅ Hecos ready in {elapsed:.1f}s{RESET}")
    print(f"{CIANO}{'─' * 55}{RESET}")

    time.sleep(0.5)
    return True


def run_diagnostics_report(config) -> str:
    """
    Returns a Markdown-formatted diagnostic report for use by the /diagnosi
    slash command. Non-interactive, does NOT clear the screen.
    """
    lines = ["## 🔍 Hecos — System Diagnostics\n"]

    # Version
    try:
        lines.append(f"**Version:** `{VERSION}`")
        lines.append(f"**Build:** `{get_version_string()}`")
    except Exception as e:
        lines.append(f"**Version:** error — {e}")

    # Hardware
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        cpu_icon = "🟢" if cpu < 80 else "🔴"
        ram_icon = "🟢" if mem.percent < 85 else "🔴"
        lines.append(f"\n### 🖥️ Hardware")
        lines.append(f"- {cpu_icon} **CPU:** {cpu:.1f}%")
        lines.append(f"- {ram_icon} **RAM:** {mem.percent:.1f}% used "
                     f"({mem.available // 1024 // 1024} MB free / "
                     f"{mem.total // 1024 // 1024} MB total)")
    except Exception as e:
        lines.append(f"\n**Hardware:** error — {e}")

    # Folder structure
    try:
        missing = check_folders()
        lines.append(f"\n### 📁 Directory Structure")
        if missing:
            lines.append(f"- 🔴 **Missing:** `{', '.join(missing)}`")
        else:
            lines.append("- 🟢 All required directories are present")
    except Exception as e:
        lines.append(f"\n**Directory:** error — {e}")

    # Plugin registry
    try:
        lines.append(f"\n### 🧩 Plugins")
        from hecos.core.system.module_state import REGISTRY_PATH, _loaded_plugins, _lazy_plugins_paths
        eager = len(_loaded_plugins)
        lazy  = len(_lazy_plugins_paths)
        lines.append(f"- **Loaded (eager):** {eager}")
        lines.append(f"- **Dormant (lazy):** {lazy}")
        results = scan_plugins_fast(config)
        for r in results:
            # Strip ANSI codes for markdown output
            import re
            clean = re.sub(r'\033\[[0-9;]*m', '', r).strip()
            lines.append(f"  - {clean}")
    except Exception as e:
        lines.append(f"\n**Plugins:** error — {e}")

    # Backend status
    try:
        backend_type = config.get('backend', {}).get('type', 'N/D')
        lines.append(f"\n### 🔌 Backend")
        lines.append(f"- **Type:** `{backend_type}`")
        check_enabled = config.get('system', {}).get('check_local_backend_on_boot', False)
        if check_enabled:
            lines.append("- ℹ️ Backend check enabled (async on boot)")
        else:
            lines.append("- ℹ️ Backend check disabled (`check_local_backend_on_boot=false`)")
    except Exception as e:
        lines.append(f"\n**Backend:** error — {e}")

    # Mic / voice config
    try:
        energy = config.get('listening', {}).get('energy_threshold', 'N/D')
        lines.append(f"\n### 🎙️ Audio")
        lines.append(f"- **Energy threshold:** `{energy}`")
    except Exception:
        pass

    lines.append("\n---")
    lines.append("*Use `/diagnostics` anytime to update this report.*")
    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────────

def print_and_speak(video_text, voice_text=None):
    print(video_text)
    if voice_text:
        voice.speak(voice_text)
    time.sleep(0.1)


def check_folders():
    """Check required directory structure. Auto-creates missing user dirs."""
    package_folders = ["plugins", "core", "ui", "app"]
    user_folders = [
        LOGS_DIR,
        SNAPSHOTS_DIR,
        os.path.join(HECOS_DIR, "memory"),
        os.path.join(HECOS_DIR, "personas"),
    ]

    missing = []
    for f in package_folders:
        if not os.path.exists(os.path.join(HECOS_DIR, f)):
            missing.append(f"hecos/{f}")

    for f_path in user_folders:
        if not os.path.exists(f_path):
            try:
                os.makedirs(f_path, exist_ok=True)
            except Exception:
                missing.append(os.path.basename(f_path))

    return missing


def check_hardware():
    """Returns a formatted string with CPU and RAM status."""
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    cpu_status = f"{VERDE}OK{RESET}" if cpu < 80 else f"{ROSSO}HIGH ({cpu}%){RESET}"
    ram_status = f"{VERDE}OK{RESET}" if ram < 85 else f"{ROSSO}CRITICAL ({ram}%){RESET}"
    return f"   [+] CPU Core: {cpu_status} | Neural Memory (RAM): {ram_status}"


def check_backend_async(config):
    """
    Verifies the status of the active backend in a background thread.
    Only runs if check_local_backend_on_boot=true in config.
    Always non-blocking.
    """
    check_enabled = config.get('system', {}).get('check_local_backend_on_boot', False)
    if not check_enabled:
        logger.debug("[DIAG] Backend check skipped (check_local_backend_on_boot=false).")
        return

    backend_type = config.get('backend', {}).get('type', 'ollama')
    if backend_type not in ('ollama', 'kobold'):
        logger.debug(f"[DIAG] Backend check skipped for cloud backend '{backend_type}'.")
        return

    def _run_check():
        import urllib.request, urllib.error
        probe_timeout = config.get('backend', {}).get('ollama', {}).get('probe_timeout_sec', 3)
        try:
            if backend_type == 'kobold':
                url = (config.get('backend', {}).get('kobold', {})
                       .get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model')
                try:
                    urllib.request.urlopen(url, timeout=probe_timeout)
                    logger.info("[DIAG] Kobold backend: ONLINE")
                except Exception as e:
                    logger.warning(f"[DIAG] Kobold backend not responding: {e}")
            else:
                ollama_base = (config.get('backend', {}).get('ollama', {})
                               .get('url', 'http://localhost:11434').rstrip('/'))
                tags_url = ollama_base + '/api/tags'
                try:
                    urllib.request.urlopen(tags_url, timeout=probe_timeout)
                    logger.info(f"[DIAG] Ollama backend: ONLINE ({ollama_base})")
                except Exception as e:
                    logger.warning(f"[DIAG] Ollama backend not responding at {ollama_base}: {e}")
        except Exception as e:
            logger.warning(f"[DIAG] Backend check error: {e}")

    t = threading.Thread(target=_run_check, daemon=True, name="HecosBackendCheck")
    t.start()
    logger.debug("[DIAG] Backend check started asynchronously.")


def scan_plugins_fast(config):
    """
    Fast plugin status scan: reads the already-built capability registry JSON
    instead of re-importing all plugin modules from scratch.
    """
    from hecos.core.system.module_state import REGISTRY_PATH
    results = []
    try:
        if not os.path.isfile(REGISTRY_PATH):
            return [f"   [-] {ROSSO}Registry file not found — run module_loader first.{RESET}"]
        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        for tag, info in registry.items():
            status = info.get('status', 'ONLINE')
            if 'DORMANT' in status or status == 'ONLINE':
                results.append(f"   [+] {tag}: {VERDE}{status}{RESET}")
            elif status in ('ERROR', 'OFFLINE'):
                results.append(f"   [-] {tag}: {ROSSO}{status}{RESET}")
            else:
                results.append(f"   [!] {tag}: {GIALLO}{status}{RESET}")
    except Exception as e:
        results.append(f"   [-] {ROSSO}Could not read registry: {e}{RESET}")
    return results
