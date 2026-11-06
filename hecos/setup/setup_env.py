"""
Hecos Setup - Environment, Dependencies and Autostart Setup
Handles Python runtime validation, dependency installations from pyproject.toml,
autostart scripting, system language configuration, and the unattended onboarding orchestrator.
"""

import os
import sys
import glob
import re
import importlib
import subprocess
from typing import List, Optional

from .utils import (
    CWD, PIPER_DIR, SYSTEM_CONFIG_PATH, 
    AUDIO_CONFIG_PATH, safe_replace_yaml
)
from .i18n import T, set_ui_lang
from .setup_piper import download_piper_engine, download_voice


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
    for pkg in ["pydantic", "yaml", "litellm", "pystray"]:
        try:
            importlib.import_module(pkg.replace("-", "_").replace(" ", "_"))
        except ImportError:
            missing.append(pkg)

    if missing:
        print(T("deps_err", deps=", ".join(missing)))
        return False
    print(T("deps_ok"))
    print()
    return True


def install_dependencies() -> bool:
    """Installs required packages dynamically parsed from pyproject.toml or fallback list."""
    print(T("install_deps"))

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    except Exception as e:
        print(f"[-] Warning: Failed to upgrade pip/setuptools: {e}")

    packages: List[str] = []
    toml_path = os.path.join(CWD, "pyproject.toml")
    if os.path.exists(toml_path):
        try:
            with open(toml_path, "r", encoding="utf-8") as f:
                content = f.read()
            deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if deps_match:
                packages.extend(re.findall(r'"([^"]+)"', deps_match.group(1)))

            service_match = re.search(r'service\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if service_match:
                packages.extend(re.findall(r'"([^"]+)"', service_match.group(1)))
        except Exception as e:
            print(f"[-] Warning: Failed to parse pyproject.toml: {e}")

    if not packages:
        print("[-] Warning: Could not parse dependencies from pyproject.toml! Using fallback list...")
        packages = [
            "pydantic>=2.0", "pyyaml", "litellm", "tenacity", "babel", "holidays",
            "requests", "icalendar", "python-vlc", "dateparser", "apscheduler",
            "pyautogui", "pygetwindow", "pytesseract", "opencv-python",
            "pywinauto", "playwright", "pywin32", "pystray", "pillow", "customtkinter", "qrcode",
            "psutil", "flask", "flask-login", "cryptography", "pynput", "SpeechRecognition", "PyAudio", "fastembed", "soundfile",
        ]

    cmd = [sys.executable, "-m", "pip", "install"] + packages
    try:
        subprocess.check_call(cmd)

        # Install Playwright Chromium binaries automatically
        try:
            print("[*] Installing Playwright browser binaries...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        except Exception as e:
            print(f"[-] Warning: Failed to install Playwright binaries: {e}")

        return True
    except Exception as e:
        print(f"[-] Error: {e}")
        return False


def enable_autostart() -> bool:
    """Configures system startup scripts for Hecos background tray."""
    if os.name == 'nt':
        script = os.path.join("scripts", "windows", "setup", "ENABLE_TRAY_AUTOSTART.bat")
    else:
        script = os.path.join("scripts", "linux", "setup", "ENABLE_TRAY_AUTOSTART.sh")

    script_path = os.path.join(CWD, script)
    if not os.path.exists(script_path):
        print(f"[-] {script} not found.")
        return False

    print("[*] Configuring Hecos Autostart...")
    env = os.environ.copy()

    try:
        if os.name == 'nt':
            result = subprocess.run(["cmd", "/c", script_path, "--silent"], env=env, capture_output=True, text=True)
        else:
            result = subprocess.run(["bash", script_path, "--silent"], env=env, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"[-] Error: {e}")
        return False


def start_tray() -> None:
    """Launches the Hecos system tray process."""
    if os.name == 'nt':
        tray_root = os.path.join(os.path.splitdrive(CWD)[0] or "C:", os.sep, "Hecos-Tray")
        script_path = os.path.join(tray_root, "START_HECOS_TRAY_WIN.bat")
        if os.path.exists(script_path):
            subprocess.Popen(["cmd", "/c", "start", "", script_path], cwd=tray_root)
    else:
        tray_root = os.path.join(os.path.expanduser("~"), "Hecos-Tray")
        script_path = os.path.join(tray_root, "START_HECOS_TRAY_LINUX.sh")
        if os.path.exists(script_path):
            subprocess.Popen(["bash", script_path], cwd=tray_root, start_new_session=True)


def auto_fix_piper_path() -> bool:
    """Locates piper executable and models on disk and writes them to audio.yaml."""
    print(T("piper_check"))

    if not os.path.exists(AUDIO_CONFIG_PATH):
        print("[-] audio.yaml missing.")
        return False

    piper_exe = os.path.join(PIPER_DIR, "piper.exe") if os.name == 'nt' else os.path.join(PIPER_DIR, "piper")
    if not os.path.exists(piper_exe):
        piper_exe = None

    onnx_models = glob.glob(os.path.join(PIPER_DIR, "*.onnx"))
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
        print(f"[-] Could not update {os.path.basename(SYSTEM_CONFIG_PATH)}")


def unattended_onboarding(target_voices: Optional[List[str]] = None) -> bool:
    """Executes the full automated setup flow without interactive prompts."""
    print("=" * 60)
    print(f"  {T('onboarding_header')}")
    print("=" * 60)
    print()

    # Step 1: Environment
    print(f"[*] {T('step_env')}")
    if not check_python_version():
        return False

    # Step 2: Dependencies
    print(f"[*] {T('step_env')}")
    install_dependencies()

    # Step 3: Piper Engine & Voices
    print("\n[*] Piper TTS Engine")
    download_piper_engine()

    if target_voices:
        print(f"\n[*] {T('step_voice')} ({len(target_voices)} voices)")
        for v_key in target_voices:
            download_voice(v_key)

    # Step 3.5: External Dependencies
    print("\n[*] Checking External Dependencies...")
    try:
        from hecos.core.ext_deps import check_all_required
        check_all_required()
    except Exception as e:
        print(f"[-] Could not check external dependencies: {e}")

    # Step 4: Fixes
    print("\n[*] " + T('step_finish'))
    auto_fix_piper_path()

    # Step 5: Autostart Link
    print("\n[*] Setting up System Infrastructure...")
    enable_autostart()

    # Step 6: Launch Tray
    print("\n[*] Launching Hecos Tray Icon...")
    start_tray()

    print("\n" + "=" * 60)
    print(f"  {T('onboarding_done')}")
    print("=" * 60)
    return True

