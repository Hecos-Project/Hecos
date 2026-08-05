import os
import tomllib
import urllib.request
from hecos.tray.config import UPDATE_SOURCES_FILE

# ─────────────────────────────────────────────────────────────────────────────
#  Default sources — shipped with Hecos, editable manually
# ─────────────────────────────────────────────────────────────────────────────
_TOML_HEADER = """\
# Hecos — Update Sources
# ─────────────────────────────────────────────────────────────────────────────
# This file works like eMule's servers.met: you can edit it by hand, or
# import a pre-built list from a URL (see the Dashboard → Updates tab).
#
# active_source  : name of the source to use when checking for updates
# [[sources]]    : one entry per source
#   name         : display name (must be unique)
#   url          : GitHub releases API URL  OR  custom JSON endpoint
#   type         : "github_release"  |  "custom_json"
#
# GitHub API format:
#   https://api.github.com/repos/<owner>/<repo>/releases/latest
#
# Custom JSON format — your server must return:
#   { "version": "1.2.3", "assets": [{"name": "file.exe", "url": "https://..."}] }
# ─────────────────────────────────────────────────────────────────────────────

"""

_DEFAULT_CONTENT = """\
active_source = "Hecos Official"

[[sources]]
name = "Hecos Official"
url  = "https://api.github.com/repos/Hecos-Project/Hecos/releases/latest"
type = "github_release"
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_file():
    """Create the sources TOML with defaults if it doesn't exist yet."""
    os.makedirs(os.path.dirname(UPDATE_SOURCES_FILE), exist_ok=True)
    if not os.path.exists(UPDATE_SOURCES_FILE):
        with open(UPDATE_SOURCES_FILE, "w", encoding="utf-8") as f:
            f.write(_TOML_HEADER + _DEFAULT_CONTENT)


def _write(data: dict):
    """Serialize `data` back to TOML, preserving the file header."""
    _ensure_file()
    lines = [_TOML_HEADER]
    lines.append(f'active_source = "{data.get("active_source", "")}"')
    lines.append("")
    for src in data.get("sources", []):
        lines.append("[[sources]]")
        lines.append(f'name = "{src.get("name", "")}"')
        lines.append(f'url  = "{src.get("url", "")}"')
        lines.append(f'type = "{src.get("type", "github_release")}"')
        lines.append("")
    with open(UPDATE_SOURCES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────
def load_sources() -> dict:
    _ensure_file()
    try:
        with open(UPDATE_SOURCES_FILE, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {"active_source": "Hecos Official", "sources": [
            {"name": "Hecos Official",
             "url": "https://api.github.com/repos/Hecos-Project/Hecos/releases/latest",
             "type": "github_release"}
        ]}


def save_sources(data: dict):
    try:
        _write(data)
    except Exception as e:
        print(f"[UPDATER] Could not save update sources: {e}")


def get_active_source_url() -> str:
    data = load_sources()
    active = data.get("active_source", "")
    for src in data.get("sources", []):
        if src.get("name") == active:
            return src.get("url", "")
    return ""


def add_source(name: str, url: str, source_type: str = "github_release"):
    data = load_sources()
    for src in data.get("sources", []):
        if src["name"] == name:
            src["url"] = url
            src["type"] = source_type
            save_sources(data)
            return
    data.setdefault("sources", []).append({"name": name, "url": url, "type": source_type})
    save_sources(data)


def remove_source(name: str):
    data = load_sources()
    data["sources"] = [s for s in data.get("sources", []) if s["name"] != name]
    if data.get("active_source") == name:
        data["active_source"] = data["sources"][0]["name"] if data["sources"] else ""
    save_sources(data)


def set_active_source(name: str):
    data = load_sources()
    data["active_source"] = name
    save_sources(data)


def _normalize_url(url: str) -> str:
    """
    Convert known paste/blob URLs to their raw equivalents so users
    can paste the friendly URL without worrying about /raw/.

    Supported conversions:
    - pastebin.com/<id>          -> pastebin.com/raw/<id>
    - github.com/.../blob/...    -> raw.githubusercontent.com/.../...
    """
    import re
    # Pastebin: https://pastebin.com/XXXXXXX -> https://pastebin.com/raw/XXXXXXX
    url = re.sub(
        r'^https?://pastebin\.com/(?!raw/)([A-Za-z0-9]+)$',
        r'https://pastebin.com/raw/\1',
        url
    )
    # GitHub blob: https://github.com/u/r/blob/branch/file
    #           -> https://raw.githubusercontent.com/u/r/branch/file
    url = re.sub(
        r'^https?://github\.com/([^/]+/[^/]+)/blob/(.+)$',
        r'https://raw.githubusercontent.com/\1/\2',
        url
    )
    return url


def import_source_list(url: str) -> tuple[int, str]:
    """
    Download a remote TOML source-list and merge its [[sources]] entries
    into the local file (skipping duplicates by name).

    Returns (added_count, error_message).
    """
    url = _normalize_url(url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hecos-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        # Guard against accidentally downloading HTML
        decoded = raw.decode("utf-8").lstrip()
        if decoded.startswith("<"):
            return 0, "The URL returned an HTML page. Use the raw/plain-text URL."
        remote = tomllib.loads(decoded)
        remote_sources = remote.get("sources", [])
        if not remote_sources:
            return 0, "No [[sources]] found in the remote file."

        local = load_sources()
        existing_names = {s["name"] for s in local.get("sources", [])}
        added = 0
        for src in remote_sources:
            if src.get("name") and src["name"] not in existing_names:
                local.setdefault("sources", []).append(src)
                existing_names.add(src["name"])
                added += 1
        save_sources(local)
        return added, ""
    except Exception as e:
        return 0, str(e)


def import_source_list_from_file(path: str) -> tuple[int, str]:
    """
    Load a local TOML source-list and merge its [[sources]] entries
    into the local config (skipping duplicates by name).

    Returns (added_count, error_message).
    """
    try:
        with open(path, "rb") as f:
            remote = tomllib.load(f)
        remote_sources = remote.get("sources", [])
        if not remote_sources:
            return 0, "No [[sources]] found in the file."

        local = load_sources()
        existing_names = {s["name"] for s in local.get("sources", [])}
        added = 0
        for src in remote_sources:
            if src.get("name") and src["name"] not in existing_names:
                local.setdefault("sources", []).append(src)
                existing_names.add(src["name"])
                added += 1
        save_sources(local)
        return added, ""
    except Exception as e:
        return 0, str(e)
