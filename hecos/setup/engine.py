import os
import sys
import subprocess
import glob
import urllib.request
import importlib
import json
from .utils import (
    CWD, PIPER_DIR, PIPER_REPO_URL, SYSTEM_CONFIG_PATH, 
    AUDIO_CONFIG_PATH, VOICE_MAP, safe_replace_yaml
)
from .i18n import T, set_ui_lang

def check_python_version():
    print(T("python_check"))
    v = sys.version_info
    v_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(T("python_err", v=v_str))
        return False
    print(T("python_ok", v=v_str, path=sys.executable))
    print()
    return True

def check_dependencies():
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

def install_dependencies():
    print(T("install_deps"))
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    except Exception as e:
        print(f"[-] Warning: Failed to upgrade pip/setuptools: {e}")

    # Parse pyproject.toml dynamically to avoid hardcoded lists
    import re
    packages = []
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

def enable_autostart():
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

def start_tray():
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

def auto_fix_piper_path():
    print(T("piper_check"))

    if not os.path.exists(AUDIO_CONFIG_PATH):
        print("[-] audio.yaml missing.")
        return False

    # Check for piper exe
    piper_exe = os.path.join(PIPER_DIR, "piper.exe") if os.name == 'nt' else os.path.join(PIPER_DIR, "piper")
    if not os.path.exists(piper_exe): piper_exe = None
    
    # Check for any onnx
    onnx_models = glob.glob(os.path.join(PIPER_DIR, "*.onnx"))
    onnx_model = onnx_models[0] if onnx_models else None

    changes = 0
    if piper_exe and safe_replace_yaml(AUDIO_CONFIG_PATH, "piper_path", piper_exe): changes += 1
    if onnx_model and safe_replace_yaml(AUDIO_CONFIG_PATH, "onnx_model", onnx_model): changes += 1

    if changes > 0: print(T("piper_fixed"))
    else: print(T("piper_ok"))
    print()
    return True

def set_system_language(lang_code):
    if safe_replace_yaml(SYSTEM_CONFIG_PATH, "language", lang_code):
        print(T("lang_fixed", lang=lang_code))
        set_ui_lang(lang_code) # Sync UI language immediately
    else:
        print(f"[-] Could not update {os.path.basename(SYSTEM_CONFIG_PATH)}")

VOICES_CACHE = None

def fetch_piper_voices():
    global VOICES_CACHE
    if VOICES_CACHE: return VOICES_CACHE
    
    url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
    print("[*] Fetching available voices from Piper repository...", end=" ", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            VOICES_CACHE = json.loads(response.read().decode())
            print("Done.")
            return VOICES_CACHE
    except Exception as e:
        print(f"\n[-] Failed to fetch voices: {e}")
        return {}

def download_voice(voice_key):
    voices = fetch_piper_voices()
    if not voices or voice_key not in voices:
        print(f"[-] Voice {voice_key} not found in repository.")
        return False
        
    voice_data = voices[voice_key]
    os.makedirs(PIPER_DIR, exist_ok=True)
    
    # Base URL for HF
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    
    # Download all files listed for this voice (usually .onnx and .onnx.json)
    for rel_path in voice_data.get("files", {}):
        if not rel_path.endswith((".onnx", ".onnx.json")): continue
        
        filename = os.path.basename(rel_path)
        target_path = os.path.join(PIPER_DIR, filename)
        
        if os.path.exists(target_path):
            print(T("already_exists", filename=filename))
        else:
            print(T("downloading", filename=filename))
            final_url = base_url + rel_path
            try:
                def progress(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = int(block_num * block_size * 100 / total_size)
                        print(f"\r    {percent}% complete...", end="", flush=True)
                urllib.request.urlretrieve(final_url, target_path, reporthook=progress)
                print(f"\n" + T("success_dl", filename=filename))
            except Exception as e:
                print(f"\n" + T("err_dl", filename=filename, err=str(e)))
                return False

    # Update audio.yaml
    onnx_path = os.path.join(PIPER_DIR, f"{voice_key}.onnx")
    safe_replace_yaml(AUDIO_CONFIG_PATH, "onnx_model", onnx_path)
    return True



def download_piper_engine():
    import tempfile
    import shutil
    piper_exe = os.path.join(PIPER_DIR, "piper.exe") if os.name == 'nt' else os.path.join(PIPER_DIR, "piper")
    if os.path.exists(piper_exe):
        print("[*] Piper engine is already installed.")
        return True

    print("[*] Downloading Piper TTS engine...")
    os.makedirs(PIPER_DIR, exist_ok=True)
    
    version = "2023.11.14-2"
    if os.name == 'nt':
        filename = "piper_windows_amd64.zip"
        is_zip = True
    else:
        filename = "piper_linux_x86_64.tar.gz"
        is_zip = False
        
    url = f"https://github.com/rhasspy/piper/releases/download/{version}/{filename}"
    
    try:
        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        
        def progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = int(block_num * block_size * 100 / total_size)
                print(f"\r    {percent}% complete...", end="", flush=True)
                
        urllib.request.urlretrieve(url, tmp_path, reporthook=progress)
        print("\n[*] Extracting Piper engine...")
        
        extract_dir = os.path.join(tempfile.gettempdir(), "piper_extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        if is_zip:
            import zipfile
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        else:
            import tarfile
            with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_dir)
                
        source_piper = os.path.join(extract_dir, "piper")
        if os.path.exists(source_piper):
            for item in os.listdir(source_piper):
                s = os.path.join(source_piper, item)
                d = os.path.join(PIPER_DIR, item)
                if os.path.exists(d):
                    if os.path.isdir(d):
                        shutil.rmtree(d)
                    else:
                        os.remove(d)
                shutil.move(s, d)
        
        try:
            os.remove(tmp_path)
            shutil.rmtree(extract_dir)
        except Exception:
            pass
            
        if os.name != 'nt':
            os.chmod(piper_exe, 0o755)
            
        print("[+] Piper engine successfully installed.")
        return True
    except Exception as e:
        print(f"\n[-] Failed to download/install Piper: {e}")
        return False

def _run_pip_install(engine_name, packages):
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    logger.info(f"[SETUP] Starting {engine_name} dependencies installation: {packages}")
    try:
        import subprocess, sys
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8', 
            errors='replace'
        )
        
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.debug(f"[{engine_name.upper()}_INSTALL] {line}")
                
        process.wait()
        if process.returncode == 0:
            logger.info(f"[SETUP] {engine_name} installed successfully.")
            return True
        else:
            logger.error(f"[SETUP] Failed to install {engine_name}. Exit code: {process.returncode}")
            return False
    except Exception as e:
        logger.error(f"[SETUP] Exception during {engine_name} installation: {e}")
        return False

def _install_espeak_ng():
    """
    Install eSpeak NG via winget (Windows only).
    Adds its install directory to the current process PATH so kokoro
    can use it immediately without requiring a full restart.
    """
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    import shutil, subprocess, sys

    # Already on PATH?
    if shutil.which("espeak-ng"):
        logger.info("[SETUP] espeak-ng is already available on PATH.")
        _patch_espeak_path()
        return True

    if sys.platform != "win32":
        logger.warning("[SETUP] Non-Windows: please install espeak-ng manually.")
        return False

    logger.info("[SETUP] Installing eSpeak NG via winget…")
    try:
        result = subprocess.run(
            [
                "winget", "install",
                "--id", "eSpeak-NG.eSpeak-NG",
                "--silent",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode == 0 or "Successfully installed" in result.stdout:
            logger.info("[SETUP] eSpeak NG installed successfully.")
            _patch_espeak_path()
            return True
        else:
            logger.error(f"[SETUP] winget espeak-ng failed (code {result.returncode}): {result.stdout.strip()}")
            return False
    except FileNotFoundError:
        logger.error("[SETUP] winget not found. Install eSpeak NG manually from https://github.com/espeak-ng/espeak-ng/releases")
        return False
    except Exception as e:
        logger.error(f"[SETUP] espeak-ng installation error: {e}")
        return False


def _patch_espeak_path():
    """Add the default eSpeak NG install directory to the current process PATH."""
    import os
    espeak_dir = r"C:\Program Files\eSpeak NG"
    if os.path.isdir(espeak_dir) and espeak_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = espeak_dir + os.pathsep + os.environ.get("PATH", "")


def download_kokoro_engine():
    _patch_espeak_path()   # Ensure espeak-ng is usable even before re-install
    pip_ok = _run_pip_install("Kokoro", ["kokoro", "misaki[en]", "soundfile"])
    esp_ok = _install_espeak_ng()
    return pip_ok and esp_ok

def download_xtts_engine():
    return _run_pip_install("XTTSv2", ["TTS"])

def unattended_onboarding(target_voices=None):
    print("=" * 60)
    print(f"  {T('onboarding_header')}")
    print("=" * 60)
    print()
    
    # Step 1: Environment
    print(f"[*] {T('step_env')}")
    if not check_python_version(): return False
    
    # Step 2: Dependencies
    print(f"[*] {T('step_env')}")
    install_dependencies()
    
    # Step 3: Piper Engine & Voices
    print(f"\n[*] Piper TTS Engine")
    download_piper_engine()
    
    if target_voices:
        print(f"\n[*] {T('step_voice')} ({len(target_voices)} voices)")
        for v_key in target_voices:
            download_voice(v_key)
            
    # Step 3.5: External Dependencies
    print(f"\n[*] Checking External Dependencies...")
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
