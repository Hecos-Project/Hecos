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
    for pkg in ["pydantic", "ruamel.yaml"]:
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
    # Check both root and hecos/ folder
    req_file = os.path.join(CWD, "requirements.txt")
    if not os.path.exists(req_file):
        req_file = os.path.join(CWD, "hecos", "requirements.txt")
    
    if not os.path.exists(req_file):
        print(f"[-] requirements.txt not found at {req_file}!")
        return False
    
    cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]
    try:
        subprocess.check_call(cmd)
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
            subprocess.check_call(["cmd", "/c", script_path], env=env)
        else:
            subprocess.check_call(["bash", script_path], env=env)
        return True
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

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
    
    # Step 3: Voices (Multiple)
    if target_voices:
        print(f"\n[*] {T('step_voice')} ({len(target_voices)} voices)")
        for v_key in target_voices:
            download_voice(v_key)
    
    # Step 4: Fixes
    print("\n[*] " + T('step_finish'))
    auto_fix_piper_path()
    
    # Step 5: Autostart Link
    print("\n[*] Setting up System Infrastructure...")
    enable_autostart()
    
    print("\n" + "=" * 60)
    print(f"  {T('onboarding_done')}")
    print("=" * 60)
    return True
