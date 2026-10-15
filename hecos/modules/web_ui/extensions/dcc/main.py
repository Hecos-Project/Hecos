"""
DCC — Dynamic Capability Chips
Routes for the chips API endpoint.
Builds a hierarchical, Hub-category-aware chip structure from the HDCS Command Registry.
"""
import os
from flask import send_from_directory, jsonify
from flask_login import login_required, current_user
from hecos.core.logging import logger


# ── plugin_tag → Hub category (mirrors config_manifest.js CONFIG_HUB.modules) ──
# Keys are uppercase plugin_tag values from the command registry.
_TAG_TO_HUB_CAT = {
    # INTELLIGENZA
    "MODELS":       "INTELLIGENZA",
    "MEMORY":       "INTELLIGENZA",
    "PERSONALITY":  "INTELLIGENZA",
    "HDCS":         "INTELLIGENZA",
    "EXECUTOR":     "INTELLIGENZA",
    "AGENT":        "INTELLIGENZA",

    # MULTIMEDIA
    "IMAGE_GEN":    "MULTIMEDIA",
    "WEBCAM":       "MULTIMEDIA",
    "AUDIO":        "MULTIMEDIA",
    "VOICE":        "MULTIMEDIA",
    "VIDEO":        "MULTIMEDIA",

    # CONNETTIVITÀ
    "BROWSER":      "CONNETTIVITÀ",
    "SEARCH":       "CONNETTIVITÀ",
    "MESSENGER":    "CONNETTIVITÀ",
    "CONTACTS":     "CONNETTIVITÀ",
    "REMOTE":       "CONNETTIVITÀ",
    "MAIL":         "CONNETTIVITÀ",

    # RISORSE
    "DRIVE":        "RISORSE",
    "DRIVE_EDITOR": "RISORSE",
    "DOCS":         "RISORSE",
    "FILES":        "RISORSE",
    "CODE":         "RISORSE",
    "CALENDAR":     "RISORSE",
    "REMINDER":     "RISORSE",

    # SISTEMA
    "AUTOMATION":   "SISTEMA",
    "UTILS":        "SISTEMA",
    "SYSTEM":       "SISTEMA",
    "BUILDER":      "SISTEMA",
    "NOTIFICATIONS":"CONNETTIVITÀ",
    "USERS":        "SISTEMA",
    "DOCUMENT_MAKER":"RISORSE",
}

# Hub category display metadata
_HUB_CATS = {
    "INTELLIGENZA": {"id": "intelligenza", "label": "Intelligence", "icon": "fas fa-brain",        "color": "#66fcf1", "order": 1},
    "MULTIMEDIA":   {"id": "multimedia",   "label": "Multimedia",   "icon": "fas fa-compact-disc", "color": "#ec4899", "order": 2},
    "CONNETTIVITÀ": {"id": "connettivita", "label": "Connectivity", "icon": "fas fa-network-wired","color": "#3b82f6", "order": 3},
    "RISORSE":      {"id": "risorse",      "label": "Resources",    "icon": "fas fa-folder-open",  "color": "#f59e0b", "order": 4},
    "SISTEMA":      {"id": "sistema",      "label": "System",       "icon": "fas fa-cogs",         "color": "#45a29e", "order": 5},
}

# Display metadata per plugin_tag (module-level chip)
_TAG_META = {
    "MEMORY":       {"label": "Memory",     "icon": "fas fa-memory",        "action": None, "short": "Remember info", "prompt": "Remember this important detail..."},
    "IMAGE_GEN":    {"label": "Image Gen",  "icon": "fas fa-image",         "action": None, "short": "Draw picture",  "prompt": "Draw a picture of a futuristic city"},
    "BROWSER":      {"label": "Browser",    "icon": "fas fa-globe",         "action": None, "short": "Search web",    "prompt": "Search online for the latest news"},
    "SEARCH":       {"label": "Search",     "icon": "fas fa-search",        "action": None, "short": "Look up",       "prompt": "Search the web"},
    "AUDIO":        {"label": "Audio",      "icon": "fas fa-music",         "action": None, "short": "Make audio",    "prompt": "Generate a sound effect for..."},
    "VIDEO":        {"label": "Video",      "icon": "fas fa-video",         "action": None, "short": "Make video",    "prompt": "Create a video animation of..."},
    "DOCS":         {"label": "Docs",       "icon": "fas fa-file-alt",      "action": None, "short": "Summarize",     "prompt": "Summarize this document for me"},
    "CODE":         {"label": "Code",       "icon": "fas fa-code",          "action": None, "short": "Write code",    "prompt": "Write a Python script to..."},
    "DRIVE":        {"label": "Drive",      "icon": "fas fa-hdd",           "action": None, "short": "Search files",  "prompt": "Search my local drive for files about..."},
    "CALENDAR":     {"label": "Calendar",   "icon": "fas fa-calendar",      "action": None, "short": "Schedule",      "prompt": "What's on my schedule today?"},
    "MAIL":         {"label": "Mail",       "icon": "fas fa-envelope",      "action": None, "short": "Read emails",   "prompt": "Check my recent emails"},
    "AUTOMATION":   {"label": "Automation", "icon": "fas fa-magic",         "action": None, "short": "Automate PC",   "prompt": "Automate a task on my desktop..."},
    "CONTACTS":     {"label": "Contacts",   "icon": "fas fa-address-book",  "action": None, "short": "Find contact",  "prompt": "Find contact details for..."},
    "MESSENGER":    {"label": "Messenger",  "icon": "fas fa-comments",      "action": None, "short": "Send message",  "prompt": "Send a message to..."},
    "WEBCAM":       {"label": "Camera",     "icon": "fas fa-camera",        "action": None, "short": "Take photo",    "prompt": "Take a picture with my webcam"},
    "UTILS":        {"label": "Utils",      "icon": "fas fa-tools",         "action": None, "short": "Convert",       "prompt": "Convert this format to..."},
    "FILES":        {"label": "Files",      "icon": "fas fa-folder",        "action": None, "short": "Organize",      "prompt": "Organize my downloads folder"},
    "REMINDER":     {"label": "Reminder",   "icon": "fas fa-bell",          "action": None, "short": "Set reminder",  "prompt": "Remind me to..."},
    "DOCUMENT_MAKER":{"label": "Doc Maker", "icon": "fas fa-file-word",     "action": None, "short": "Create doc",    "prompt": "Create a document about..."},
    "NOTIFICATIONS":{"label": "Alerts",     "icon": "fas fa-bell-exclamation","action": None, "short": "Notify me",   "prompt": "Set up a notification for..."},
    "BUILDER":      {"label": "Builder",    "icon": "fas fa-hammer",        "action": None, "short": "Build module",  "prompt": "Help me build a new module"},
    "USERS":        {"label": "Users",      "icon": "fas fa-users",         "action": None, "short": "User tools",    "prompt": "Show user profile tools"},
    "MODELS":       {"label": "Models",     "icon": "fas fa-server",        "action": "/models.get_current_backend", "short": "Check AI", "prompt": "Which AI model are we using?"},
    "HDCS":         {"label": "Commands",   "icon": "fas fa-terminal",      "action": "/help", "short": "Commands", "prompt": "Show me all available commands"},
    "EXECUTOR":     {"label": "Executor",   "icon": "fas fa-bolt",          "action": None, "short": "Run code",      "prompt": "Run this code snippet for me..."},
    "AGENT":        {"label": "Agent",      "icon": "fas fa-robot",         "action": None, "short": "Analyze",       "prompt": "Analyze my project and suggest improvements"},
    "PERSONALITY":  {"label": "Persona",    "icon": "fas fa-user-astronaut","action": "/souls", "short": "Persona", "prompt": "Show me available personalities"},
}


def _build_hierarchy(config: dict) -> list:
    """
    Build the DCC hierarchy for Capability Showcase:
    [
      {
        id, label, icon, color,         ← L1 category
        modules: [
          {
            id, label, icon, prompt, action ← L2 capability chip
          }
        ]
      }
    ]
    """
    from hecos.core.commands.registry import get_registry
    registry = get_registry(config=config)
    all_cmds = registry.get_all()

    safe_cmds = [
        {k: v for k, v in c.items() if not callable(v) and k != "_handler"}
        for c in all_cmds
    ]

    core_cmds = [c for c in safe_cmds if c.get("category") == "CORE" and not c["id"].startswith("zz_")]
    hpm_cmds  = [c for c in safe_cmds if c.get("category") == "HPM"]
    persona_cmds = [c for c in safe_cmds if c.get("category") in ("PERSONA", "SYSTEM")]

    seen = set()
    persona_unique = []
    for c in persona_cmds:
        if c["id"] not in seen:
            seen.add(c["id"])
            persona_unique.append(c)

    plugin_cmds = [c for c in safe_cmds if c.get("category") == "PLUGINS"]
    tag_groups: dict[str, list] = {}
    for cmd in plugin_cmds:
        tag = (cmd.get("plugin_tag") or "").upper() or "OTHER"
        if tag == "PERSONALITY":
            continue
        tag_groups.setdefault(tag, []).append(cmd)

    cat_modules: dict[str, list] = {k: [] for k in _HUB_CATS}

    def _module_from_tag(tag, cmds):
        meta = _TAG_META.get(tag, {
            "label": tag.replace("_", " ").title(),
            "icon":  "fas fa-puzzle-piece",
            "action": None,
            "short": f"Use {tag.title()}",
            "prompt": f"Use {tag.replace('_', ' ').title()} capabilities..."
        })
        
        # Determine fallback action if no prompt/action explicitly defined
        action = meta.get("action")
        if not action and not meta.get("prompt") and cmds:
            action = cmds[0].get("aliases", [f"/{cmds[0]['id']}"])[0]

        return {
            "id":     tag.lower(),
            "label":  meta["label"],
            "icon":   meta["icon"],
            "short":  meta.get("short", meta["label"]),
            "prompt": meta["prompt"],
            "action": action
        }

    for tag, cmds in tag_groups.items():
        hub_cat = _TAG_TO_HUB_CAT.get(tag, "SISTEMA")
        if hub_cat in cat_modules:
            cat_modules[hub_cat].append(_module_from_tag(tag, cmds))

    if core_cmds:
        cat_modules["SISTEMA"].insert(0, {
            "id":     "core",
            "label":  "System Core",
            "icon":   "fas fa-desktop",
            "short":  "System status",
            "prompt": "Give me a system report",
            "action": "/status"
        })

    if persona_unique:
        cat_modules["INTELLIGENZA"].insert(0, {
            "id":     "persona",
            "label":  "Persona",
            "icon":   "fas fa-user-astronaut",
            "short":  "Change Soul",
            "prompt": "Change your personality...",
            "action": "/souls"
        })

    if hpm_cmds:
        cat_modules["SISTEMA"].append({
            "id":     "hpm",
            "label":  "Packages",
            "icon":   "fas fa-box",
            "short":  "Packages",
            "prompt": "What modules do you have available?",
            "action": "/hpm"
        })

    categories = []
    all_modules = []
    for cat_key, cat_meta in sorted(_HUB_CATS.items(), key=lambda x: x[1]["order"]):
        modules = cat_modules.get(cat_key, [])
        if not modules:
            continue
        all_modules.extend(modules)
        categories.append({
            "id":      cat_meta["id"],
            "label":   cat_meta["label"],
            "icon":    cat_meta["icon"],
            "color":   cat_meta["color"],
            "order":   cat_meta["order"],
            "modules": modules,
        })

    import random
    import os
    import time
    import sqlite3
    from datetime import datetime

    core_ids = {"core", "persona", "hpm"}
    plugins = [m for m in all_modules if m["id"] not in core_ids]
    cores = [m for m in all_modules if m["id"] in core_ids]
    
    # Read DCC settings from WEB_UI config
    web_ui_cfg = config.get("plugins", {}).get("WEB_UI", {})
    new_first = web_ui_cfg.get("dcc_new_first", True)
    highlight_hours = web_ui_cfg.get("dcc_new_highlight_hours", 72)  # Default: 72h (3 days)
    highlight_secs = highlight_hours * 3600

    hecos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    now = time.time()

    # ── Build a timestamp map from ALL available sources ──────────────────────
    # Maps package_id → most_recent_install_epoch
    pkg_timestamps = {}
    # Maps package_id → module_type string
    pkg_types = {}

    # Maps package_id → {"llm_tools": N, "slash_commands": N}
    pkg_caps = {}

    # Source 1: HPM manifest files (hpm/{pkg}/hpkg_manifest.toml mtime)
    # This is the most reliable source — the manifest is written at install time
    hpm_dir = os.path.join(hecos_root, "hpm")
    if os.path.isdir(hpm_dir):
        for d in os.listdir(hpm_dir):
            manifest_path = os.path.join(hpm_dir, d, "hpkg_manifest.toml")
            if os.path.isfile(manifest_path):
                try:
                    pkg_timestamps[d] = os.path.getmtime(manifest_path)
                    
                    try:
                        import tomllib
                        with open(manifest_path, 'rb') as f:
                            data = tomllib.load(f)
                            pkg_types[d] = data.get("type", "App")
                            
                            caps = data.get("capabilities", {})
                            llm_tools = len(caps.get("llm_tools", []))
                            slash_cmds = len(caps.get("slash_commands", []))
                            pkg_caps[d] = {"llm": llm_tools, "cmd": slash_cmds}
                    except ImportError:
                        # Fallback if tomllib is missing
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip().startswith('type') and '=' in line:
                                    val = line.split('=')[1].strip().strip('\'"')
                                    pkg_types[d] = val
                                    break
                except Exception:
                    pass

    # Source 2: packages.db (installed_at / updated_at)
    db_path = os.path.join(hecos_root, "config", "data", "packages.db")
    if os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, type, installed_at, updated_at FROM packages WHERE status='installed'"
            ).fetchall()
            for row in rows:
                pid = row["id"]
                if row.get("type"):
                    pkg_types[pid] = row["type"]
                    
                ts_candidates = []
                for field in ["installed_at", "updated_at"]:
                    val = row[field]
                    if val:
                        try:
                            ts_candidates.append(datetime.fromisoformat(val).timestamp())
                        except Exception:
                            pass
                if ts_candidates:
                    best = max(ts_candidates)
                    pid = row["id"]
                    # Use DB timestamp if it's more recent than manifest
                    if pid not in pkg_timestamps or best > pkg_timestamps[pid]:
                        pkg_timestamps[pid] = best
            conn.close()
        except Exception as e:
            logger.debug(f"[DCC] Could not query packages.db: {e}")

    logger.debug(f"[DCC] Package timestamps loaded: {len(pkg_timestamps)} packages tracked")

    # ── Classify plugins as new or normal ────────────────────────────────────
    new_plugins = []
    other_plugins = []

    for p in plugins:
        pid = p["id"]
        ts = pkg_timestamps.get(pid, 0)
        age = now - ts if ts > 0 else float('inf')
        
        # Determine package type
        p_type = pkg_types.get(pid, "App")
        p["type"] = str(p_type).title()
        
        # Add capability counts
        p["caps"] = pkg_caps.get(pid, {})

        if ts > 0 and age < highlight_secs:
            p["is_new"] = True
            p["installed_ago_h"] = round(age / 3600, 1)
            p["_install_ts"] = ts  # internal, for sorting
            new_plugins.append(p)
            logger.debug(f"[DCC] NEW capability: {pid} (installed {p['installed_ago_h']}h ago)")
        else:
            p["is_new"] = False
            other_plugins.append(p)
            
    for c in cores:
        c["type"] = "System Core"

    # Sort new plugins: most recently installed first
    new_plugins.sort(key=lambda x: x.get("_install_ts", 0), reverse=True)
    # Clean up internal field before sending to frontend
    for p in new_plugins:
        p.pop("_install_ts", None)

    # Shuffle the rest for variety
    others = other_plugins + cores
    random.shuffle(others)
    
    # Build featured list: new first (if enabled), then shuffled others
    if new_first:
        featured = new_plugins + others
    else:
        all_mixed = new_plugins + others
        random.shuffle(all_mixed)
        featured = all_mixed

    # DCC display settings for the frontend
    dcc_settings = {
        "new_first": new_first,
        "highlight_hours": highlight_hours,
        "new_count": len(new_plugins),
    }

    return categories, featured, dcc_settings


def init_routes(app, root_dir: str = None):
    logger.info("[DCC] Initializing routes...")

    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/ext/dcc/static/<path:filename>")
    def dcc_static(filename):
        return send_from_directory(_static_dir, filename)

    @app.route("/api/dcc/chips", methods=["GET"])
    @login_required
    def api_dcc_chips():
        """
        Returns the DCC hierarchy: categories → modules → commands.
        Response: { ok: true, categories: [...], featured: [...] }
        """
        try:
            import sys as _sys
            config_manager = getattr(_sys, 'hecos_config_manager', None)
            config = config_manager.config if config_manager else {}

            categories, featured, dcc_settings = _build_hierarchy(config)

            return jsonify({
                "ok":         True,
                "categories": categories,
                "featured":   featured,
                "count":      sum(len(c["modules"]) for c in categories),
                "settings":   dcc_settings,
            })
        except Exception as e:
            logger.error(f"[DCC] Error building chips: {e}", exc_info=True)
            return jsonify({"ok": False, "error": str(e)}), 500
