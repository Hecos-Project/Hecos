"""
routes_shortcuts.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Keyboard Shortcuts Backend Routes
Provides API endpoints for persisting user keyboard shortcut bindings and
preferences server-side (per-user, stored in data/users/<username>/shortcuts.json).
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import logging

from flask import request, jsonify
from flask_login import current_user, login_required


log = logging.getLogger("hecos.web_ui.shortcuts")


# ── Default bindings (mirrors hks_bindings.js DEFAULTS) ───────────────────────

DEFAULT_BINDINGS = {
    "nav.help":          "f1",
    "nav.backend":       "f2",
    "nav.ia":            "f3",
    "ui.toggle_mic":     "f4",
    "ui.toggle_voice":   "f6",
    "nav.hub":           "f7",
    "ui.toggle_ptt":     "f8",
    "sys.reboot":        "f9",
    
    "nav.chat":          "f10",
    "nav.home":          "f11",
    "ui.open_hdcs":      "f12",
    
    "ui.ptt_trigger":    "ctrl+shift",
    "nav.packages":      "ctrl+shift+p",
    "nav.drive":         "ctrl+shift+d",
    "nav.flows":         "ctrl+shift+f",
    "ui.toggle_room":    "ctrl+shift+r",
    "ui.toggle_sidebar": "ctrl+b",
    "ui.new_chat":       "ctrl+enter",
    
    "ui.show_cheatsheet":"?",
    "nav.shortcuts":     "ctrl+,",
    "ui.close_modal":    "escape",
    "ui.copy_last":      "ctrl+shift+c",
    "ui.toggle_history": "ctrl+shift+h",
    "ui.focus_input":    "ctrl+shift+i",
    "focus.next":        "ctrl+tab",
    "focus.prev":        "ctrl+shift+tab",
}

DEFAULT_PREFS = {
    "toastEnabled":    True,
    "fKeysEnabled":    True,
    "tabCycleEnabled": True,
}


def _user_shortcuts_path(root_dir: str, username: str) -> str:
    """Return the path to the user's shortcuts.json file."""
    return os.path.join(root_dir, "hecos", "data", "users", username, "shortcuts.json")


def _load_user_shortcuts(root_dir: str, username: str) -> dict:
    """Load shortcuts from disk, merging with defaults for any missing keys."""
    path = _user_shortcuts_path(root_dir, username)
    data = {"bindings": {}, "prefs": {}}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.warning(f"[Shortcuts] Could not load {path}: {e}")

    # Merge with defaults (new defaults in updates survive existing user files)
    merged_bindings = dict(DEFAULT_BINDINGS)
    merged_bindings.update(data.get("bindings", {}))

    merged_prefs = dict(DEFAULT_PREFS)
    merged_prefs.update(data.get("prefs", {}))

    return {"bindings": merged_bindings, "prefs": merged_prefs}


def _save_user_shortcuts(root_dir: str, username: str, bindings: dict, prefs: dict) -> bool:
    """Save shortcuts to disk."""
    path = _user_shortcuts_path(root_dir, username)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"bindings": bindings, "prefs": prefs}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log.error(f"[Shortcuts] Could not save {path}: {e}")
        return False


def init_shortcuts_routes(app, root_dir: str, logger=None):
    """Register keyboard shortcut API endpoints."""

    global log
    if logger:
        log = logger

    # ── GET /api/shortcuts/bindings ───────────────────────────────────────────

    @app.route("/api/shortcuts/bindings", methods=["GET"])
    @login_required
    def get_shortcuts_bindings():
        """Return the current user's shortcut bindings and preferences."""
        username = current_user.username if current_user.is_authenticated else "anonymous"
        data = _load_user_shortcuts(root_dir, username)
        return jsonify({"ok": True, **data})

    # ── POST /api/shortcuts/bindings ──────────────────────────────────────────

    @app.route("/api/shortcuts/bindings", methods=["POST"])
    @login_required
    def save_shortcuts_bindings():
        """Save the current user's shortcut bindings and preferences."""
        username = current_user.username if current_user.is_authenticated else "anonymous"

        body = request.get_json(silent=True) or {}
        bindings = body.get("bindings")
        prefs    = body.get("prefs")

        if bindings is None and prefs is None:
            return jsonify({"ok": False, "error": "No bindings or prefs provided"}), 400

        # If partial update, load existing and merge
        existing = _load_user_shortcuts(root_dir, username)
        if bindings is not None:
            existing["bindings"].update(bindings)
        if prefs is not None:
            existing["prefs"].update(prefs)

        ok = _save_user_shortcuts(root_dir, username,
                                  existing["bindings"], existing["prefs"])
        if ok:
            log.debug(f"[Shortcuts] Saved bindings for user '{username}'.")
            return jsonify({"ok": True, "message": "Shortcuts saved"})
        else:
            return jsonify({"ok": False, "error": "Failed to save shortcuts"}), 500

    # ── POST /api/shortcuts/reset ─────────────────────────────────────────────

    @app.route("/api/shortcuts/reset", methods=["POST"])
    @login_required
    def reset_shortcuts_bindings():
        """Reset the current user's bindings to defaults."""
        username = current_user.username if current_user.is_authenticated else "anonymous"
        ok = _save_user_shortcuts(root_dir, username, DEFAULT_BINDINGS, DEFAULT_PREFS)
        if ok:
            log.info(f"[Shortcuts] Reset to defaults for user '{username}'.")
            return jsonify({"ok": True, "bindings": DEFAULT_BINDINGS, "prefs": DEFAULT_PREFS})
        return jsonify({"ok": False, "error": "Reset failed"}), 500

    # ── GET /api/shortcuts/defaults ───────────────────────────────────────────

    @app.route("/api/shortcuts/defaults", methods=["GET"])
    @login_required
    def get_shortcuts_defaults():
        """Return the default bindings (read-only, no user data)."""
        return jsonify({"ok": True, "bindings": DEFAULT_BINDINGS, "prefs": DEFAULT_PREFS})

    log.debug("[WebUI] Keyboard shortcuts routes registered.")
