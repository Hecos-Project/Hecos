"""
hecos/core/llm/adaptive/engine.py
─────────────────────────────────────────────────────────────────────────────
VRAM Adaptive Engine — selects num_ctx dynamically based on available VRAM.

DESIGN PHILOSOPHY
─────────────────
Instead of hardcoding absolute MB thresholds for a specific GPU model,
profiles use min_free_pct (percentage of total VRAM that must be free).
This makes the engine portable across all GPU sizes:

    8 GB card  (GTX 1070, RTX 3070 Mobile):  thresholds scale to ~6400/4000/2000 MB
    12 GB card (RTX 3080, 4070):             thresholds scale to ~9600/6000/3000 MB
    16 GB card (RTX 5060 Ti, 4080):          thresholds scale to ~12800/8000/4000 MB
    24 GB card (RTX 3090, 4090):             thresholds scale to ~19200/12000/6000 MB

Users can override profiles in system.yaml → backend.ollama.adaptive_ctx_profiles.
Each profile entry supports either min_free_pct OR min_free_mb (or both — pct wins).

DEFAULT PROFILES
────────────────
  HIGH_POWER  (>= 80% free) → num_ctx 65536   (LLM alone, full power)
  BALANCED    (>= 50% free) → num_ctx 40960   (LLM + TTS / light workloads)
  ECONOMY     (>= 25% free) → num_ctx 24576   (LLM + TTS + image gen)
  MINIMAL     (>=  0% free) → num_ctx 16384   (all services active, low headroom)

ACTIVATION
──────────
Set adaptive_ctx: true in system.yaml → backend.ollama.
When false (or nvidia-smi unavailable), engine returns None and
params_builder falls back to the static num_ctx from config.
"""

from typing import Optional

from hecos.core.logging.logger import (
    debug  as zlog_debug,
    info   as zlog_info,
    warning as zlog_warning,
)
from .gpu_probe import probe_gpu, GpuMemInfo

_MODULE = "VRAM"

# ─── Default portable profiles ────────────────────────────────────────────────
# min_free_pct: minimum % of total VRAM that must be free to activate this profile.
# num_ctx     : context window size to request from Ollama.
# label       : human-readable name shown in logs.
DEFAULT_PROFILES = [
    {
        "min_free_pct": 80,
        "num_ctx":      65536,
        "label":        "HIGH_POWER",
        "note":         "LLM alone — maximum context",
    },
    {
        "min_free_pct": 50,
        "num_ctx":      40960,
        "label":        "BALANCED",
        "note":         "LLM + TTS or light background services",
    },
    {
        "min_free_pct": 25,
        "num_ctx":      24576,
        "label":        "ECONOMY",
        "note":         "LLM + TTS + image generation (Flux/ComfyUI)",
    },
    {
        "min_free_pct": 0,
        "num_ctx":      16384,
        "label":        "MINIMAL",
        "note":         "All services active — low VRAM headroom",
    },
]


def _resolve_threshold(profile: dict, gpu: GpuMemInfo) -> int:
    """
    Returns the min free MB threshold for a profile.

    Priority:
      1. min_free_pct  (portable — fraction of GPU's total VRAM)
      2. min_free_mb   (absolute — for explicit overrides)
    """
    pct = profile.get("min_free_pct")
    if pct is not None:
        return int(gpu.total_mb * pct / 100)
    return profile.get("min_free_mb", 0)


def get_optimal_num_ctx(ollama_cfg: dict) -> Optional[int]:
    """
    Returns the optimal num_ctx for the current VRAM state.

    Returns None if:
      - adaptive_ctx is False or not set in ollama_cfg
      - GPU probe fails (no nvidia-smi, no GPU, timeout)

    When None is returned, params_builder uses the static num_ctx from config.

    :param ollama_cfg: The backend.ollama section of the merged config dict.
    """
    # ── 0. Feature gate ───────────────────────────────────────────────────────
    if not ollama_cfg.get("adaptive_ctx", False):
        zlog_debug(_MODULE, "[ADAPTIVE CTX] Feature disabled (adaptive_ctx=false) — using static num_ctx")
        return None

    zlog_debug(_MODULE, "[ADAPTIVE CTX] Probing GPU memory before LLM call...")

    # ── 1. Probe GPU ──────────────────────────────────────────────────────────
    gpu = probe_gpu()
    if gpu is None:
        zlog_warning(
            _MODULE,
            "[ADAPTIVE CTX] GPU probe failed — no VRAM data available. "
            "Falling back to static num_ctx from config. "
            "Install NVIDIA drivers or set adaptive_ctx: false to suppress this warning."
        )
        return None

    # ── 2. Log GPU state ──────────────────────────────────────────────────────
    zlog_debug(
        _MODULE,
        f"[ADAPTIVE CTX] GPU detected: {gpu.name} | "
        f"Total: {gpu.total_mb:,} MB | "
        f"Used: {gpu.used_mb:,} MB ({gpu.used_pct:.1f}%) | "
        f"Free: {gpu.free_mb:,} MB ({gpu.free_pct:.1f}%)"
    )

    # ── 3. Load profiles ──────────────────────────────────────────────────────
    raw_profiles = ollama_cfg.get("adaptive_ctx_profiles", DEFAULT_PROFILES)

    # Sort descending by resolved threshold so highest-priority profile is checked first
    try:
        profiles_sorted = sorted(
            raw_profiles,
            key=lambda p: _resolve_threshold(p, gpu),
            reverse=True,
        )
    except Exception as exc:
        zlog_warning(_MODULE, f"[ADAPTIVE CTX] Profile sort failed ({exc}) — using defaults")
        profiles_sorted = sorted(
            DEFAULT_PROFILES,
            key=lambda p: _resolve_threshold(p, gpu),
            reverse=True,
        )

    # ── 4. Log profile table (DEBUG only) ─────────────────────────────────────
    zlog_debug(_MODULE, "[ADAPTIVE CTX] Profile evaluation:")
    for p in profiles_sorted:
        threshold_mb = _resolve_threshold(p, gpu)
        meets = "✓ MATCH" if gpu.free_mb >= threshold_mb else "✗ skip "
        zlog_debug(
            _MODULE,
            f"[ADAPTIVE CTX]   {meets} | {p.get('label', '?'):12s} | "
            f"need >= {threshold_mb:,} MB free | "
            f"num_ctx={p.get('num_ctx', '?'):,} | "
            f"{p.get('note', '')}"
        )

    # ── 5. Select first matching profile ──────────────────────────────────────
    for profile in profiles_sorted:
        threshold_mb = _resolve_threshold(profile, gpu)
        if gpu.free_mb >= threshold_mb:
            ctx   = profile.get("num_ctx", 16384)
            label = profile.get("label", "UNKNOWN")
            note  = profile.get("note", "")

            zlog_info(
                _MODULE,
                f"[ADAPTIVE CTX] {gpu.name} | "
                f"Free: {gpu.free_mb:,} / {gpu.total_mb:,} MB ({gpu.free_pct:.1f}%) | "
                f"Profile: {label} → num_ctx: {ctx:,}"
                + (f" ({note})" if note else "")
            )
            return ctx

    # ── 6. Absolute fallback (should never reach here with min_free_pct=0) ───
    fallback = ollama_cfg.get("num_ctx", 16384)
    zlog_warning(
        _MODULE,
        f"[ADAPTIVE CTX] No profile matched for {gpu.free_mb:,} MB free. "
        f"Falling back to config num_ctx={fallback:,}. "
        "Check that your profiles include a min_free_pct=0 entry."
    )
    return fallback
