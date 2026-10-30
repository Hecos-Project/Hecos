"""
Automated Downloader for Fish Audio S2-Pro TTS Model
Downloads complete S2-Pro weights from Hugging Face into checkpoints/s2-pro.
"""
import os
import sys
import time
from datetime import datetime

# Ensure UTF-8 output on Windows console
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

DEST_DIR = os.path.join(ROOT, "hecos", "engines", "fish_speech", "checkpoints", "s2-pro")
os.makedirs(DEST_DIR, exist_ok=True)

LOG_PATH = os.path.join(ROOT, "hecos", "logs", "fish_speech_download.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def main():
    log("=" * 60)
    log("🚀 Starting Fish Audio S2-Pro Model Download (~10.9 GB total)")
    log(f"📁 Destination: {DEST_DIR}")
    log("=" * 60)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        log("❌ huggingface_hub not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
        from huggingface_hub import snapshot_download

    patterns = [
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

    t0 = time.time()
    try:
        log("⬇️ Downloading S2-Pro files from Hugging Face (fishaudio/s2-pro)...")
        snapshot_download(
            repo_id="fishaudio/s2-pro",
            local_dir=DEST_DIR,
            allow_patterns=patterns,
            max_workers=4,
        )
        elapsed = time.time() - t0
        log(f"✅ S2-Pro download complete in {elapsed/60:.1f} minutes!")

        # Verify files
        log("🔍 Verifying downloaded files:")
        all_ok = True
        for p in patterns:
            fpath = os.path.join(DEST_DIR, p)
            if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                sz_mb = os.path.getsize(fpath) / (1024 * 1024)
                log(f"  • {p}: {sz_mb:.1f} MB [OK]")
            else:
                log(f"  • {p}: MISSING or empty! [FAIL]")
                all_ok = False

        if all_ok:
            log("🎉 All S2-Pro files successfully verified! Ready for inference.")
            sys.exit(0)
        else:
            log("❌ Some files failed verification.")
            sys.exit(1)

    except Exception as err:
        log(f"❌ Download failed with exception: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
