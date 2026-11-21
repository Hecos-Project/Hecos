"""
Hecos Setup - Cyber-Styled Interactive CLI
Uses `rich` when installed (for cyber panels, tables, and colors), with a clean
ANSI fallback so the wizard always works even before dependencies are installed.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from . import i18n
from .engine import (
    auto_fix_piper_path,
    download_voice,
    enable_autostart,
    fetch_piper_voices,
    install_dependencies,
    register_installation,
    run_doctor,
    run_full_install,
    set_system_language,
)
from .i18n import T
from .install_registry import find_tray_dir, validate_install_path
from .utils import CWD

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    _HAS_RICH = True
    _CONSOLE = Console()
except Exception:
    _HAS_RICH = False
    _CONSOLE = None  # type: ignore[assignment]


# Fallback ANSI palette (matches shared Hecos cyber contract)
_CYAN = "\033[96m"
_MAGENTA = "\033[95m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_DIM = "\033[90m"
_RESET = "\033[0m"


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _get_core_version() -> str:
    ver_file = os.path.join(CWD, "hecos", "core", "version")
    try:
        if os.path.isfile(ver_file):
            return open(ver_file, "r", encoding="utf-8").read().strip()
    except Exception:
        pass
    return "unknown"


def _print_banner(subtitle: str = "") -> None:
    ver = _get_core_version()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    tray_dir, _ = find_tray_dir(CWD, os.environ.get("HECOS_TRAY_DIR"))
    path_ok, path_errs, path_warns = validate_install_path(CWD)

    if _HAS_RICH:
        info_lines = [
            f"[bold bright_magenta]HECOS CORE[/bold bright_magenta] [bright_cyan]v{ver}[/bright_cyan]  [dim]|[/dim]  [bright_cyan]{subtitle or T('header')}[/bright_cyan]",
            f"[dim]Core:[/dim] [white]{CWD}[/white]   [dim]Python:[/dim] [bright_green]{py_ver}[/bright_green]",
            f"[dim]Tray:[/dim] "
            + (f"[bright_green]{tray_dir}[/bright_green]" if tray_dir else "[yellow]Not detected[/yellow]"),
        ]
        if not path_ok:
            info_lines.append(f"[bold bright_red][FAIL] Path issue:[/bold bright_red] {'; '.join(path_errs)}")
        elif path_warns:
            info_lines.append(f"[yellow][WARN][/yellow] {'; '.join(path_warns)}")

        _CONSOLE.print(
            Panel(
                "\n".join(info_lines),
                border_style="bright_cyan",
                box=box.DOUBLE,
                padding=(0, 2),
            )
        )
    else:
        print(f"{_CYAN}{'=' * 72}{_RESET}")
        print(f"  {_MAGENTA}HECOS CORE v{ver}{_RESET}  |  {_CYAN}{subtitle or T('header')}{_RESET}")
        print(f"  {_DIM}Core:{_RESET} {CWD}   {_DIM}Python:{_RESET} {_GREEN}{py_ver}{_RESET}")
        tray_txt = f"{_GREEN}{tray_dir}{_RESET}" if tray_dir else f"{_YELLOW}Not detected{_RESET}"
        print(f"  {_DIM}Tray:{_RESET} {tray_txt}")
        if not path_ok:
            print(f"  {_RED}[FAIL] {'; '.join(path_errs)}{_RESET}")
        elif path_warns:
            print(f"  {_YELLOW}[WARN] {'; '.join(path_warns)}{_RESET}")
        print(f"{_CYAN}{'=' * 72}{_RESET}")


def render_doctor_report(report: Dict[str, Any]) -> None:
    """Render the system diagnostics report in cyber style."""
    checks: List[Dict[str, str]] = report.get("checks", [])

    if _HAS_RICH:
        table = Table(
            title="[bold bright_cyan]HECOS SYSTEM DIAGNOSTICS[/bold bright_cyan]",
            box=box.ROUNDED,
            border_style="bright_cyan",
            show_lines=False,
        )
        table.add_column("Component", style="bold white", width=20)
        table.add_column("Status", width=10, justify="center")
        table.add_column("Details", style="white")

        badge_map = {
            "ok": "[bold bright_green][ OK ][/bold bright_green]",
            "warn": "[bold yellow][WARN][/bold yellow]",
            "fail": "[bold bright_red][FAIL][/bold bright_red]",
        }
        for item in checks:
            table.add_row(
                item["name"],
                badge_map.get(item["status"], item["status"]),
                item["detail"],
            )
        _CONSOLE.print(table)
        if report.get("ok"):
            if report.get("has_warnings"):
                _CONSOLE.print("[yellow][WARN] Core is healthy, with optional items pending.[/yellow]")
            else:
                _CONSOLE.print("[bold bright_green][ OK ] All system checks passed![/bold bright_green]")
        else:
            _CONSOLE.print("[bold bright_red][FAIL] One or more critical checks failed. Run Full Setup or Quick Repair.[/bold bright_red]")
    else:
        print(f"\n{_CYAN}--- HECOS SYSTEM DIAGNOSTICS ---{_RESET}")
        color_map = {"ok": _GREEN, "warn": _YELLOW, "fail": _RED}
        tag_map = {"ok": "[ OK ]", "warn": "[WARN]", "fail": "[FAIL]"}
        for item in checks:
            col = color_map.get(item["status"], "")
            tag = tag_map.get(item["status"], "[ .. ]")
            print(f"  {col}{tag}{_RESET} {item['name']:<18} {item['detail']}")
        print()


def voice_selection_menu() -> None:
    voices = fetch_piper_voices()
    if not voices:
        print("[WARN] Could not fetch voices (offline or Hugging Face timeout).")
        return

    langs = sorted(
        list(set(v.get("language", {}).get("name_english", "Other") for v in voices.values()))
    )

    print(T("select_lang"))
    for i, l in enumerate(langs):
        print(f" {i + 1}) {l}")

    try:
        l_idx = int(input("\nSelect Language # --> ")) - 1
        if 0 <= l_idx < len(langs):
            selected_lang = langs[l_idx]
            v_in_lang = [
                (k, v)
                for k, v in voices.items()
                if v.get("language", {}).get("name_english") == selected_lang
            ]

            print(f"\n--- {selected_lang} ---")
            for i, (k, v) in enumerate(v_in_lang):
                print(f" {i + 1}) {v.get('name')} ({v.get('quality')}) [{k}]")

            v_idx = int(input("\nSelect Voice # --> ")) - 1
            if 0 <= v_idx < len(v_in_lang):
                download_voice(v_in_lang[v_idx][0])
    except (ValueError, IndexError):
        print(T("invalid_opt"))


def lang_selection_menu() -> None:
    print(T("select_lang"))
    print(f"({T('tip_lang_multilingual')})")
    print(" 1) English")
    print(" 2) Italiano")
    c = input("--> ").strip()
    if c == "1":
        set_system_language("en")
    elif c == "2":
        set_system_language("it")


def guided_onboarding() -> None:
    _clear_screen()
    _print_banner(T("onboarding_header"))
    print()

    # Step 1: Language Select
    if _HAS_RICH:
        _CONSOLE.print(f"[bold bright_magenta]STEP 1/2[/bold bright_magenta] [bright_cyan]{T('step_lang')}[/bright_cyan]")
    else:
        print(f"{_MAGENTA}[STEP 1/2]{_RESET} {_CYAN}{T('step_lang')}{_RESET}")
    lang_selection_menu()
    print()

    # Step 2: Full Installation (voices can be configured anytime in Hecos WebUI)
    if _HAS_RICH:
        _CONSOLE.print(f"[bold bright_magenta]STEP 2/2[/bold bright_magenta] [bright_cyan]{T('step_install').upper()}[/bright_cyan]\n")
    else:
        print(f"{_MAGENTA}[STEP 2/2]{_RESET} {_CYAN}{T('step_install').upper()}{_RESET}\n")

    run_full_install(target_voices=None)
    input(f"\n{T('press_enter')}")


def quick_repair() -> None:
    _clear_screen()
    _print_banner("QUICK REPAIR")
    print()
    install_dependencies(force=True)
    auto_fix_piper_path()
    register_installation()
    enable_autostart()
    print()
    render_doctor_report(run_doctor())
    input(f"\n{T('press_enter')}")


def start_cli_wizard() -> None:
    while True:
        _clear_screen()
        _print_banner()
        print()

        if _HAS_RICH:
            menu = Table.grid(padding=(0, 2))
            menu.add_column(style="bold bright_cyan", width=4)
            menu.add_column(style="white")
            menu.add_row("1)", "[bold]Start Web Setup Wizard[/bold] [bright_green](Recommended — local browser UI)[/bright_green]")
            menu.add_row("2)", f"{T('onboarding_header')} (CLI) [dim](Headless / advanced users)[/dim]")
            menu.add_row("3)", "System Diagnostics [dim](Doctor — check Python, deps, paths, Tray)[/dim]")
            menu.add_row("4)", "Quick Repair [dim](Reinstall missing deps, fix Piper & autostart)[/dim]")
            menu.add_row("5)", f"Toggle Setup Language [dim](Current: {i18n.UI_LANG.upper()})[/dim]")
            menu.add_row("0)", "[dim]Exit[/dim]")
            _CONSOLE.print(menu)
        else:
            print(f"  {_CYAN}1){_RESET} Start Web Setup Wizard {_GREEN}(Recommended - local browser UI){_RESET}")
            print(f"  {_CYAN}2){_RESET} {T('onboarding_header')} (CLI - headless / advanced)")
            print(f"  {_CYAN}3){_RESET} System Diagnostics (Doctor)")
            print(f"  {_CYAN}4){_RESET} Quick Repair (Deps, Piper paths, Autostart)")
            print(f"  {_CYAN}5){_RESET} Toggle Setup Language (Current: {i18n.UI_LANG.upper()})")
            print(f"  {_DIM}0) Exit{_RESET}")

        try:
            choice = input("\nSelect option (0-5) --> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{T('exit_msg')}")
            break

        if choice == "1":
            from .web_ui import start_web_setup
            start_web_setup()
            input(f"\n{T('press_enter')}")
        elif choice == "2":
            guided_onboarding()
        elif choice == "3":
            _clear_screen()
            _print_banner("SYSTEM DIAGNOSTICS")
            print()
            render_doctor_report(run_doctor())
            input(f"\n{T('press_enter')}")
        elif choice == "4":
            quick_repair()
        elif choice == "5":
            i18n.set_ui_lang("it" if i18n.UI_LANG == "en" else "en")
        elif choice == "0":
            print(T("exit_msg"))
            break
        else:
            print(T("invalid_opt"))
            input(f"\n{T('press_enter')}")
