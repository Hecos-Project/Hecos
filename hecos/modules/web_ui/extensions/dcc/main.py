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

    # SISTEMA
    "AUTOMATION":   "SISTEMA",
    "UTILS":        "SISTEMA",
    "SYSTEM":       "SISTEMA",
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

    core_ids = {"core", "persona", "hpm"}
    plugins = [m for m in all_modules if m["id"] not in core_ids]
    cores = [m for m in all_modules if m["id"] in core_ids]
    
    # Determine which plugins are newly installed (last 3 days)
    hecos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    modules_dir = os.path.join(hecos_root, "modules")
    now = time.time()

    new_plugins = []
    other_plugins = []

    for p in plugins:
        folder = os.path.join(modules_dir, p["id"])
        ctime = os.path.getctime(folder) if os.path.exists(folder) else 0
        if ctime > 0 and (now - ctime) < 3 * 24 * 3600:
            p["is_new"] = True
            new_plugins.append(p)
        else:
            p["is_new"] = False
            other_plugins.append(p)

    # Sort new plugins so the absolute newest is first
    new_plugins.sort(key=lambda x: os.path.getctime(os.path.join(modules_dir, x["id"])), reverse=True)

    # Shuffle the rest for variety
    others = other_plugins + cores
    random.shuffle(others)
    
    # Combine: Newest plugins always first, filled by shuffled others (no limit — carousel handles scrolling)
    featured = new_plugins + others

    return categories, featured


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

            categories, featured = _build_hierarchy(config)

            return jsonify({
                "ok":         True,
                "categories": categories,
                "featured":   featured,
                "count":      sum(len(c["modules"]) for c in categories),
            })
        except Exception as e:
            logger.error(f"[DCC] Error building chips: {e}", exc_info=True)
            return jsonify({"ok": False, "error": str(e)}), 500
