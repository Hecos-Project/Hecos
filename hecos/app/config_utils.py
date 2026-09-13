import os
import shutil
from hecos.core.logging import logger

def ensure_files_exist(yaml_path, hecos_dir):
    """Auto-generate config files from templates if missing."""
    data_dir = os.path.dirname(yaml_path)

    files_to_check = [
        "system.yaml",
        "plugins.yaml",
        "widgets.yaml",
        "routing_overrides.yaml",
        "audio.yaml",
        "agent.yaml",
        "media.yaml",
        "keys.yaml"
    ]

    for filename in files_to_check:
        yaml_file = os.path.join(data_dir, filename)
        example_file = yaml_file + ".example"
        if not os.path.exists(yaml_file) and os.path.exists(example_file):
            try:
                shutil.copy2(example_file, yaml_file)
                logger.info(f"[CONFIG] Auto-generated {filename} from template.")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to auto-generate {filename}: {e}")

    env_file = os.path.join(hecos_dir, ".env")
    env_example = env_file + ".example"
    if not os.path.exists(env_file) and os.path.exists(env_example):
        try:
            shutil.copy2(env_example, env_file)
            logger.info("[CONFIG] Auto-generated .env from template.")
        except Exception as e:
            logger.error(f"[CONFIG] Failed to auto-generate .env: {e}")


def sanitize_widgets_yaml(widgets_path, hecos_dir):
    """Remove stale per_widget entries from widgets.yaml for widgets that are
    no longer installed. Only truly built-in widgets (telemetry_widget,
    media_player_widget, quick_links) are kept unconditionally; all others
    must correspond to a discovered extension folder in web_ui/extensions/.
    
    Returns True if modifications were made.
    """
    _BUILTIN_WIDGETS = set()

    if not os.path.exists(widgets_path):
        return False
    try:
        import yaml as _yaml

        # Discover widget IDs from the extensions directory
        extensions_dir = os.path.join(hecos_dir, "modules", "web_ui", "extensions")
        discovered_widget_ids = set()
        if os.path.isdir(extensions_dir):
            for entry in os.listdir(extensions_dir):
                manifest_path = os.path.join(extensions_dir, entry, "manifest.json")
                if os.path.isfile(manifest_path):
                    try:
                        import json as _json
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            m = _json.load(f)
                        discovered_widget_ids.add(m.get("id", entry))
                    except Exception:
                        discovered_widget_ids.add(entry)

        allowed_ids = _BUILTIN_WIDGETS | discovered_widget_ids

        with open(widgets_path, "r", encoding="utf-8") as f:
            raw = _yaml.safe_load(f) or {}

        per_widget = raw.get("widgets", {}).get("per_widget", {})
        stale = [k for k in per_widget if k not in allowed_ids]

        modified = False
        if stale:
            for k in stale:
                per_widget.pop(k)
                logger.info(f"[CONFIG] Removed stale widget entry from widgets.yaml: '{k}'")
            raw.setdefault("widgets", {})["per_widget"] = per_widget
            modified = True

        # Also clean home_layout / room_layout lists
        for layout_key in ("home_layout", "room_layout"):
            layout = raw.get("widgets", {}).get(layout_key, [])
            if isinstance(layout, list):
                cleaned = [w for w in layout if w in allowed_ids]
                if cleaned != layout:
                    raw["widgets"][layout_key] = cleaned
                    modified = True

        if modified:
            with open(widgets_path, "w", encoding="utf-8") as f:
                _yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)
            logger.info("[CONFIG] widgets.yaml sanitized — stale widget entries removed.")
            return True
            
    except Exception as e:
        logger.warning(f"[CONFIG] Could not sanitize widgets.yaml: {e}")
        
    return False


def sync_available_personalities(config_dict, project_root, set_callback, save_callback):
    """
    Scans the 'personas' folder for directories containing persona.yaml and updates
    'ai.available_personalities' if the list has changed.
    Returns the current list of personality names.
    """
    import os
    folder = os.path.join(project_root, "hecos", "personas")
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except Exception:
            pass

    files = sorted([d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))])

    if files:
        primary = "Hecos_System_Soul"
        if primary in files:
            files.remove(primary)
            files.insert(0, primary)

        personality_dict = {str(i + 1): name for i, name in enumerate(files)}
        current_dict = config_dict.get("ai", {}).get("available_personalities", {})
        current_dict_str = {str(k): v for k, v in current_dict.items()} if isinstance(current_dict, dict) else {}

        active = config_dict.get("ai", {}).get("active_personality")
        files_lower = [f.lower() for f in files]
        needs_revert = active and active.lower() not in files_lower

        if needs_revert:
            logger.warning(f"[CONFIG] Active personality '{active}' not found. Reverting to {primary}.")
            set_callback(primary, "ai", "active_personality")

        if personality_dict != current_dict_str or needs_revert:
            set_callback(personality_dict, "ai", "available_personalities")
            save_callback()
            logger.info("[CONFIG] Personality list synchronized with filesystem.")

    return files
