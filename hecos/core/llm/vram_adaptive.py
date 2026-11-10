"""
hecos/core/llm/vram_adaptive.py
─────────────────────────────────────────────────────────────────────────────
VRAM Adaptive Engine — dynamically selects num_ctx based on available VRAM.

Activated only when backend=ollama and adaptive_ctx=true in config.
Reads free VRAM via nvidia-smi and maps it to a context-window size profile,
so the LLM gets maximum context when it has the GPU to itself, and
gracefully degrades when SwarmUI/Flux, Kokoro TTS, or other services
are consuming VRAM.

Profile resolution (highest matching profile wins):
    free_mb >= min_free_mb  →  use that profile's num_ctx

Falls back to the static num_ctx from config if:
  - adaptive_ctx is False/missing
  - nvidia-smi is unavailable
  - no profile matches (should not happen with min_free_mb=0 fallback)
"""

import shutil
import subprocess
import sys
from typing import Optional

from hecos.core.logging.logger import info as zlog_info, debug as zlog_debug

# ─── Default profiles (user can override via system.yaml) ─────────────────────
#
# Tuned for a 16 GB VRAM card (RTX 5060 Ti).
# Adjust min_free_mb thresholds for your setup.
#
# Rule of thumb for Gemma/Qwen 12B QAT:
#   model VRAM ≈ 8 GB  →  leave the rest for context + KV cache
#   Each 1024 tokens of context ≈ 150–300 MB KV cache (model-dependent)
#
DEFAULT_PROFILES = [
    # Only LLM loaded — give it maximum context
    {"min_free_mb": 13000, "num_ctx": 65536,  "label": "HIGH_POWER"},
    # LLM + Kokoro TTS (≈1–2 GB) — balanced
    {"min_free_mb":  8000, "num_ctx": 40960,  "label": "BALANCED"},
    # LLM + TTS + Flux/SwarmUI light (≈4–6 GB) — economy
    {"min_free_mb":  4000, "num_ctx": 24576,  "label": "ECONOMY"},
    # Everything active, low headroom — minimal safe context
    {"min_free_mb":     0, "num_ctx": 16384,  "label": "MINIMAL"},
]


def _get_vram_free_mb() -> int:
    """
    Queries the first GPU's free VRAM via nvidia-smi.
    Returns free MB, or -1 if nvidia-smi is unavailable or fails.
    """
    try:
        smi = shutil.which("nvidia-smi")
        if not smi:
            alt = r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
            import os
            smi = alt if os.path.exists(alt) else None
        if not smi:
            return -1

        kwargs: dict = {}
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs = {"startupinfo": si, "creationflags": 0x08000000}

        out = subprocess.check_output(
            [smi, "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            timeout=2,
            stderr=subprocess.DEVNULL,
            **kwargs,
        ).decode().strip()

        # nvidia-smi may return multiple lines on multi-GPU systems — take first GPU
        first_line = out.splitlines()[0].strip()
        return int(first_line)
    except Exception as exc:
        zlog_debug("VRAM", f"[ADAPTIVE CTX] nvidia-smi query failed: {exc}")
        return -1


def get_optimal_num_ctx(ollama_cfg: dict) -> Optional[int]:
    """
    Returns the optimal num_ctx for the current VRAM state.

    Returns None if:
      - adaptive_ctx is False or not set in ollama_cfg
      - nvidia-smi is unavailable

    When None is returned, params_builder falls back to the static
    num_ctx value from config (no change in behaviour).

    :param ollama_cfg: The backend.ollama section of the merged config dict.
    """
    if not ollama_cfg.get("adaptive_ctx", False):
        return None  # Feature disabled — use static config value

    profiles = ollama_cfg.get("adaptive_ctx_profiles", DEFAULT_PROFILES)

    free_mb = _get_vram_free_mb()
    if free_mb < 0:
        zlog_debug("VRAM", "[ADAPTIVE CTX] VRAM query unavailable — using static num_ctx")
        return None

    # Sort profiles descending by min_free_mb; pick first where free_mb >= threshold
    for profile in sorted(profiles, key=lambda p: p.get("min_free_mb", 0), reverse=True):
        if free_mb >= profile.get("min_free_mb", 0):
            ctx   = profile.get("num_ctx", 16384)
            label = profile.get("label", "?")
            zlog_info(
                "VRAM",
                f"[ADAPTIVE CTX] Free VRAM: {free_mb:,} MB → profile={label}, num_ctx={ctx:,}",
            )
            return ctx

    # Fallback (should never reach here if profiles include min_free_mb=0)
    return ollama_cfg.get("num_ctx", 16384)
