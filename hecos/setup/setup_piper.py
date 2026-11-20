"""
Hecos Setup - Piper TTS and Voice Downloader
Handles downloading and extracting the Piper speech synthesis binary and neural voice models.
"""

import os
import glob
import json
import tempfile
import shutil
import urllib.request
from typing import Dict, Any, Optional

from .utils import PIPER_DIR, AUDIO_CONFIG_PATH, safe_replace_yaml
from .i18n import T

VOICES_CACHE: Optional[Dict[str, Any]] = None


def fetch_piper_voices() -> Dict[str, Any]:
    """Fetches list of available Piper voices from the Hugging Face repository."""
    global VOICES_CACHE
    if VOICES_CACHE:
        return VOICES_CACHE

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


def download_voice(voice_key: str) -> bool:
    """Downloads the .onnx and .onnx.json files for the selected voice model."""
    voices = fetch_piper_voices()
    if not voices or voice_key not in voices:
        print(f"[-] Voice {voice_key} not found in repository.")
        return False

    voice_data = voices[voice_key]
    os.makedirs(PIPER_DIR, exist_ok=True)

    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"

    for rel_path in voice_data.get("files", {}):
        if not rel_path.endswith((".onnx", ".onnx.json")):
            continue

        filename = os.path.basename(rel_path)
        target_path = os.path.join(PIPER_DIR, filename)

        if os.path.exists(target_path):
            print(T("already_exists", filename=filename))
        else:
            final_url = base_url + rel_path
            try:
                from hecos.core.progress import progress
                with progress.task(f"setup_voice_{filename}", title=f"Voce {filename}", source="SETUP") as pt:
                    progress.download(final_url, target_path, task=pt)
                print(T("success_dl", filename=filename))
            except Exception as e:
                print(T("err_dl", filename=filename, err=str(e)))
                return False

    # Update audio.yaml with default onnx model path
    onnx_path = os.path.join(PIPER_DIR, f"{voice_key}.onnx")
    safe_replace_yaml(AUDIO_CONFIG_PATH, "onnx_model", onnx_path)
    return True


def download_piper_engine() -> bool:
    """Downloads and installs the platform-specific Piper standalone engine binary."""
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
        from hecos.core.progress import progress
        phases = [("download", 75, "Download"), ("extract", 25, "Estrazione")]
        with progress.task("setup_piper_engine", title="Piper TTS Engine", source="SETUP", phases=phases) as pt:
            pt.phase("download")
            progress.download(url, tmp_path, task=pt)
            pt.phase("extract", message="Estrazione Piper engine...")
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

