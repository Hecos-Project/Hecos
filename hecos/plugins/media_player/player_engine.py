"""
Hecos Media Player — OS-Level Playback Engine (player_engine.py)
Provides cross-platform media playback via VLC, mpv, or system default.

Priority chain:
  1. python-vlc (if installed)        → full control: pause, stop, volume, seek
  2. mpv (if on PATH)                 → via subprocess, proper process tracking
  3. system default player            → winsound SND_ASYNC + duration timer (WAV)
                                        afplay (macOS), ffplay/aplay (Linux)
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

def _setup_vlc_path_win():
    """On Windows, help python-vlc find libvlc.dll in standard install locations."""
    if sys.platform != "win32":
        return
    if os.environ.get("PYTHON_VLC_MODULE_PATH"):
        return  # already set
    candidates = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\VideoLAN\VLC"),
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "libvlc.dll")):
            os.environ["PYTHON_VLC_MODULE_PATH"] = path
            # Also add to DLL search path
            os.add_dll_directory(path)
            logger.info(f"[MediaEngine] VLC DLL path set: {path}")
            return


def _has_vlc() -> bool:
    _setup_vlc_path_win()
    try:
        import vlc  # noqa
        _test = vlc.Instance("--quiet")
        del _test
        return True
    except (ImportError, OSError, Exception) as e:
        logger.debug(f"[MediaEngine] VLC not available: {e}")
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

    def set_volume(self, vol: int):
        self._player.audio_set_volume(max(0, min(100, vol)))

    def get_volume(self) -> int:
        return self._player.audio_get_volume()

    def seek(self, seconds: float):
        length = self._player.get_length() / 1000
        if length > 0:
            pos = max(0.0, min(1.0, seconds / length))
            self._player.set_position(pos)

    def get_position(self) -> float:
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
        logger.warning("[MediaEngine] mpv backend: volume control not supported.")

    def get_volume(self) -> int: return -1
    def seek(self, seconds: float): pass
    def get_position(self) -> float: return 0.0
    def get_length(self) -> float: return 0.0

    def is_playing(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def is_finished(self) -> bool:
        return self._proc is None or self._proc.poll() is not None


# ─── System Default Backend ────────────────────────────────────────────────────
# Windows WAV  → winsound.SND_ASYNC + wave header duration tracking
# Windows other → PowerShell Start-Process -Wait in a thread
# macOS         → afplay (blocking in a thread)
# Linux         → ffplay -nodisp -autoexit, fallback to aplay

class SystemPlayer:
    def __init__(self):
        self._playing    = False
        self._duration   = 0.0   # estimated track duration in seconds
        self._start_time = 0.0   # monotonic time when play() was called
        self._timer: threading.Timer | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _wav_duration(self, path: str) -> float:
        """Return duration of a WAV file in seconds, or 0 on failure."""
        try:
            import wave
            with wave.open(path, "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            return 0.0

    def _mark_finished(self):
        self._playing = False

    def _play_in_thread(self, target, args=()):
        """Run a blocking play call in a daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=target, args=args, daemon=True, name="HecosPlay")
        self._thread.start()

    # ── Platform play implementations ─────────────────────────────────────────

    def _win_wav(self, path: str):
        """Windows WAV: async winsound + duration-based finish detection."""
        try:
            import winsound
            dur = self._wav_duration(path)
            self._duration   = dur
            self._start_time = time.monotonic()
            self._playing    = True
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            if dur > 0:
                # Block this thread for the audio duration (respects stop_event)
                self._stop_event.wait(timeout=dur)
            else:
                # Unknown duration — poll until stop requested
                while not self._stop_event.is_set():
                    time.sleep(0.5)
        except Exception as e:
            logger.error(f"[MediaEngine] winsound error: {e}")
        finally:
            self._playing = False

    def _win_other(self, path: str):
        """Windows non-WAV: PowerShell Start-Process -Wait."""
        try:
            escaped = path.replace("'", "''")
            ps_cmd = (
                f"$p = Start-Process -FilePath '{escaped}' -PassThru; "
                f"$p.WaitForExit()"
            )
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            while not self._stop_event.is_set():
                try:
                    proc.wait(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.poll() is None:
                proc.terminate()
        except Exception as e:
            logger.error(f"[MediaEngine] PowerShell play error: {e}")
        finally:
            self._playing = False

    def _linux_play(self, path: str):
        """Linux: ffplay or aplay (blocking subprocess)."""
        cmds = [
            ["ffplay", "-nodisp", "-autoexit", path],
            ["aplay", path],
        ]
        proc = None
        for cmd in cmds:
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                break
            except FileNotFoundError:
                continue
        if proc is None:
            logger.error("[MediaEngine] No audio player found (install ffplay or aplay).")
            self._playing = False
            return
        try:
            while not self._stop_event.is_set():
                try:
                    proc.wait(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.poll() is None:
                proc.terminate()
        finally:
            self._playing = False

    def _mac_play(self, path: str):
        """macOS: afplay (blocking subprocess)."""
        try:
            proc = subprocess.Popen(
                ["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            while not self._stop_event.is_set():
                try:
                    proc.wait(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.poll() is None:
                proc.terminate()
        except Exception as e:
            logger.error(f"[MediaEngine] afplay error: {e}")
        finally:
            self._playing = False

    # ── Public API ────────────────────────────────────────────────────────────

    def play(self, path_or_url: str):
        self.stop()
        _ext = os.path.splitext(path_or_url)[1].lower()
        if sys.platform == "win32":
            if _ext == ".wav":
                self._play_in_thread(self._win_wav, (path_or_url,))
            else:
                self._playing = True
                self._play_in_thread(self._win_other, (path_or_url,))
        elif sys.platform == "darwin":
            self._playing = True
            self._play_in_thread(self._mac_play, (path_or_url,))
        else:
            self._playing = True
            self._play_in_thread(self._linux_play, (path_or_url,))

    def pause(self):
        # winsound/afplay/ffplay don't support mid-track pause
        logger.warning("[MediaEngine] System backend: pause not supported. Use stop/play.")

    def stop(self):
        self._stop_event.set()
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE | winsound.SND_ASYNC)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread  = None
        self._playing = False
        self._stop_event.clear()

    def set_volume(self, vol: int):
        pass  # not supported in system backend

    def get_volume(self) -> int:
        return -1

    def seek(self, seconds: float):
        pass

    def get_position(self) -> float:
        if self._playing and self._start_time > 0:
            return time.monotonic() - self._start_time
        return 0.0

    def get_length(self) -> float:
        return self._duration

    def is_playing(self) -> bool:
        return self._playing

    def is_finished(self) -> bool:
        if self._thread is None:
            return True
        return not self._thread.is_alive()


# ─── Engine Factory ────────────────────────────────────────────────────────────

def create_engine():
    """Returns the best available playback backend."""
    if BACKEND == "vlc":
        try:
            return VLCPlayer()
        except Exception as e:
            logger.warning(f"[MediaEngine] VLC init failed ({e}), falling back to mpv.")
    if BACKEND in ("mpv", "vlc"):
        try:
            return MpvPlayer()
        except Exception as e:
            logger.warning(f"[MediaEngine] mpv init failed ({e}), falling back to system.")
    return SystemPlayer()
