"""
downloader.py
─────────────────────────────────────────────────────────────────────────────
Hecos External Dependency Manager — Downloader
─────────────────────────────────────────────────────────────────────────────
Downloads an external dependency installer to a temporary directory,
verifies its SHA256 checksum, and returns the local path.

Uses only Python stdlib (urllib, tempfile, hashlib) — no extra deps.
Cross-platform: temp dir resolved via tempfile.gettempdir().
"""
from __future__ import annotations

import hashlib
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, Optional
from urllib.error import URLError

from hecos.core.logging import logger
from .registry import ExternalDep

# Staging dir: OS-native temp location / hecos_ext_deps
# Windows → C:\Users\Tony\AppData\Local\Temp\hecos_ext_deps
# Linux   → /tmp/hecos_ext_deps
# macOS   → /var/folders/.../hecos_ext_deps
_STAGING_DIR = Path(tempfile.gettempdir()) / "hecos_ext_deps"

_MAX_RETRIES = 3
_CHUNK_SIZE  = 65536  # 64 KB chunks for progress reporting


# ── Progress callback type ─────────────────────────────────────────────────────
# Called repeatedly during download: callback(bytes_done, total_bytes)
ProgressCallback = Callable[[int, int], None]


def _sha256(path: Path) -> str:
    """Computes the SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def download(
    dep: ExternalDep,
    progress_cb: Optional[ProgressCallback] = None,
    local_fallback_dir: Optional[Path] = None,
) -> Path:
    """
    Downloads the installer for the given dep to a temp staging dir.

    Args:
        dep:               The ExternalDep to download.
        progress_cb:       Optional callback(bytes_done, total_bytes) for UI updates.
        local_fallback_dir: If provided and the installer is already there,
                            skip downloading (offline/manual mode).

    Returns:
        Path to the local installer file (ready to be passed to installer.py).

    Raises:
        FileNotFoundError: If download_url is empty and no local fallback found.
        ValueError:        If SHA256 checksum mismatch after download.
        ConnectionError:   If all download retries failed.
    """
    filename = dep.download_url.split("/")[-1] if dep.download_url else ""
    if not filename:
        raise FileNotFoundError(
            f"[EDM] No download_url defined for dependency '{dep.id}'."
        )

    # ── 1. Check local fallback first (e.g. user's manual dependencies/ folder) ──
    if local_fallback_dir:
        local_file = Path(local_fallback_dir) / filename
        if local_file.exists():
            logger.info("EDM", f"Found local fallback for '{dep.name}' at {local_file}")
            return local_file

    # ── 2. Check staging cache (already downloaded in a previous session) ────────
    _STAGING_DIR.mkdir(parents=True, exist_ok=True)
    dest = _STAGING_DIR / filename

    if dest.exists():
        # Verify checksum if available
        if dep.checksum_sha256:
            actual = _sha256(dest)
            if actual == dep.checksum_sha256:
                logger.debug("EDM", f"Found valid cached installer for '{dep.name}'")
                return dest
            # Checksum mismatch — delete and re-download
            logger.warning("EDM", f"Cached installer for '{dep.name}' has invalid checksum. Re-downloading.")
            dest.unlink()

    # ── 3. Download with retries ─────────────────────────────────────────────────
    last_error: Optional[Exception] = None
    logger.info("EDM", f"Downloading '{dep.name}' from {dep.download_url}")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(dep.download_url, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                done  = 0
                with open(dest, "wb") as out:
                    while True:
                        chunk = resp.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        if progress_cb:
                            progress_cb(done, total)
            break  # success → exit retry loop

        except (URLError, OSError) as e:
            last_error = e
            logger.warning("EDM", f"Download attempt {attempt}/{_MAX_RETRIES} failed for '{dep.name}': {e}")
            if dest.exists():
                dest.unlink()
            if attempt == _MAX_RETRIES:
                logger.error("EDM", f"All download retries failed for '{dep.name}'")
                raise ConnectionError(
                    f"[EDM] Failed to download '{dep.name}' after {_MAX_RETRIES} attempts: {e}"
                ) from e

    # ── 4. Checksum verification ─────────────────────────────────────────────────
    if dep.checksum_sha256:
        actual = _sha256(dest)
        if actual != dep.checksum_sha256:
            dest.unlink()
            logger.error("EDM", f"Checksum mismatch for '{dep.name}'. Expected: {dep.checksum_sha256}, Got: {actual}")
            raise ValueError(
                f"[EDM] SHA256 mismatch for '{dep.name}'! "
                f"Expected: {dep.checksum_sha256}  Got: {actual}. "
                "The file may be corrupted or tampered with."
            )

    logger.debug("EDM", f"Download complete and verified for '{dep.name}'")
    return dest
