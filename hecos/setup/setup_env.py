"""
Hecos Setup - Environment, Dependencies, Diagnostics and Autostart Setup
Handles Python runtime validation, dependency installations from pyproject.toml
(via tomllib), autostart scripting, install registry updates, system diagnostics,
and the onboarding orchestrator.
"""

from __future__ import annotations

import glob
import importlib
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .deps_guard import (
    CONSTRAINTS_PATH,
    ensure_build_tools,
    find_missing_dependencies,
    generate_constraints_lock,
    is_playwright_chromium_installed,
)
from .i18n import T, set_ui_lang
from .install_registry import (
    find_tray_dir,
    get_registry_path,
    read_registry,
    update_registry,
    validate_install_path,
)
from .setup_piper import download_piper_engine, download_voice
from .utils import (
    AUDIO_CONFIG_PATH,
    CWD,
    PIPER_DIR,
    SYSTEM_CONFIG_PATH,
    parse_pyproject_dependencies,
    refresh_tray_dir,
    safe_replace_yaml,
)


# Packages that are strictly required for Hecos Core to boot.
# Used for resilient staged installation so a failing optional native wheel
# (e.g. PyAudio on Linux without portaudio19-dev) does not block core setup.
ESSENTIAL_PACKAGE_PREFIXES = (
    "pydantic",
    "pyyaml",
    "tomli-w",
    "litellm",
    "tenacity",
    "babel",
    "holidays",
    "requests",
    "psutil",
    "flask",
    "flask-login",
    "flask-compress",
    "cryptography",
    "rich",
    "beautifulsoup4",
)

FALLBACK_PACKAGES = [
    "pydantic>=2.0",
    "pyyaml",
    "tomli-w",
    "litellm",
    "tenacity",
    "babel",
    "holidays",
    "requests",
    "psutil",
    "flask",
    "flask-login",
    "flask-compress",
    "cryptography",
    "rich>=13.0.0",
    "beautifulsoup4",
    "pypdf",
    "python-docx",
    "SpeechRecognition",
    "PyAudio",
    "fastembed",
    "lancedb>=0.33.0",
    "sentence-transformers",
    "sounddevice",
    "pygame",
    "GPUtil",
    "numpy",
    "soundfile",
    "pynput",
    "playwright>=1.40.0",
    "pystray",
    "pillow",
    "customtkinter",
    "qrcode",
]


def _pkg_base_name(spec: str) -> str:
    return re.split(r"[\[\];>=<~!@]", spec)[0].strip().lower()


def check_python_version() -> bool:
    """Verifies that the running Python interpreter meets minimum version requirements (>=3.10)."""
    print(T("python_check"))
    v = sys.version_info
    v_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(T("python_err", v=v_str))
        return False
    print(T("python_ok", v=v_str, path=sys.executable))
    print()
    return True


def check_dependencies() -> bool:
    """Checks whether foundational core dependencies are importable."""
    print(T("deps_check"))
    missing = []
    for label, mod in [
        ("pydantic", "pydantic"),
        ("pyyaml", "yaml"),
        ("litellm", "litellm"),
        ("flask", "flask"),
        ("requests", "requests"),
        ("psutil", "psutil"),
    ]:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(label)

    if missing:
        print(T("deps_err", deps=", ".join(missing)))
        return False
    print(T("deps_ok"))
    print()
    return True


def install_dependencies(
    quiet: bool = False,
    force: bool = False,
    use_constraints: bool = True,
) -> bool:
    """Smart, reproducible dependency installer driven by pyproject.toml + constraints.txt.

    Behavior:
      - Fast pre-pip check (<0.2s): if all declared dependencies already satisfy
        pyproject.toml (and force=False), skips pip completely so existing working
        packages are NEVER unnecessarily touched or upgraded.
      - Never blindly upgrades pip/setuptools/wheel on every launch (avoids breaking
        setuptools >=82 jumps).
      - Installs ONLY missing/outdated packages (or all when force=True) using a
        3-tier resilient strategy:
          Tier 1: `pip install -c constraints.txt <targets>` (exact tested versions)
          Tier 2: `pip install <targets>` (pyproject.toml safe upper-bounded ranges)
          Tier 3: Staged install (essential packages first, then optional individually)
      - Only runs `playwright install chromium` when Chromium binaries are missing
        (or when force=True).
    """
    toml_path = os.path.join(CWD, "pyproject.toml")
    all_packages = parse_pyproject_dependencies(toml_path, extras=("service",))

    if not all_packages:
        print("[WARN] Could not parse dependencies from pyproject.toml. Using fallback list...")
        all_packages = list(FALLBACK_PACKAGES)
        if os.name == "nt":
            all_packages.append("pywin32")

    satisfied, missing = find_missing_dependencies(toml_path, extras=("service",))

    if not force and not missing:
        print(f"[ OK ] All {len(satisfied)} required dependencies are already satisfied (skipping pip).")
        _ensure_playwright_chromium(force=False)
        return True

    print(T("install_deps"))
    ensure_build_tools(quiet=quiet)

    targets = all_packages if force else missing
    if force:
        print(f"[ .. ] Repair/verify mode: checking {len(targets)} packages from pyproject.toml...")
    else:
        print(f"[ .. ] Installing {len(targets)} missing/outdated package(s) ({len(satisfied)} already satisfied)...")

    pip_base = [sys.executable, "-m", "pip", "install"]
    if quiet:
        pip_base.append("--quiet")

    has_constraints = use_constraints and os.path.isfile(CONSTRAINTS_PATH)
    batch_ok = False

    # Tier 1: Reproducible install using tested constraints.txt
    if has_constraints:
        print(f"[ .. ] Using tested version constraints: {os.path.basename(CONSTRAINTS_PATH)}")
        try:
            subprocess.check_call(pip_base + ["-c", CONSTRAINTS_PATH] + targets)
            batch_ok = True
        except subprocess.CalledProcessError as exc:
            print(f"[WARN] Locked constraints install returned exit code {exc.returncode}.")
            print("[ .. ] Falling back to safe version ranges from pyproject.toml...")

    # Tier 2: Safe version ranges from pyproject.toml (no lockfile constraints)
    if not batch_ok:
        try:
            subprocess.check_call(pip_base + targets)
            batch_ok = True
        except subprocess.CalledProcessError as exc:
            print(f"[WARN] Batch pip install returned exit code {exc.returncode}.")
            print("[ .. ] Switching to resilient staged install (essential packages first)...")

    failed_essential: List[str] = []
    failed_optional: List[str] = []

    # Tier 3: Staged essential -> individual optional packages
    if not batch_ok:
        essential = [p for p in targets if _pkg_base_name(p) in ESSENTIAL_PACKAGE_PREFIXES]
        optional = [p for p in targets if _pkg_base_name(p) not in ESSENTIAL_PACKAGE_PREFIXES]

        if essential:
            try:
                subprocess.check_call(pip_base + essential)
            except subprocess.CalledProcessError:
                for pkg in essential:
                    rc = subprocess.call(pip_base + [pkg])
                    if rc != 0:
                        failed_essential.append(pkg)

        for pkg in optional:
            rc = subprocess.call(pip_base + [pkg])
            if rc != 0:
                failed_optional.append(pkg)

        if failed_optional:
            print("[WARN] Some optional packages could not be installed:")
            for pkg in failed_optional:
                print(f"       - {pkg}")
            if os.name != "nt" and any(_pkg_base_name(p) == "pyaudio" for p in failed_optional):
                print("       Hint (Linux): install system portaudio headers (e.g. sudo apt install portaudio19-dev)")

        if failed_essential:
            print("[FAIL] Essential packages failed to install:")
            for pkg in failed_essential:
                print(f"       - {pkg}")
            return False

    _ensure_playwright_chromium(force=force)
    print("[ OK ] Python dependencies ready.")
    return True


def _ensure_playwright_chromium(force: bool = False) -> None:
    """Install Playwright Chromium binaries only when missing (or in force repair mode)."""
    try:
        importlib.import_module("playwright")
    except ImportError:
        print("[WARN] Playwright not installed; skipping Chromium binary setup.")
        return

    if not force and is_playwright_chromium_installed():
        print("[ OK ] Playwright Chromium binaries already installed (skipping download).")
        return

    try:
        print("[ .. ] Installing Playwright Chromium browser binaries...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    except Exception as e:
        print(f"[WARN] Failed to install Playwright Chromium binaries (can retry later): {e}")


def register_installation(tray_override: Optional[str] = None) -> str:
    """Update shared install.toml with Core path, Python executable, and detected Tray."""
    tray_dir, _ = refresh_tray_dir(override=tray_override)
    fields: Dict[str, Optional[str]] = {
        "core_path": CWD,
        "core_python": sys.executable,
    }
    if tray_dir:
        fields["tray_path"] = tray_dir
    return update_registry(**fields)


def enable_autostart() -> bool:
    """Configures system startup scripts for Hecos background tray."""
    if os.name == "nt":
        script = os.path.join("scripts", "windows", "setup", "ENABLE_TRAY_AUTOSTART.bat")
    else:
        script = os.path.join("scripts", "linux", "setup", "ENABLE_TRAY_AUTOSTART.sh")

    script_path = os.path.join(CWD, script)
    if not os.path.exists(script_path):
        print(f"[WARN] {script} not found.")
        return False

    print("[ .. ] Configuring Hecos Autostart...")
    env = os.environ.copy()
    tray_dir, _ = find_tray_dir(CWD, env.get("HECOS_TRAY_DIR"))
    if tray_dir:
        env["HECOS_TRAY_DIR"] = tray_dir

    try:
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", script_path, "--silent"],
                env=env,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                ["bash", script_path, "--silent"],
                env=env,
                capture_output=True,
                text=True,
            )

        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())

        return result.returncode == 0
    except Exception as e:
        print(f"[WARN] Error configuring autostart: {e}")
        return False


def start_tray() -> bool:
    """Launches the Hecos system tray process using the shared Tray locator."""
    tray_root, _ = find_tray_dir(CWD, os.environ.get("HECOS_TRAY_DIR"))
    if not tray_root:
        print("[WARN] Hecos Tray not found; skipping Tray auto-launch.")
        return False

    if os.name == "nt":
        script_path = os.path.join(tray_root, "START_HECOS_TRAY_WIN.bat")
        if os.path.exists(script_path):
            subprocess.Popen(["cmd", "/c", "start", "", script_path, "--silent"], cwd=tray_root)
            return True
    else:
        script_path = os.path.join(tray_root, "START_HECOS_TRAY_LINUX.sh")
        if os.path.exists(script_path):
            subprocess.Popen(["bash", script_path], cwd=tray_root, start_new_session=True)
            return True

    print(f"[WARN] Tray launcher script not found inside {tray_root}.")
    return False


def auto_fix_piper_path() -> bool:
    """Locates piper executable and models on disk and writes them to audio.yaml."""
    print(T("piper_check"))

    if not os.path.exists(AUDIO_CONFIG_PATH):
        print("[WARN] audio.yaml missing.")
        return False

    piper_exe = (
        os.path.join(PIPER_DIR, "piper.exe")
        if os.name == "nt"
        else os.path.join(PIPER_DIR, "piper")
    )
    if not os.path.exists(piper_exe):
        piper_exe = None

    onnx_models = sorted(glob.glob(os.path.join(PIPER_DIR, "*.onnx")))
    onnx_model = onnx_models[0] if onnx_models else None

    changes = 0
    if piper_exe and safe_replace_yaml(AUDIO_CONFIG_PATH, "piper_path", piper_exe):
        changes += 1
    if onnx_model and safe_replace_yaml(AUDIO_CONFIG_PATH, "onnx_model", onnx_model):
        changes += 1

    if changes > 0:
        print(T("piper_fixed"))
    else:
        print(T("piper_ok"))
    print()
    return True


def set_system_language(lang_code: str) -> None:
    """Updates language setting in system.yaml and updates UI translation context."""
    if safe_replace_yaml(SYSTEM_CONFIG_PATH, "language", lang_code):
        print(T("lang_fixed", lang=lang_code))
        set_ui_lang(lang_code)
    else:
        print(f"[WARN] Could not update {os.path.basename(SYSTEM_CONFIG_PATH)}")


def run_doctor() -> Dict[str, Any]:
    """Run comprehensive diagnostics on the Hecos Core installation."""
    checks: List[Dict[str, str]] = []

    # 1. Core directory & version
    ver_file = os.path.join(CWD, "hecos", "core", "version")
    core_ver = None
    if os.path.isfile(ver_file):
        try:
            core_ver = open(ver_file, "r", encoding="utf-8").read().strip()
        except Exception:
            core_ver = "unknown"
    checks.append({
        "name": "Hecos Core",
        "status": "ok" if core_ver else "fail",
        "detail": f"v{core_ver} at {CWD}" if core_ver else f"version file missing in {CWD}",
    })

    # 2. Install path safety
    path_ok, path_errs, path_warns = validate_install_path(CWD)
    if not path_ok:
        checks.append({"name": "Install Path", "status": "fail", "detail": "; ".join(path_errs)})
    elif path_warns:
        checks.append({"name": "Install Path", "status": "warn", "detail": "; ".join(path_warns)})
    else:
        checks.append({"name": "Install Path", "status": "ok", "detail": f"Clean safe path ({CWD})"})

    # 3. Python runtime & tkinter
    v = sys.version_info
    v_str = f"{v.major}.{v.minor}.{v.micro}"
    py_ok = (v.major == 3 and v.minor >= 10)
    tk_ok = False
    try:
        importlib.import_module("tkinter")
        tk_ok = True
    except Exception:
        tk_ok = False
    py_detail = f"Python {v_str} ({sys.executable}) | tkinter: {'yes' if tk_ok else 'no'}"
    if not py_ok:
        checks.append({"name": "Python Runtime", "status": "fail", "detail": py_detail + " (requires 3.10+)"})
    elif v.minor != 11:
        checks.append({"name": "Python Runtime", "status": "warn", "detail": py_detail + " (3.11 recommended)"})
    else:
        checks.append({"name": "Python Runtime", "status": "ok", "detail": py_detail})

    # 4. Install registry
    reg_path = get_registry_path()
    reg_data = read_registry(reg_path)
    if reg_data.get("core_path"):
        checks.append({
            "name": "Install Registry",
            "status": "ok",
            "detail": f"{reg_path} (core={reg_data.get('core_path')})",
        })
    else:
        checks.append({
            "name": "Install Registry",
            "status": "warn",
            "detail": f"Not registered yet ({reg_path})",
        })

    # 5. Tray detection
    tray_dir, tray_ver_folder = find_tray_dir(CWD, os.environ.get("HECOS_TRAY_DIR"))
    if tray_dir:
        t_ver_file = os.path.join(tray_dir, "tray", "version")
        t_ver = ""
        try:
            t_ver = open(t_ver_file, "r", encoding="utf-8").read().strip()
        except Exception:
            pass
        status = "warn" if tray_ver_folder else "ok"
        detail = f"v{t_ver} at {tray_dir}" if t_ver else tray_dir
        if tray_ver_folder:
            detail += " (versioned folder name; consider renaming to Hecos-Tray)"
        checks.append({"name": "Hecos Tray", "status": status, "detail": detail})
    else:
        checks.append({
            "name": "Hecos Tray",
            "status": "warn",
            "detail": "Not detected (optional; Core can still run via Global Launcher)",
        })

    # 6. Core dependencies
    key_mods = [
        ("pydantic", "pydantic"),
        ("pyyaml", "yaml"),
        ("litellm", "litellm"),
        ("flask", "flask"),
        ("requests", "requests"),
        ("psutil", "psutil"),
        ("cryptography", "cryptography"),
        ("rich", "rich"),
    ]
    missing_core = []
    for label, mod in key_mods:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing_core.append(label)
    if missing_core:
        checks.append({
            "name": "Core Packages",
            "status": "fail",
            "detail": f"Missing: {', '.join(missing_core)}",
        })
    else:
        checks.append({
            "name": "Core Packages",
            "status": "ok",
            "detail": f"All {len(key_mods)} essential modules importable",
        })

    # 7. Optional multimedia / AI packages
    opt_mods = [
        ("playwright", "playwright"),
        ("lancedb", "lancedb"),
        ("fastembed", "fastembed"),
        ("soundfile", "soundfile"),
        ("pyaudio", "pyaudio"),
        ("pynput", "pynput"),
    ]
    missing_opt = []
    for label, mod in opt_mods:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing_opt.append(label)
    if missing_opt:
        checks.append({
            "name": "Optional Packages",
            "status": "warn",
            "detail": f"Missing: {', '.join(missing_opt)}",
        })
    else:
        checks.append({
            "name": "Optional Packages",
            "status": "ok",
            "detail": f"All {len(opt_mods)} optional modules importable",
        })

    # 8. Piper TTS
    piper_exe = os.path.join(PIPER_DIR, "piper.exe" if os.name == "nt" else "piper")
    onnx_models = glob.glob(os.path.join(PIPER_DIR, "*.onnx"))
    if os.path.isfile(piper_exe) and onnx_models:
        checks.append({
            "name": "Piper TTS",
            "status": "ok",
            "detail": f"Binary present + {len(onnx_models)} voice model(s)",
        })
    elif os.path.isfile(piper_exe):
        checks.append({
            "name": "Piper TTS",
            "status": "warn",
            "detail": "Binary present, no .onnx voices downloaded yet",
        })
    else:
        checks.append({
            "name": "Piper TTS",
            "status": "warn",
            "detail": "Not installed yet (run Full Setup to download)",
        })

    # 9. Autostart
    if os.name == "nt":
        lnk = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\HecosTray.lnk")
        auto_ok = os.path.isfile(lnk)
    else:
        lnk = os.path.expanduser("~/.config/autostart/hecos-tray.desktop")
        auto_ok = os.path.isfile(lnk)
    checks.append({
        "name": "Tray Autostart",
        "status": "ok" if auto_ok else "warn",
        "detail": f"Configured ({lnk})" if auto_ok else "Not configured",
    })

    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    return {
        "ok": not has_fail,
        "has_warnings": has_warn,
        "exit_code": 1 if has_fail else 0,
        "checks": checks,
    }


def run_full_install(
    target_voices: Optional[List[str]] = None,
    skip_deps: bool = False,
    launch_tray: bool = True,
    tray_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Unified installation engine returning accurate status and exit codes (0/1/2).

    Exit codes:
      0 = Complete success
      2 = Core installed successfully, some optional steps had warnings
      1 = Critical step failed (Python incompatible or essential deps failed)
    """
    errors: List[str] = []
    warnings: List[str] = []

    print("=" * 64)
    print(f"  {T('onboarding_header')}")
    print("=" * 64)
    print()

    # Step 1: Python runtime check
    print("[1/6] Checking Python runtime...")
    if not check_python_version():
        errors.append("Incompatible Python version (3.10+ required).")
        return {"ok": False, "exit_code": 1, "errors": errors, "warnings": warnings}

    # Step 2: Core Python dependencies
    print(f"[2/6] {T('step_env')}...")
    if skip_deps:
        print("[ .. ] Skipping pip install (--skip-deps).")
    else:
        if not install_dependencies():
            errors.append("Failed to install essential Python dependencies.")
            return {"ok": False, "exit_code": 1, "errors": errors, "warnings": warnings}

    # Step 3: Piper TTS Engine & Voices
    print("\n[3/6] Piper TTS Engine & Voices...")
    if not download_piper_engine():
        warnings.append("Piper TTS engine could not be downloaded (offline or GitHub unreachable).")

    if target_voices:
        print(f"[ .. ] {T('step_voice')} ({len(target_voices)} voice(s))")
        for v_key in target_voices:
            if not download_voice(v_key):
                warnings.append(f"Voice download failed: {v_key}")

    # Step 4: External Dependencies
    print("\n[4/6] Checking External Dependencies...")
    try:
        from hecos.core.ext_deps import check_all_required
        check_all_required()
    except Exception as e:
        warnings.append(f"External dependency check skipped: {e}")
        print(f"[WARN] Could not check external dependencies: {e}")

    # Step 5: Configuration & Path Fixes
    print(f"\n[5/6] {T('step_finish')}...")
    auto_fix_piper_path()

    # Step 6: Registry, Autostart & Tray
    print("\n[6/6] Registering Installation & System Infrastructure...")
    try:
        reg_path = register_installation(tray_override=tray_override)
        print(f"[ OK ] Install registry updated: {reg_path}")
    except Exception as e:
        warnings.append(f"Could not update install registry: {e}")
        print(f"[WARN] Could not update install registry: {e}")

    tray_dir, _ = find_tray_dir(CWD, tray_override or os.environ.get("HECOS_TRAY_DIR"))
    if tray_dir:
        if not enable_autostart():
            warnings.append("Autostart shortcut could not be configured.")
        if launch_tray:
            print("[ .. ] Launching Hecos Tray Icon...")
            if not start_tray():
                warnings.append("Hecos Tray could not be auto-launched.")
    else:
        print("[WARN] Hecos Tray not detected; skipping Tray autostart & launch.")

    print("\n" + "=" * 64)
    if warnings:
        print(f"  {T('onboarding_done')} (with {len(warnings)} warning(s))")
        for w in warnings:
            print(f"  [WARN] {w}")
    else:
        print(f"  {T('onboarding_done')}")
    print("=" * 64)

    exit_code = 2 if warnings else 0
    return {"ok": True, "exit_code": exit_code, "errors": errors, "warnings": warnings}


def unattended_onboarding(target_voices: Optional[List[str]] = None) -> bool:
    """Backward-compatible wrapper returning True on full/partial success, False on failure."""
    res = run_full_install(target_voices=target_voices)
    return bool(res["ok"])
