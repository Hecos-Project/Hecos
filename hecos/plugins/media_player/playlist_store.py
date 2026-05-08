"""
Hecos Media Player — Playlist Store (playlist_store.py)
CRUD for named playlists, persisted as JSON.

Storage: hecos/data/media_playlists.json
Format:
  {
    "my_playlist": {
      "name": "my_playlist",
      "created": "2026-05-08T...",
      "items": [
        {"path": "/abs/path/to/file.mp3", "name": "file.mp3", "type": "audio"},
        ...
      ]
    }
  }
"""

import os
import json
import time
from datetime import datetime
from typing import Optional

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[PLAYLIST]", *a)
        def error(self, *a): print("[PLAYLIST ERR]", *a)
        def debug(self, *a, **kw): pass
        def warning(self, *a): print("[PLAYLIST WARN]", *a)
    logger = _L()

# ─── Storage path ──────────────────────────────────────────────────────────────
_DATA_DIR  = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
_STORE_PATH = os.path.join(_DATA_DIR, "media_playlists.json")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v", ".mkv", ".avi"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".oga", ".flac", ".aac", ".m4a", ".opus", ".wma"}

def _media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS: return "image"
    if ext in VIDEO_EXTS: return "video"
    if ext in AUDIO_EXTS: return "audio"
    return "unknown"


# ─── Persistence ────────────────────────────────────────────────────────────────

def _load() -> dict:
    if not os.path.exists(_STORE_PATH):
        return {}
    try:
        with open(_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Playlist] Load error: {e}")
        return {}


def _save(data: dict) -> bool:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"[Playlist] Save error: {e}")
        return False


# ─── Public API ─────────────────────────────────────────────────────────────────

def list_playlists() -> list[dict]:
    """Returns a list of all playlist summaries."""
    data = _load()
    return [
        {
            "name":    pl["name"],
            "count":   len(pl.get("items", [])),
            "created": pl.get("created", ""),
        }
        for pl in data.values()
    ]


def get_playlist(name: str) -> Optional[dict]:
    """Returns a playlist dict or None if not found."""
    data = _load()
    return data.get(name)


def create_playlist(name: str, items: list[str] | None = None) -> dict:
    """
    Creates a new (or replaces an existing) playlist.
    items: list of file paths as strings.
    Returns the created playlist dict.
    """
    data = _load()
    playlist = {
        "name":    name,
        "created": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "items":   []
    }
    for path in (items or []):
        path = os.path.abspath(path) if not path.startswith("http") else path
        playlist["items"].append({
            "path": path,
            "name": os.path.basename(path),
            "type": _media_type(path),
        })
    data[name] = playlist
    _save(data)
    logger.info(f"[Playlist] Created '{name}' with {len(playlist['items'])} items.")
    return playlist


def add_to_playlist(name: str, path: str) -> bool:
    """Appends a file to an existing playlist. Creates playlist if missing."""
    data = _load()
    if name not in data:
        create_playlist(name, [path])
        return True
    abs_path = os.path.abspath(path) if not path.startswith("http") else path
    data[name]["items"].append({
        "path": abs_path,
        "name": os.path.basename(abs_path),
        "type": _media_type(abs_path),
    })
    return _save(data)


def remove_from_playlist(name: str, index: int) -> bool:
    """Removes item at index from a playlist."""
    data = _load()
    if name not in data:
        return False
    items = data[name]["items"]
    if index < 0 or index >= len(items):
        return False
    items.pop(index)
    return _save(data)


def delete_playlist(name: str) -> bool:
    """Deletes an entire playlist."""
    data = _load()
    if name not in data:
        return False
    del data[name]
    _save(data)
    logger.info(f"[Playlist] Deleted '{name}'.")
    return True


def build_playlist_from_folder(folder: str, recursive: bool = False) -> list[str]:
    """
    Scans a folder and returns sorted list of playable file paths.
    Useful for LLM tool: 'play everything in Music/Jazz'.
    """
    exts = AUDIO_EXTS | VIDEO_EXTS
    found = []
    if recursive:
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in exts:
                    found.append(os.path.join(root, f))
    else:
        if os.path.isdir(folder):
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in exts:
                    found.append(os.path.join(folder, f))
    return found
