"""
hecos/ui/terminal_renderer.py
Handles all ASCII/ANSI rendering for the Hecos terminal header rows:
status bar, hardware telemetry, menus, and help screen.
"""
import os
import sys
import re
import glob
import requests

from colorama import Fore, Back, Style
from hecos.core.logging import logger
from hecos.core.system import module_loader
from hecos.core.i18n import translator

GREEN   = Fore.GREEN
YELLOW  = Fore.YELLOW
RED     = Fore.RED
CYAN    = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE   = Fore.WHITE
RESET   = Style.RESET_ALL

_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def translate_status(s):
    """Translates known status keys using the translator."""
    if not s:
        return s
    s_lower = s.lower()
    keys = ["ready", "error", "offline", "timeout", "waiting", "loading", "online", "disabled"]
    for k in keys:
        if s_lower.startswith(k):
            remainder = s[len(k):]
            return translator.t(k) + remainder
    return s


def get_status_color(s):
    """Returns the Fore color code based on current status."""
    if not s:
        return Fore.WHITE
    s_lower = s.lower()
    if "ready" in s_lower or "pronto" in s_lower or "online" in s_lower:
        return Fore.GREEN
    if "thinking" in s_lower or "pensando" in s_lower or "loading" in s_lower:
        return Fore.YELLOW
    if "speaking" in s_lower or "parlando" in s_lower:
        return Fore.CYAN
    if "error" in s_lower or "offline" in s_lower:
        return Fore.RED
    return Fore.WHITE


def get_header_row(L=90):
    from hecos.core.system.version import get_version_string
    titolo = f" {get_version_string()} "
    return f"\033[46m\033[30m{titolo.center(L)}\033[0m"


def get_system_menu_row(L=90):
    comandi = (
        f" {translator.t('menu_help')} | {translator.t('menu_models')} | "
        f"{translator.t('menu_persona')} | {translator.t('menu_mic')} | "
        f"{translator.t('menu_refresh')} | {translator.t('menu_voice')} | "
        f"{translator.t('menu_config')} | PTT (F8) | {translator.t('menu_reboot')} "
    )
    if len(_ANSI_RE.sub('', comandi)) > L:
        comandi = " F1..F4: Menu | F5: Ref | F6: Voice | F8: PTT | F9: Reb "
    return f"{Style.DIM}{comandi.center(L)}{Style.RESET_ALL}"


def get_status_bar(config, voice_status, listening_status, system_status, L, ptt_status=False):
    from hecos.app.model_manager import ModelManager
    try:
        _, model_eff = ModelManager.get_effective_model_info(config)
    except Exception:
        model_eff = "N/D"

    ai_conf = config.get('ai') or {}
    soul = str(ai_conf.get('active_personality', 'N/D')).replace('.yaml', '')
    mic_str = "ON" if listening_status else "OFF"
    spk_str = "ON" if voice_status else "OFF"
    ptt_str = "ON" if ptt_status else "OFF"

    status_translated = translate_status(system_status)
    status_color = get_status_color(system_status)
    info_status = translator.t("system_status", status="{S}").replace("{S}", f"{status_color}{status_translated}{Fore.WHITE}")
    header_mod = translator.t("header_model")
    header_ani = translator.t("header_soul")
    header_mic = translator.t("header_mic")
    header_voc = translator.t("header_voice")

    info_str = f" {info_status} | {header_mod}: {model_eff} | {header_ani}: {soul} | {header_mic}: {mic_str} | {header_voc}: {spk_str} | PTT: {ptt_str} "
    vis_len = len(_ANSI_RE.sub('', info_str))
    p_left = max(0, L - vis_len) // 2
    p_right = max(0, L - vis_len) - p_left
    return f"{Back.BLUE}{Fore.WHITE}{' '*p_left}{info_str}{' '*p_right}{Style.RESET_ALL}"


def get_ptt_hint_row(L=90, system_status="READY", ptt_status=False):
    if "LISTENING" in str(system_status).upper() or "RECORDING" in str(system_status).upper():
        rec_text = " 🔴 RECORDING... "
        return f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{rec_text.center(L)}{Style.RESET_ALL}"
    elif ptt_status:
        hint_text = f" {translator.t('ptt_hint')} "
        return f"{Fore.YELLOW}{hint_text.center(L)}{Style.RESET_ALL}"
    else:
        return f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}"


def get_hardware_row(config=None, dashboard_mod=None):
    """Returns the formatted string for the hardware row (CPU, RAM, VRAM, backend)."""
    from hecos.ui.ui_updater import get_cached_L
    L = get_cached_L()

    if dashboard_mod is None:
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")

    dsb_config = config.get("plugins", {}).get("DASHBOARD", {}) if config else {}
    col_dsb = dsb_config.get("console_dashboard_enabled", True)
    col_tel = dsb_config.get("console_telemetry_enabled", True)

    if not col_dsb:
        return f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}"

    if dashboard_mod:
        try:
            from hecos.ui import graphics
            stats = dashboard_mod.get_stats(config)
            cpu = stats['cpu']
            ram = stats['ram']
            vram = stats['vram']
            if len(str(vram)) > 25:
                vram = str(vram)[:22] + ".."
            backend_status = stats['backend_status']

            cpu_bar = graphics.create_bar(cpu, width=5)
            ram_bar = graphics.create_bar(ram, width=5)

            if backend_status in ("READY", "CLOUD", "ONLINE"):
                display_status = translator.t("ready")
                if backend_status == "CLOUD":
                    display_status = "CLOUD"
                status_color = Fore.GREEN
            elif backend_status in ("OFFLINE", "ERROR", "TIMEOUT"):
                key = backend_status.lower() if backend_status.lower() in ["offline", "error", "timeout"] else "disabled"
                display_status = translator.t(key)
                status_color = Fore.RED
            elif backend_status == "STARTING":
                display_status = "STARTING..."
                status_color = Fore.YELLOW
            else:
                display_status = backend_status if backend_status else "--"
                status_color = Fore.YELLOW

            if col_tel:
                info_hw_raw = translator.t("hardware_line",
                    cpu=cpu_bar, ram=ram_bar, gpu=stats.get('gpu_load', 'N/D'), vram=vram,
                    backend=f"{status_color}{display_status}{Style.RESET_ALL}"
                )
            else:
                info_hw_raw = f" TELEMETRY: {Fore.LIGHTBLACK_EX}NOT ACTIVE{Style.RESET_ALL} | BACKEND AI: {status_color}{display_status}{Style.RESET_ALL} "

            visible_len = len(_ANSI_RE.sub('', info_hw_raw))
            pad_left = max(0, L - visible_len) // 2
            pad_right = max(0, L - visible_len) - pad_left
            info_hw = f"{' ' * pad_left}{info_hw_raw}{' ' * pad_right}"

        except Exception as e:
            info_hw = f"{Fore.RED}-- HARDWARE ERROR: {e} --{Style.RESET_ALL}".center(L)
    else:
        return f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}"

    return f"{Fore.CYAN}{info_hw}{Style.RESET_ALL}"


def show_web_access_info(config):
    """Prints Web UI access links."""
    web_opts = config.get("plugins", {}).get("WEB_UI", {})
    port = web_opts.get("port", 7070)
    use_https = web_opts.get("https_enabled", False)
    scheme = "https" if use_https else "http"

    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.254.254.254', 1))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "localhost"

    base_url = f"{scheme}://{lan_ip}:{port}"

    from hecos.ui.ui_updater import get_cached_L
    L = get_cached_L()

    def get_visible_len(s):
        return len(_ANSI_RE.sub('', s))

    border_color = Fore.CYAN
    title_color = Fore.YELLOW
    label_color = Fore.WHITE

    print(f"{border_color}┌{'─' * (L-2)}┐{RESET}")
    title_text = "WEB INTERFACE ACCESS"
    pad = (L - 2 - len(title_text)) // 2
    pad_r = (L - 2 - len(title_text)) - pad
    print(f"{border_color}│{RESET}{' ' * pad}{title_color}{title_text}{RESET}{' ' * pad_r}{border_color}│{RESET}")
    print(f"{border_color}├{'─' * (L-2)}┤{RESET}")

    for label, url_path in [("Chat:  ", "/chat"), ("Config:", "/hecos/config/ui"), ("Drive: ", "/drive")]:
        left_part = f"  • {label_color}{label}{RESET} {base_url}{url_path}"
        visible_l = get_visible_len(left_part)
        padding = max(0, L - 2 - visible_l)
        print(f"{border_color}│{RESET}{left_part}{' ' * padding}{border_color}│{RESET}")

    print(f"{border_color}└{'─' * (L-2)}┘{RESET}")
    print()
