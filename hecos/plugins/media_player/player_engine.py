"""
Hecos Media Player — OS-Level Playback Engine (player_engine.py)
Provides cross-platform media playback via VLC, mpv, or system default.

Priority chain:
  1. python-vlc (if installed)        → full control: pause, stop, volume, seek
  2. mpv (if on PATH)                 → via subprocess
  3. system default player            → subprocess, fire-and-forget
"""

import os
import sys
import subprocess
import threading
import time

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[MEDIA_ENGINE]", *a)
        def error(self, *a): print("[MEDIA_ENGINE ERR]", *a)
        def debug(self, *a, **kw): pass
        def warning(self, *a): print("[MEDIA_ENGINE WARN]", *a)
    logger = _L()


# ─── Backend detection ──────────────────────────────────────────────────────────

def _has_vlc() -> bool:
    try:
        import vlc  # noqa
        return True
    except ImportError:
        return False

def _has_mpv() -> bool:
    try:
        result = subprocess.run(["mpv", "--version"], capture_output=True, timeout=2)
        return result.returncode == 0
    except Exception:
        return False

def _detect_backend() -> str:
    if _has_vlc():
        return "vlc"
    if _has_mpv():
        return "mpv"
    return "system"

BACKEND = _detect_backend()
logger.info(f"[MediaEngine] Detected playback backend: {BACKEND}")


# ─── VLC Backend ───────────────────────────────────────────────────────────────

class VLCPlayer:
    def __init__(self):
        import vlc
        self._instance = vlc.Instance("--no-xlib --quiet")
        self._player   = self._instance.media_player_new()
        self._vlc      = vlc

    def play(self, path_or_url: str):
        media = self._instance.media_new(path_or_url)
        self._player.set_media(media)
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def set_volume(self, vol: int):  # 0–100
        self._player.audio_set_volume(max(0, min(100, vol)))

    def get_volume(self) -> int:
        return self._player.audio_get_volume()

    def seek(self, seconds: float):
        length = self._player.get_length() / 1000  # ms → s
        if length > 0:
            pos = max(0.0, min(1.0, seconds / length))
            self._player.set_position(pos)

    def get_position(self) -> float:
        """Returns elapsed seconds."""
        return self._player.get_time() / 1000

    def get_length(self) -> float:
        return self._player.get_length() / 1000

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def is_finished(self) -> bool:
        state = self._player.get_state()
        return state in (self._vlc.State.Ended, self._vlc.State.Error, self._vlc.State.Stopped)


# ─── mpv Backend ───────────────────────────────────────────────────────────────

class MpvPlayer:
    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def play(self, path_or_url: str):
        self.stop()
        self._proc = subprocess.Popen(
            ["mpv", "--no-terminal", path_or_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def pause(self):
        logger.warning("[MediaEngine] mpv backend: pause not supported in subprocess mode.")

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try: self._proc.wait(timeout=3)
            except Exception: self._proc.kill()
        self._proc = None

    def set_volume(self, vol: int):
        logger.warning("[MediaEngine] mpv backend: volume control not supported in subprocess mode.")

    def get_volume(self) -> int:
        return -1

    def seek(self, seconds: float):
        logger.warning("[MediaEngine] mpv backend: seek not supported in subprocess mode.")

    def get_position(self) -> float:
        return 0.0

    def get_length(self) -> float:
        return 0.0

    def is_playing(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def is_finished(self) -> bool:
        return self._proc is None or self._proc.poll() is not None


# ─── System Default Backend ────────────────────────────────────────────────────

class SystemPlayer:
    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def _open_cmd(self, path: str) -> list[str]:
        if sys.platform == "win32":
            return ["cmd", "/c", "start", "", path]
        elif sys.platform == "darwin":
            return ["open", path]
        else:
            return ["xdg-open", path]

    def play(self, path_or_url: str):
        self.stop()
        try:
            cmd = self._open_cmd(path_or_url)
            self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"[MediaEngine] SystemPlayer error: {e}")

    def pause(self):
        logger.warning("[MediaEngine] System backend: pause not supported.")

    def stop(self):
        if self._proc and self._proc.poll() is None:
            try: self._proc.terminate()
            except Exception: pass
        self._proc = None

    def set_volume(self, vol: int): pass
    def get_volume(self) -> int: return -1
    def seek(self, seconds: float): pass
    def get_position(self) -> float: return 0.0
    def get_length(self) -> float: return 0.0
    def is_playing(self) -> bool: return self._proc is not None and self._proc.poll() is None
    def is_finished(self) -> bool: return self._proc is None or self._proc.poll() is not None


# ─── Engine Factory ────────────────────────────────────────────────────────────

def create_engine():
    """Returns the best available playback backend."""
    if BACKEND == "vlc":
        try:
            return VLCPlayer()
        except Exception as e:
            logger.warning(f"[MediaEngine] VLC init failed ({e}), falling back to mpv.")
    if BACKEND == "mpv" or BACKEND == "vlc":
        try:
            return MpvPlayer()
        except Exception as e:
            logger.warning(f"[MediaEngine] mpv init failed ({e}), falling back to system.")
    return SystemPlayer()
