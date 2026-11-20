"""
hecos/core/llm/adaptive/gpu_probe.py
─────────────────────────────────────────────────────────────────────────────
GPU hardware probe layer.

Abstracts GPU memory queries away from vendor-specific tools.
Currently supports:
  - NVIDIA GPUs via nvidia-smi   (primary)
  - Fallback: returns None so the engine degrades gracefully

Returns a GpuMemInfo dataclass with total/used/free in MB, plus gpu name.
On multi-GPU systems, returns info for the GPU with the most total VRAM
(the discrete card, not an iGPU) — matching what Ollama uses by default.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from hecos.core.logging.logger import (
    debug as zlog_debug,
    warning as zlog_warning,
)

_MODULE = "VRAM"


@dataclass
class GpuMemInfo:
    name: str           # GPU name (e.g. "NVIDIA GeForce RTX 5060 Ti")
    total_mb: int       # Total VRAM in MB
    used_mb: int        # Currently used VRAM in MB
    free_mb: int        # Currently free VRAM in MB

    @property
    def free_pct(self) -> float:
        """Free VRAM as percentage of total (0–100)."""
        return (self.free_mb / self.total_mb * 100) if self.total_mb > 0 else 0.0

    @property
    def used_pct(self) -> float:
        """Used VRAM as percentage of total (0–100)."""
        return (self.used_mb / self.total_mb * 100) if self.total_mb > 0 else 0.0


def _run_nvidia_smi(*extra_args: str) -> Optional[str]:
    """
    Runs nvidia-smi with the given extra arguments.
    Returns stdout as a string, or None on failure.
    """
    smi = shutil.which("nvidia-smi")
    if not smi and sys.platform == "win32":
        alt = r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
        smi = alt if os.path.exists(alt) else None
    if not smi:
        return None

    kwargs: dict = {}
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs = {"startupinfo": si, "creationflags": 0x08000000}

    try:
        raw = subprocess.check_output(
            [smi, *extra_args],
            timeout=3,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        return raw.decode("utf-8", errors="replace").strip()
    except subprocess.TimeoutExpired:
        zlog_warning(_MODULE, "[GPU PROBE] nvidia-smi timed out")
        return None
    except Exception as exc:
        zlog_debug(_MODULE, f"[GPU PROBE] nvidia-smi error: {exc}")
        return None


def probe_gpu() -> Optional[GpuMemInfo]:
    """
    Queries GPU memory via nvidia-smi.

    On multi-GPU systems (e.g. Intel iGPU + Nvidia dGPU), selects the GPU
    with the highest total VRAM to match what Ollama uses.

    Returns GpuMemInfo, or None if no GPU could be detected.
    """
    # Query: name, total, used, free — one line per GPU
    out = _run_nvidia_smi(
        "--query-gpu=name,memory.total,memory.used,memory.free",
        "--format=csv,noheader,nounits",
    )

    if not out:
        zlog_debug(_MODULE, "[GPU PROBE] nvidia-smi returned no output")
        return None

    best: Optional[GpuMemInfo] = None
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            zlog_debug(_MODULE, f"[GPU PROBE] Unexpected nvidia-smi line: {line!r}")
            continue
        try:
            name     = parts[0]
            total_mb = int(parts[1]) if parts[1].isdigit() else 0
            used_mb  = int(parts[2]) if parts[2].isdigit() else 0
            free_mb  = int(parts[3]) if parts[3].isdigit() else 0

            info = GpuMemInfo(name=name, total_mb=total_mb, used_mb=used_mb, free_mb=free_mb)
            if best is None or info.total_mb > best.total_mb:
                best = info
        except (ValueError, IndexError) as exc:
            zlog_debug(_MODULE, f"[GPU PROBE] Parse error on line {line!r}: {exc}")

    return best
