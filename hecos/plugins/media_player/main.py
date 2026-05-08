"""
Hecos Media Player — Main Plugin Entry Point (main.py)
Exposes LLM tools for OS-level media playback and playlist management.
Loaded at boot via manifest (is_class_based: true, on_load: true).

LLM Tools:
  play(path_or_url, playlist_name?)    → play a file or a playlist
  pause()                               → pause/resume current track
  stop()                                → stop playback
  next_track()                          → advance to next track in queue
  prev_track()                          → go back to previous track
  set_volume(level)                     → 0–100
  get_status()                          → current playback state
  create_playlist(name, items?)         → create a named playlist
  add_to_playlist(name, path)           → add a file to a playlist
  remove_from_playlist(name, index)     → remove item by index
  delete_playlist(name)                 → delete a playlist
  list_playlists()                      → list all playlists
  get_playlist(name)                    → get playlist contents
  play_playlist(name, shuffle?)         → play a saved playlist
  scan_folder(folder, save_as?, recursive?) → build playlist from folder
"""

import os
import random
import threading
from typing import Optional

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[MEDIA_PLAYER]", *a)
        def error(self, *a): print("[MEDIA_PLAYER ERR]", *a)
        def debug(self, *a, **kw): pass
        def warning(self, *a): print("[MEDIA_PLAYER WARN]", *a)
    logger = _L()

from hecos.plugins.media_player.player_engine import create_engine
from hecos.plugins.media_player import playlist_store


TAG = "MEDIA_PLAYER"


class MediaPlayerTools:
    """Hecos Media Player — exposes all LLM tools and manages playback state."""

    def __init__(self, config=None):
        self.tag  = TAG
        self.desc = "Media player: play audio/video, manage playlists via AI or dashboard."
        self._cfg = config or {}
        self._engine = None   # lazy-init on first play
        self._queue: list[dict] = []   # current play queue
        self._queue_index: int = 0
        self._shuffle: bool = False
        self._repeat: bool = False
        self._lock = threading.Lock()
        self._watchdog: threading.Thread | None = None

    # ── Engine (lazy) ──────────────────────────────────────────────────────────────

    def _get_engine(self):
        if self._engine is None:
            self._engine = create_engine()
            logger.info(f"[MediaPlayer] Engine initialized.")
        return self._engine

    # ── Watchdog — auto-advance queue ─────────────────────────────────────────────

    def _start_watchdog(self):
        if self._watchdog and self._watchdog.is_alive():
            return
        self._watchdog = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="HecosMediaWatchdog"
        )
        self._watchdog.start()

    def _watchdog_loop(self):
        """Watches for track end and advances to the next track automatically."""
        import time
        while True:
            time.sleep(1)
            with self._lock:
                if not self._queue:
                    continue
                engine = self._get_engine()
                if engine.is_finished():
                    self._advance()

    def _advance(self):
        """Advance to next track in queue. Called with lock held."""
        if not self._queue:
            return
        if self._shuffle:
            self._queue_index = random.randint(0, len(self._queue) - 1)
        else:
            self._queue_index += 1
            if self._queue_index >= len(self._queue):
                if self._repeat:
                    self._queue_index = 0
                else:
                    logger.info("[MediaPlayer] Playlist finished.")
                    return
        item = self._queue[self._queue_index]
        self._get_engine().play(item["path"])
        logger.info(f"[MediaPlayer] Auto-advanced to: {item['name']}")

    # ── LLM TOOLS ─────────────────────────────────────────────────────────────────

    def play(self, path_or_url: str, playlist_name: str = None) -> str:
        """
        Play a media file or URL.
        Optionally specify a playlist_name to load a full queue.

        :param path_or_url: Absolute file path or HTTP/HTTPS URL to play.
        :param playlist_name: (Optional) The name of a saved playlist to queue up.
        """
        with self._lock:
            if playlist_name:
                return self.play_playlist(playlist_name)

            # Resolve path
            if not path_or_url.startswith("http"):
                path_or_url = os.path.abspath(path_or_url)
                if not os.path.isfile(path_or_url):
                    return f"❌ File not found: {path_or_url}"

            self._queue = [{
                "path": path_or_url,
                "name": os.path.basename(path_or_url),
                "type": playlist_store._media_type(path_or_url),
            }]
            self._queue_index = 0

            self._get_engine().play(path_or_url)
            self._start_watchdog()
            name = os.path.basename(path_or_url)
            logger.info(f"[MediaPlayer] Playing: {name}")
            return f"▶️ Now playing: **{name}**"

    def pause(self) -> str:
        """
        Pause or resume the current track.
        """
        engine = self._get_engine()
        engine.pause()
        state = "⏸ Paused" if engine.is_playing() is False else "▶️ Resumed"
        return state

    def stop(self) -> str:
        """
        Stop playback completely.
        """
        self._get_engine().stop()
        with self._lock:
            self._queue = []
            self._queue_index = 0
        return "⏹ Playback stopped."

    def next_track(self) -> str:
        """
        Skip to the next track in the current queue.
        """
        with self._lock:
            if not self._queue:
                return "⚠️ No active queue."
            self._advance()
            item = self._queue[self._queue_index] if self._queue else None
        return f"⏭ Now playing: **{item['name']}**" if item else "⚠️ Queue ended."

    def prev_track(self) -> str:
        """
        Go back to the previous track in the current queue.
        """
        with self._lock:
            if not self._queue:
                return "⚠️ No active queue."
            self._queue_index = max(0, self._queue_index - 1)
            item = self._queue[self._queue_index]
            self._get_engine().play(item["path"])
        return f"⏮ Now playing: **{item['name']}**"

    def set_volume(self, level: int) -> str:
        """
        Set playback volume.

        :param level: Volume from 0 (mute) to 100 (max).
        """
        level = max(0, min(100, int(level)))
        self._get_engine().set_volume(level)
        return f"🔊 Volume set to {level}%"

    def get_status(self) -> str:
        """
        Return the current playback status (track name, position, volume).
        """
        engine = self._get_engine()
        is_playing = engine.is_playing()
        state = "▶️ Playing" if is_playing else "⏸ Paused/Stopped"
        with self._lock:
            track = self._queue[self._queue_index]["name"] if self._queue else "—"
            total = len(self._queue)
            idx = self._queue_index + 1

        pos = engine.get_position()
        dur = engine.get_length()
        vol = engine.get_volume()

        time_str = ""
        if dur > 0:
            def _fmt(s): return f"{int(s//60)}:{int(s%60):02d}"
            time_str = f" [{_fmt(pos)} / {_fmt(dur)}]"

        vol_str = f"Vol {vol}%" if vol >= 0 else ""

        return (
            f"{state} — **{track}**{time_str}\n"
            f"Track {idx}/{total}  {vol_str}"
            + (f"  🔀 Shuffle" if self._shuffle else "")
            + (f"  🔁 Repeat"  if self._repeat  else "")
        )

    # ── Playlist LLM Tools ────────────────────────────────────────────────────────

    def create_playlist(self, name: str, items: str = "") -> str:
        """
        Create a named playlist with a list of file paths.

        :param name: Playlist name (e.g. 'Jazz Evening').
        :param items: Comma-separated list of absolute file paths.
        """
        paths = [p.strip() for p in items.split(",") if p.strip()] if items else []
        pl = playlist_store.create_playlist(name, paths)
        return f"✅ Playlist **{name}** created with {len(pl['items'])} tracks."

    def add_to_playlist(self, name: str, path: str) -> str:
        """
        Add a file to an existing playlist (creates it if missing).

        :param name: Playlist name.
        :param path: Absolute file path to add.
        """
        ok = playlist_store.add_to_playlist(name, path.strip())
        fname = os.path.basename(path.strip())
        return f"➕ Added **{fname}** to playlist **{name}**." if ok else "❌ Error adding to playlist."

    def remove_from_playlist(self, name: str, index: int) -> str:
        """
        Remove a track from a playlist by its position (1-based).

        :param name: Playlist name.
        :param index: 1-based position of the track to remove.
        """
        ok = playlist_store.remove_from_playlist(name, int(index) - 1)
        return f"🗑 Track {index} removed from **{name}**." if ok else "❌ Error removing track."

    def delete_playlist(self, name: str) -> str:
        """
        Delete a named playlist permanently.

        :param name: Playlist name to delete.
        """
        ok = playlist_store.delete_playlist(name)
        return f"🗑 Playlist **{name}** deleted." if ok else f"❌ Playlist '{name}' not found."

    def list_playlists(self) -> str:
        """
        List all saved playlists with their track count.
        """
        playlists = playlist_store.list_playlists()
        if not playlists:
            return "📋 No playlists saved yet. Use `create_playlist` to make one."
        lines = [f"📋 **Saved Playlists** ({len(playlists)} total):"]
        for pl in playlists:
            lines.append(f"  • **{pl['name']}** — {pl['count']} tracks")
        return "\n".join(lines)

    def get_playlist(self, name: str) -> str:
        """
        Show the contents of a saved playlist.

        :param name: Playlist name.
        """
        pl = playlist_store.get_playlist(name)
        if not pl:
            return f"❌ Playlist '{name}' not found."
        lines = [f"📋 **{pl['name']}** ({len(pl['items'])} tracks):\n"]
        for i, item in enumerate(pl["items"], 1):
            lines.append(f"  {i}. `{item['name']}` [{item['type']}]")
        return "\n".join(lines)

    def play_playlist(self, name: str, shuffle: bool = False) -> str:
        """
        Load and play a saved playlist.

        :param name: Playlist name.
        :param shuffle: If True, play tracks in random order.
        """
        pl = playlist_store.get_playlist(name)
        if not pl or not pl.get("items"):
            return f"❌ Playlist '{name}' not found or empty."

        with self._lock:
            self._queue = list(pl["items"])
            self._shuffle = shuffle
            if shuffle:
                random.shuffle(self._queue)
            self._queue_index = 0
            item = self._queue[0]
            self._get_engine().play(item["path"])
            self._start_watchdog()

        suffix = " 🔀 (shuffled)" if shuffle else ""
        return f"▶️ Playing playlist **{name}**{suffix} — {len(self._queue)} tracks."

    def scan_folder(self, folder: str, save_as: str = "", recursive: bool = False) -> str:
        """
        Scan a folder for audio/video files and optionally save as a playlist.

        :param folder: Absolute path to the folder to scan.
        :param save_as: If provided, save the result as a named playlist.
        :param recursive: If True, scan subfolders too.
        """
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            return f"❌ Folder not found: {folder}"

        paths = playlist_store.build_playlist_from_folder(folder, recursive=recursive)
        if not paths:
            return f"📂 No playable media found in: {folder}"

        if save_as:
            pl = playlist_store.create_playlist(save_as, paths)
            return f"📁 Found {len(paths)} files. Saved as playlist **{save_as}**."

        lines = [f"📁 Found {len(paths)} files in `{folder}`:"]
        for p in paths[:20]:
            lines.append(f"  • `{os.path.basename(p)}`")
        if len(paths) > 20:
            lines.append(f"  ... and {len(paths) - 20} more.")
        lines.append("\n_Use `save_as` parameter to save as a playlist._")
        return "\n".join(lines)


# ─── Plugin singleton ──────────────────────────────────────────────────────────

tools = MediaPlayerTools()


def on_load(config: dict):
    """Called at Hecos boot. Injects config into the plugin."""
    global tools
    tools._cfg = config.get("plugins", {}).get(TAG, {})
    vol = tools._cfg.get("default_volume", 80)
    try:
        tools._get_engine().set_volume(vol)
    except Exception:
        pass
    logger.info(f"[MediaPlayer] Plugin loaded. Default volume: {vol}%")


# ─── Standard plugin interface ─────────────────────────────────────────────────

def info():
    return {
        "tag":  TAG,
        "desc": tools.desc,
        "commands": {
            "play":                "Play a media file or URL",
            "pause":               "Pause/resume playback",
            "stop":                "Stop playback",
            "next_track":          "Skip to next track",
            "prev_track":          "Go to previous track",
            "set_volume":          "Set volume (0–100)",
            "get_status":          "Get current playback status",
            "create_playlist":     "Create a named playlist",
            "add_to_playlist":     "Add a file to a playlist",
            "remove_from_playlist":"Remove a track from a playlist",
            "delete_playlist":     "Delete a playlist",
            "list_playlists":      "List all saved playlists",
            "get_playlist":        "Show playlist contents",
            "play_playlist":       "Load and play a saved playlist",
            "scan_folder":         "Scan a folder for media files",
        }
    }


def status():
    return "ONLINE"


def get_plugin():
    return tools
