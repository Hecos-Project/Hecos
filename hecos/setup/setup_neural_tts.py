"""
Hecos Setup - Advanced Neural TTS Engine Installers
Handles installation and runtime configuration for Kokoro TTS, XTTSv2, and Fish Speech S2-Pro,
including espeak-ng, Python C-headers patching, and MSVC build tools.
"""

import os
import sys
import shutil
import zipfile
import tempfile
import importlib
import subprocess
import urllib.request
from typing import Tuple, Dict, Any, List

from .utils import CWD


def _run_pip_install(engine_name: str, packages: List[str]) -> bool:
    """Installs pip packages using Hecos progress system or fallback logger."""
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    logger.info(f"[SETUP] Starting {engine_name} dependencies installation: {packages}")
    try:
        from hecos.core.progress import progress
        with progress.task(
            f"setup_pip_{engine_name.lower().replace(' ', '_')}",
            title=f"Dipendenze {engine_name}",
            source="SETUP",
        ) as pt:
            retcode, output = progress.pip(packages, task=pt)

        if retcode == 0:
            logger.info(f"[SETUP] {engine_name} installed successfully.")
            return True
        else:
            logger.error(f"[SETUP] Failed to install {engine_name}. Exit code: {retcode}")
            if engine_name.upper() == "XTTSV2":
                logger.error("[SETUP] ❌ XTTSv2 installation failed (usually due to missing build dependencies).")
                logger.error("[SETUP] 💡 TO FIX THIS, YOU PROBABLY NEED MICROSOFT C++ BUILD TOOLS:")
                logger.error("[SETUP]    1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
                logger.error("[SETUP]    2. Install the 'Desktop development with C++' workload.")
                logger.error("[SETUP]    3. RESTART your PC.")
                logger.error("[SETUP] 🔄 After restarting, try installing XTTSv2 again from Hecos settings.")
            return False
    except Exception as e:
        logger.error(f"[SETUP] Exception during {engine_name} installation: {e}")
        return False


def _patch_espeak_path():
    """Add the default eSpeak NG install directory to the current process PATH."""
    espeak_dir = r"C:\Program Files\eSpeak NG"
    if os.path.isdir(espeak_dir) and espeak_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = espeak_dir + os.pathsep + os.environ.get("PATH", "")


def _install_espeak_ng() -> bool:
    """
    Install eSpeak NG via winget (Windows only).
    Adds its install directory to the current process PATH so kokoro can use it immediately.
    """
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

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


def download_kokoro_engine() -> bool:
    """Installs Kokoro TTS engine dependencies, espeak-ng, and pre-caches default weights."""
    _patch_espeak_path()
    pip_ok = _run_pip_install("Kokoro", ["kokoro", "misaki[en]", "soundfile"])
    esp_ok = _install_espeak_ng()
    try:
        from huggingface_hub import hf_hub_download
        from hecos.core.audio.tts.kokoro_engine import KOKORO_VOICES
        hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename="config.json")
        hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename="kokoro-v1_0.pth")
        for voice_key in KOKORO_VOICES:
            hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename=f"voices/{voice_key}.pt")
    except Exception as e:
        print(f"[SETUP] Note: pre-caching Kokoro voices encountered: {e}")
    return pip_ok and esp_ok


def _patch_python_headers() -> bool:
    """Downloads and extracts missing Python.h headers from NuGet into the embedded environment."""
    python_env_dir = os.path.dirname(sys.executable)
    include_dir = os.path.join(python_env_dir, "Include")
    libs_dir = os.path.join(python_env_dir, "libs")
    python_h = os.path.join(include_dir, "Python.h")
    python_h_lower = os.path.join(python_env_dir, "include", "Python.h")

    if os.path.exists(python_h) or os.path.exists(python_h_lower):
        return True

    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"

    logger.info(f"[SETUP] ⚠️ Missing Python {version_str} C-headers (Python.h). Patching embedded environment...")
    url = f"https://www.nuget.org/api/v2/package/python/{version_str}"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "python.zip")
            logger.info("[SETUP] ⏳ Downloading Python headers from nuget.org...")

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            logger.info("[SETUP] ⏳ Extracting headers...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            tools_include = os.path.join(tmpdir, "tools", "include")
            tools_libs = os.path.join(tmpdir, "tools", "libs")

            if os.path.exists(tools_include):
                os.makedirs(include_dir, exist_ok=True)
                for item in os.listdir(tools_include):
                    s = os.path.join(tools_include, item)
                    d = os.path.join(include_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

            if os.path.exists(tools_libs):
                os.makedirs(libs_dir, exist_ok=True)
                for item in os.listdir(tools_libs):
                    s = os.path.join(tools_libs, item)
                    d = os.path.join(libs_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

        logger.info("[SETUP] ✅ Python environment patched with C-headers successfully.")
        return True
    except Exception as e:
        logger.error(f"[SETUP] ❌ Failed to patch Python headers: {e}")
        return False


def _install_msvc_build_tools() -> bool:
    """Attempts automatic installation of MSVC Build Tools via winget."""
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    logger.info("[SETUP] ⚠️ Attempting automatic installation of MSVC Build Tools via winget.")
    logger.info("[SETUP] ⏳ THIS MAY TAKE 10-20 MINUTES and download ~2GB of data. Please wait...")
    try:
        result = subprocess.run(
            [
                "winget", "install",
                "--id", "Microsoft.VisualStudio.2022.BuildTools",
                "--silent",
                "--accept-source-agreements",
                "--accept-package-agreements",
                "--override", "--wait --quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode == 0 or "Successfully installed" in result.stdout:
            logger.info("[SETUP] ✅ MSVC Build Tools installed successfully.")
            return True
        else:
            logger.error(f"[SETUP] winget MSVC installation failed (code {result.returncode}): {result.stdout.strip()}")
            return False
    except Exception as e:
        logger.error(f"[SETUP] MSVC installation error: {e}")
        return False


def download_xtts_engine() -> bool:
    """Installs XTTSv2 engine, compiling requirements and verifying imports."""
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    logger.info("[SETUP] ═══════════════════════════════════════════════════════")
    logger.info("[SETUP] 🚀 Starting XTTSv2 installation (Coqui TTS)")
    logger.info("[SETUP] ═══════════════════════════════════════════════════════")
    logger.info("[SETUP] Step 1/3: Installing build tools and patching Python...")

    _patch_python_headers()

    prereq_ok = _run_pip_install("XTTSv2-Prerequisites", ["Cython", "setuptools", "wheel", "numpy"])
    if not prereq_ok:
        logger.error("[SETUP] ❌ Failed to install build prerequisites. Cannot continue.")
        return False

    logger.info("[SETUP] ✅ Build tools ready.")
    logger.info("[SETUP] Step 2/3: Installing TTS library (this may take several minutes)...")

    tts_ok = _run_pip_install("XTTSv2", ["TTS"])

    # If TTS fails, retry after installing MSVC Build Tools
    if not tts_ok:
        logger.warning("[SETUP] ⚠️ TTS installation failed. Likely missing Microsoft Visual C++ Build Tools.")
        msvc_ok = _install_msvc_build_tools()
        if msvc_ok:
            logger.info("[SETUP] 🔄 Retrying TTS library installation...")
            tts_ok = _run_pip_install("XTTSv2", ["TTS"])

    if not tts_ok:
        logger.error("[SETUP] ❌ TTS library installation failed.")
        logger.error("[SETUP] 💡 Try manually: C:\\Hecos\\python_env\\python.exe -m pip install TTS")
        logger.error("[SETUP] 🔄 After fixing, RESTART Hecos and try again.")
        return False

    logger.info("[SETUP] ✅ TTS library installed successfully.")
    logger.info("[SETUP] Step 3/3: Verifying import...")

    try:
        TTS_mod = importlib.import_module("TTS")
        logger.info(f"[SETUP] ✅ XTTSv2 is ready! (TTS v{getattr(TTS_mod, '__version__', '?')})")
        logger.info("[SETUP] 🔄 RESTART Hecos to activate XTTSv2 as your TTS engine.")
        logger.info("[SETUP] ℹ️  The XTTSv2 model (~1.8GB) will be downloaded automatically on first use.")
        return True
    except ImportError as e:
        logger.error(f"[SETUP] ⚠️ TTS installed but cannot be imported: {e}")
        logger.error("[SETUP] 🔄 RESTART Hecos — the module should become available after a fresh start.")
        return False


def check_fish_speech_engine() -> Tuple[bool, Dict[str, Any]]:
    """
    Performs comprehensive diagnostic checks for Fish Speech TTS.
    Returns (ok: bool, report: dict) detailing missing dependencies, repository, weights, or GPU.
    """
    report = {
        "ok": True,
        "missing_dependencies": [],
        "missing_repo": False,
        "missing_weights": [],
        "gpu": {"cuda_available": False, "device_name": "CPU"},
    }

    # 1. Check Python Dependencies
    req_pkgs = [
        "torch", "torchaudio", "soundfile", "fastapi", "uvicorn", 
        "ormsgpack", "loguru", "pyrootutils", "hydra", "einx", "huggingface_hub",
        "cachetools", "safetensors"
    ]
    for pkg in req_pkgs:
        try:
            importlib.import_module(pkg)
        except ImportError:
            report["missing_dependencies"].append(pkg)

    # 2. Check Engine Repository
    engine_dir = os.path.join(CWD, "hecos", "engines", "fish_speech")
    inference_init_s2 = os.path.join(engine_dir, "fish_speech", "inference_engine", "__init__.py")
    inference_init_old = os.path.join(engine_dir, "tools", "inference_engine", "__init__.py")
    if not os.path.exists(inference_init_s2) and not os.path.exists(inference_init_old):
        report["missing_repo"] = True

    # 3. Check Checkpoints (Check S2-Pro first, fallback to 1.5)
    s2_ckpt_dir = os.path.join(engine_dir, "checkpoints", "s2-pro")
    s2_required_files = [
        ("codec.pth", 1_500_000_000),
        ("model-00001-of-00002.safetensors", 4_000_000_000),
        ("model-00002-of-00002.safetensors", 3_500_000_000),
        ("config.json", 100),
        ("model.safetensors.index.json", 1_000),
        ("tokenizer.json", 5_000_000),
        ("special_tokens_map.json", 1_000),
    ]

    s2_missing = [
        fname for fname, min_size in s2_required_files 
        if not os.path.exists(os.path.join(s2_ckpt_dir, fname)) or os.path.getsize(os.path.join(s2_ckpt_dir, fname)) < min_size
    ]

    legacy_ckpt_dir = os.path.join(engine_dir, "checkpoints", "fish-speech-1.5")
    legacy_required = [
        ("model.pth", 100_000_000),
        ("firefly-gan-vq-fsq-8x1024-21hz-generator.pth", 50_000_000),
        ("config.json", 100),
        ("special_tokens.json", 100),
        ("tokenizer.tiktoken", 100_000),
    ]
    legacy_missing = [
        fname for fname, min_size in legacy_required
        if not os.path.exists(os.path.join(legacy_ckpt_dir, fname)) or os.path.getsize(os.path.join(legacy_ckpt_dir, fname)) < min_size
    ]

    if not s2_missing:
        report["engine_version"] = "s2-pro"
        report["missing_weights"] = []
    elif not legacy_missing:
        report["engine_version"] = "fish-speech-1.5"
        report["missing_weights"] = []
    else:
        report["engine_version"] = "s2-pro"
        report["missing_weights"] = s2_missing

    # 4. Check GPU / CUDA
    try:
        import torch
        report["gpu"]["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            report["gpu"]["device_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass

    if report["missing_dependencies"] or report["missing_repo"] or report["missing_weights"]:
        report["ok"] = False

    return report["ok"], report


def download_fish_speech_engine() -> bool:
    """
    Complete installer for Fish Speech S2-Pro TTS:
    1. Installs Python dependencies
    2. Ensures engine source code is present
    3. Downloads S2-Pro checkpoints (~10.9 GB)
    4. Validates full system readiness
    """
    try:
        from hecos.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger("SETUP")

    logger.info("[SETUP] ═══════════════════════════════════════════════════════")
    logger.info("[SETUP] 🚀 Starting Complete Fish Speech S2-Pro Installation")
    logger.info("[SETUP] ═══════════════════════════════════════════════════════")

    # Step 1: Install Python dependencies
    req_path = os.path.join(CWD, "hecos", "setup", "requirements_fish_speech.txt")
    if os.path.isfile(req_path):
        logger.info(f"[SETUP] Step 1/3: Installing Python dependencies from {os.path.basename(req_path)}...")
        pip_ok = _run_pip_install("Fish-Speech", ["-r", req_path])
    else:
        logger.info("[SETUP] Step 1/3: Installing Python dependencies...")
        fallback_pkgs = [
            "ormsgpack", "httpx", "requests", "soundfile", "fish-audio-sdk",
            "fastapi", "uvicorn", "loguru", "pyrootutils", "hydra-core",
            "natsort", "einx", "pydub", "resampy", "silero-vad",
            "opencc-python-reimplemented", "descript-audio-codec",
            "huggingface_hub", "loralib", "vector-quantize-pytorch",
            "cachetools", "safetensors", "kui"
        ]
        pip_ok = _run_pip_install("Fish-Speech", fallback_pkgs)

    if not pip_ok:
        logger.error("[SETUP] ❌ Failed to install Fish Speech Python dependencies.")
        return False

    logger.info("[SETUP] ✅ Python dependencies verified.")

    # Step 2: Ensure Engine Source Repository
    engine_dir = os.path.join(CWD, "hecos", "engines", "fish_speech")
    inference_init = os.path.join(engine_dir, "fish_speech", "inference_engine", "__init__.py")
    if not os.path.exists(inference_init):
        logger.info("[SETUP] Step 2/3: Fetching Fish Speech engine repository (main branch)...")
        os.makedirs(os.path.dirname(engine_dir), exist_ok=True)
        try:
            cmd = ["git", "clone", "--depth", "1", "https://github.com/fishaudio/fish-speech.git", engine_dir]
            subprocess.check_call(cmd)
            logger.info("[SETUP] ✅ Fish Speech engine repository cloned successfully.")
        except Exception as clone_err:
            logger.error(f"[SETUP] ❌ Failed to clone Fish Speech repository: {clone_err}")
            return False
    else:
        logger.info("[SETUP] Step 2/3: Fish Speech engine repository already present.")

    # Step 3: Model Checkpoints for S2-Pro
    s2_ckpt_dir = os.path.join(engine_dir, "checkpoints", "s2-pro")
    os.makedirs(s2_ckpt_dir, exist_ok=True)
    required_files = [
        "config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "chat_template.jinja",
        "model.safetensors.index.json",
        "codec.pth",
        "model-00001-of-00002.safetensors",
        "model-00002-of-00002.safetensors",
    ]

    missing_files = []
    for fname in required_files:
        p = os.path.join(s2_ckpt_dir, fname)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            missing_files.append(fname)

    if missing_files:
        logger.info(f"[SETUP] Step 3/3: Downloading missing S2-Pro model checkpoints (~10.9 GB): {missing_files}...")
        try:
            from huggingface_hub import hf_hub_download
            for fname in missing_files:
                logger.info(f"[SETUP] ⬇️ Downloading {fname} to checkpoints/s2-pro...")
                hf_hub_download(
                    repo_id="fishaudio/s2-pro",
                    filename=fname,
                    local_dir=s2_ckpt_dir
                )
            logger.info("[SETUP] ✅ Fish Speech S2-Pro checkpoints downloaded successfully.")
        except Exception as dl_err:
            logger.error(f"[SETUP] ❌ Failed to download S2-Pro checkpoints: {dl_err}")
            return False
    else:
        logger.info("[SETUP] Step 3/3: All S2-Pro model checkpoints are cached and ready.")

    # Final Validation
    ok, report = check_fish_speech_engine()
    if ok:
        device_str = report["gpu"]["device_name"]
        logger.info("=" * 60)
        logger.info(f"[SETUP] 🎉 Fish Speech S2-Pro is fully installed and ready on {device_str}!")
        logger.info("[SETUP] 💡 Expressive tags like [whisper], [laughing], [angry] are natively supported!")
        logger.info("=" * 60)
        return True
    else:
        logger.error(f"[SETUP] ❌ Installation completed but validation failed: {report}")
        return False

