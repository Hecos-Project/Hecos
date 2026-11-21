"""
Hecos Setup - Entry Point
Supports interactive CLI menu, unattended install, diagnostics (doctor),
dependency bootstrap, web setup wizard, uninstaller, and silent health check.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

from .i18n import set_ui_lang
from .utils import get_current_system_lang, refresh_tray_dir


def _extract_flag_value(argv: List[str], flag: str) -> Optional[str]:
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


def main(argv: Optional[List[str]] = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    # Sync initial language
    initial_lang = get_current_system_lang()
    set_ui_lang(initial_lang)

    # Optional explicit --tray-dir handoff from Tray or batch scripts
    tray_dir_arg = _extract_flag_value(args, "--tray-dir")
    if tray_dir_arg:
        os.environ["HECOS_TRAY_DIR"] = tray_dir_arg
        refresh_tray_dir(override=tray_dir_arg)

    standalone = "--standalone" in args

    # Best-effort registration of Core location in shared install.toml
    # (skipped in --standalone mode because we are running from a temp bootstrap dir)
    if not standalone and "--auto" not in args and "--uninstall" not in args:
        try:
            from .setup_env import register_installation
            register_installation(tray_override=tray_dir_arg)
        except Exception:
            pass

    # --- Silent health check (used by run scripts) ---
    if "--auto" in args:
        from .engine import check_dependencies, check_python_version
        devnull = open(os.devnull, "w")
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            py_ok = check_python_version()
            dep_ok = check_dependencies()
        finally:
            sys.stdout = old_stdout
            devnull.close()
        sys.exit(0 if (py_ok and dep_ok) else 1)

    # --- Uninstaller ---
    if "--uninstall" in args:
        if "--web" in args:
            from .web_ui import start_web_setup
            start_web_setup()
        else:
            from .uninstaller import GlobalUninstaller
            uninstaller = GlobalUninstaller()
            uninstaller.execute_full_uninstall()
            sys.exit(0)
        return

    # --- Generate / refresh constraints.txt lockfile ---
    if "lock" in args or "--freeze-lock" in args:
        from .deps_guard import generate_constraints_lock
        count, lock_path = generate_constraints_lock()
        print(f"[ OK ] Wrote {count} tested version constraints to: {lock_path}")
        sys.exit(0)

    # --- Dependency-only install (called by .bat / .sh bootstrap) ---
    if "--install-deps" in args or "deps" in args:
        from .setup_env import install_dependencies
        quiet = "--quiet" in args
        force = "--force" in args
        ok = install_dependencies(quiet=quiet, force=force)
        sys.exit(0 if ok else 1)

    # --- System Diagnostics (Doctor) ---
    if "doctor" in args or "--doctor" in args:
        from .cli_ui import render_doctor_report
        from .setup_env import run_doctor
        report = run_doctor()
        render_doctor_report(report)
        sys.exit(report["exit_code"])

    # --- Unattended / Full Install ---
    if "install" in args or "--install" in args or "--unattended" in args or "--silent" in args:
        from .setup_env import run_full_install
        skip_deps = "--skip-deps" in args
        no_tray = "--no-tray" in args
        res = run_full_install(
            target_voices=None,
            skip_deps=skip_deps,
            launch_tray=not no_tray,
            tray_override=tray_dir_arg,
        )
        sys.exit(res["exit_code"])

    # --- Unified Graphical Setup Wizard (App-Window / Web) ---
    if "--web" in args or "--gui" in args:
        from .web_ui import start_web_setup
        start_web_setup(standalone=standalone)
        return

    # --- Default / `menu`: Cyber CLI Wizard ---
    from .cli_ui import start_cli_wizard
    start_cli_wizard()


if __name__ == "__main__":
    main()
