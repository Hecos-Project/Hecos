"""
hecos/ui/terminal_renderer.py
Handles all ASCII/ANSI rendering for the Hecos terminal header rows:
status bar, hardware telemetry, menus, and WebUI access banner.
"""
import os
import sys
import re
import glob

from colorama import Fore, Back, Style
from hecos.core.logging import logger
from hecos.core.system import module_loader
from hecos.core.i18n import translator
from hecos.ui.viewport import get_viewport, strip_ansi, visible_width, clip_ansi

GREEN   = Fore.GREEN
YELLOW  = Fore.YELLOW
RED     = Fore.RED
CYAN    = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE   = Fore.WHITE
RESET   = Style.RESET_ALL

_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _resolve_width(L=None) -> int:
    if L is not None and L > 0:
        return L
    return get_viewport().usable_width


def _center_ansi(text: str, width: int, fill_prefix: str = "", fill_reset: str = RESET) -> str:
    """Centers an ANSI string to exact visible `width` columns, clipping safely if wider."""
    clipped = clip_ansi(text, width)
    vis = visible_width(clipped)
    pad_left = max(0, width - vis) // 2
    pad_right = max(0, width - vis) - pad_left
    if fill_prefix:
        return f"{fill_prefix}{' ' * pad_left}{clipped}{fill_prefix}{' ' * pad_right}{fill_reset}"
    return f"{' ' * pad_left}{clipped}{' ' * pad_right}{fill_reset}"


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


def get_header_row(L=None):
    L = _resolve_width(L)
    from hecos.core.system.version import get_version_string
    titolo = f" {get_version_string()} "
    if len(titolo) > L:
        titolo = titolo[:L]
    return f"\033[46m\033[30m{titolo.center(L)}\033[0m"


def get_system_menu_row(L=None):
    L = _resolve_width(L)
    comandi = (
        f" {translator.t('menu_help')} | {translator.t('menu_models')} | "
        f"{translator.t('menu_persona')} | {translator.t('menu_mic')} | "
        f"{translator.t('menu_refresh')} | {translator.t('menu_voice')} | "
        f"{translator.t('menu_config')} | PTT (F8) | {translator.t('menu_reboot')} "
    )
    if visible_width(comandi) > L:
        comandi = " F1..F4: Menu | F5: Ref | F6: Voice | F7: Hub | F8: PTT | F9: Reb "
    clipped = clip_ansi(comandi, L)
    vis = visible_width(clipped)
    pad_l = max(0, L - vis) // 2
    pad_r = max(0, L - vis) - pad_l
    return f"{Style.DIM}{' ' * pad_l}{clipped}{' ' * pad_r}{Style.RESET_ALL}"


def get_status_bar(config, voice_status, listening_status, system_status, L=None, ptt_status=False):
    L = _resolve_width(L)
    from hecos.app.model_manager import ModelManager
    try:
        _, model_eff = ModelManager.get_effective_model_info(config)
    except Exception:
        model_eff = "N/D"

    ai_conf = config.get('ai') or {}
    raw_soul = ai_conf.get('active_personality') or 'N/D'
    soul = str(raw_soul).replace('.yaml', '').strip() or 'N/D'

    mic_str = "ON" if listening_status else f"{Fore.RED}OFF{Fore.WHITE}"
    spk_str = "ON" if voice_status else f"{Fore.RED}OFF{Fore.WHITE}"
    ptt_str = "ON" if ptt_status else f"{Fore.RED}OFF{Fore.WHITE}"

    status_translated = translate_status(system_status)
    status_color = get_status_color(system_status)
    info_status = translator.t("system_status", status="{S}").replace(
        "{S}", f"{status_color}{status_translated}{Fore.WHITE}"
    )
    header_mod = translator.t("header_model")
    header_ani = translator.t("header_soul")
    header_mic = translator.t("header_mic")
    header_voc = translator.t("header_voice")

    def _build_info(mod_str: str, soul_str: str) -> str:
        return (
            f" {info_status} | {header_mod}: {mod_str} | {header_ani}: {soul_str} | "
            f"{header_mic}: {mic_str} | {header_voc}: {spk_str} | PTT: {ptt_str} "
        )

    info_str = _build_info(str(model_eff), soul)

    # Smart shortening of long model / soul names so right-hand flags never get cut off
    if visible_width(info_str) > L:
        overflow = visible_width(info_str) - L
        mod_s = str(model_eff)
        if len(mod_s) > 16:
            keep = max(12, len(mod_s) - overflow - 1)
            mod_s = mod_s[:keep] + "…"
            info_str = _build_info(mod_s, soul)
        if visible_width(info_str) > L and len(soul) > 12:
            overflow2 = visible_width(info_str) - L
            keep_s = max(8, len(soul) - overflow2 - 1)
            info_str = _build_info(mod_s, soul[:keep_s] + "…")

    clipped = clip_ansi(info_str, L)
    # Re-apply Back.BLUE + Fore.WHITE because clip_ansi appends \033[0m
    if clipped.endswith("\033[0m"):
        clipped = clipped[:-4]
    vis_len = visible_width(clipped)
    p_left = max(0, L - vis_len) // 2
    p_right = max(0, L - vis_len) - p_left
    return f"{Back.BLUE}{Fore.WHITE}{' ' * p_left}{clipped}{Back.BLUE}{Fore.WHITE}{' ' * p_right}{Style.RESET_ALL}"


def get_ptt_hint_row(L=None, system_status="READY", ptt_status=False):
    L = _resolve_width(L)
    if "LISTENING" in str(system_status).upper() or "RECORDING" in str(system_status).upper():
        rec_text = " 🔴 RECORDING... "
        vis = visible_width(rec_text)
        p_left = max(0, L - vis) // 2
        p_right = max(0, L - vis) - p_left
        return f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{' ' * p_left}{rec_text}{' ' * p_right}{Style.RESET_ALL}"
    elif ptt_status:
        hint_text = clip_ansi(f" {translator.t('ptt_hint')} ", L)
        vis = visible_width(hint_text)
        p_left = max(0, L - vis) // 2
        p_right = max(0, L - vis) - p_left
        return f"{Fore.YELLOW}{' ' * p_left}{hint_text}{' ' * p_right}{Style.RESET_ALL}"
    else:
        return f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}"


def get_hardware_row(config=None, dashboard_mod=None, L=None):
    """Returns the formatted string for the hardware row (CPU, RAM, VRAM, backend)."""
    L = _resolve_width(L)

    if dashboard_mod is None:
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")

    dsb_config = config.get("plugins", {}).get("DASHBOARD", {}) if config else {}
    col_dsb = dsb_config.get("console_dashboard_enabled", True)
    col_tel = dsb_config.get("console_telemetry_enabled", True)

    if not col_dsb or not dashboard_mod:
        return f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}"

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
            display_status = "CLOUD" if backend_status == "CLOUD" else translator.t("ready")
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
            info_hw_raw = translator.t(
                "hardware_line",
                cpu=cpu_bar,
                ram=ram_bar,
                gpu=stats.get('gpu_load', 'N/D'),
                vram=vram,
                backend=f"{status_color}{display_status}{Style.RESET_ALL}",
            )
        else:
            info_hw_raw = (
                f" TELEMETRY: {Fore.LIGHTBLACK_EX}NOT ACTIVE{Style.RESET_ALL} | "
                f"BACKEND AI: {status_color}{display_status}{Style.RESET_ALL} "
            )

        clipped = clip_ansi(info_hw_raw, L)
        vis_len = visible_width(clipped)
        pad_left = max(0, L - vis_len) // 2
        pad_right = max(0, L - vis_len) - pad_left
        return f"{Fore.CYAN}{' ' * pad_left}{clipped}{' ' * pad_right}{Style.RESET_ALL}"

    except Exception as e:
        err_raw = clip_ansi(f"-- HARDWARE ERROR: {e} --", L)
        vis_len = visible_width(err_raw)
        pad_left = max(0, L - vis_len) // 2
        pad_right = max(0, L - vis_len) - pad_left
        return f"{Fore.RED}{' ' * pad_left}{err_raw}{' ' * pad_right}{Style.RESET_ALL}"


def show_web_access_info(config):
    """Prints Web UI access links strictly inside Zone 2 (Body)."""
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

    vp = get_viewport()
    L = vp.usable_width
    inner_w = max(20, L - 2)

    border_color = Fore.CYAN
    title_color = Fore.YELLOW
    label_color = Fore.WHITE

    box_lines = []
    box_lines.append(f"{border_color}┌{'─' * inner_w}┐{RESET}")

    title_text = "WEB INTERFACE ACCESS"
    pad = max(0, inner_w - len(title_text)) // 2
    pad_r = max(0, inner_w - len(title_text)) - pad
    box_lines.append(
        f"{border_color}│{RESET}{' ' * pad}{title_color}{title_text[:inner_w]}{RESET}{' ' * pad_r}{border_color}│{RESET}"
    )
    box_lines.append(f"{border_color}├{'─' * inner_w}┤{RESET}")

    for label, url_path in [("Chat:  ", "/chat"), ("Config:", "/hecos/config/ui"), ("Drive: ", "/drive")]:
        left_part = clip_ansi(f"  • {label_color}{label}{RESET} {base_url}{url_path}", inner_w)
        vis_l = visible_width(left_part)
        padding = max(0, inner_w - vis_l)
        box_lines.append(f"{border_color}│{RESET}{left_part}{' ' * padding}{border_color}│{RESET}")

    box_lines.append(f"{border_color}└{'─' * inner_w}┘{RESET}")
    box_lines.append("")

    vp.print_body("\n".join(box_lines))
