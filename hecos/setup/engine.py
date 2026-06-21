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
            "pywinauto", "playwright", "pywin32", "pystray", "pillow", "flet", "qrcode",
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
        script = os.path.join("scripts", "windows", "run", "HECOS_TRAY_WIN.bat")
        script_path = os.path.join(CWD, script)
        if os.path.exists(script_path):
            subprocess.Popen(["cmd", "/c", "start", "", script_path], cwd=CWD)
    else:
        script = os.path.join("scripts", "linux", "run", "HECOS_TRAY_LINUX.sh")
        script_path = os.path.join(CWD, script)
        if os.path.exists(script_path):
            subprocess.Popen(["bash", script_path], cwd=CWD, start_new_session=True)

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
    print("[*] Fetching available voices from Piper repository...")
    try:
        with urllib.request.urlopen(url) as response:
            VOICES_CACHE = json.loads(response.read().decode())
            return VOICES_CACHE
    except Exception as e:
        print(f"[-] Failed to fetch voices: {e}")
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

def install_external_dependencies():
    deps_dir = os.path.join(CWD, "dependencies")
    if not os.path.exists(deps_dir):
        print(T("dep_not_found"))
        print()
        return False
        
    exe_files = glob.glob(os.path.join(deps_dir, "*.exe")) + glob.glob(os.path.join(deps_dir, "*.msi"))
    if not exe_files:
        print(T("dep_not_found"))
        print()
        return False

    success = True
    for exe in exe_files:
        filename = os.path.basename(exe)
        print(T("installing_dep", filename=filename))
        
        lower_name = filename.lower()
        if lower_name.endswith(".msi"):
            args = ["msiexec.exe", "/i", exe, "/qn", "/norestart"]
        else:
            args = [exe]
            if "vcredist" in lower_name or "vc_redist" in lower_name:
                args.extend(["/install", "/quiet", "/norestart"])
            elif "tesseract" in lower_name:
                args.extend(["/SILENT"])
            else:
                args.extend(["/SILENT"])
            
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == 0 or result.returncode == 3010: # 3010 means restart required
                print(T("dep_success", filename=filename))
            else:
                print(T("dep_err", filename=filename, err=f"Exit code {result.returncode}"))
                success = False
        except Exception as e:
            print(T("dep_err", filename=filename, err=str(e)))
            success = False
            
    print()
    return success

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
    print(f"\n[*] {T('step_ext_deps')}")
    install_external_dependencies()
    
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
