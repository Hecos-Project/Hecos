import os
import time
from hecos.core.logging import logger

def load_config_models(yaml_path, plugins_path, widgets_path):
    from hecos.config.yaml_utils import load_yaml
    from hecos.config.schemas.system_schema import SystemConfig
    from hecos.config.schemas.plugins_schema import PluginsFileConfig
    from hecos.config.schemas.widgets_schema import WidgetsFileConfig

    # --- L0: system.yaml ---
    try:
        system_model = load_yaml(yaml_path, SystemConfig)
    except Exception as e:
        logger.error(f"[CONFIG] Failed to load system.yaml: {e}. Using defaults.")
        system_model = SystemConfig()

    # --- L1: plugins.yaml ---
    try:
        plugins_model = load_yaml(plugins_path, PluginsFileConfig)
    except Exception as e:
        logger.error(f"[CONFIG] Failed to load plugins.yaml: {e}. Using defaults.")
        plugins_model = PluginsFileConfig()

    # --- L2: widgets.yaml ---
    try:
        widgets_model = load_yaml(widgets_path, WidgetsFileConfig)
    except Exception as e:
        logger.error(f"[CONFIG] Failed to load widgets.yaml: {e}. Using defaults.")
        widgets_model = WidgetsFileConfig()
        
    return system_model, plugins_model, widgets_model


def save_config(yaml_path, plugins_path, widgets_path, config_dict, project_root):
    # write app flag
    try:
        flag_path = os.path.join(project_root, ".config_saved_by_app")
        with open(flag_path, "w") as f:
            f.write("1")
        time.sleep(0.05)
    except Exception:
        pass

    from hecos.config.schemas.system_schema import SystemConfig
    from hecos.config.schemas.plugins_schema import PluginsFileConfig
    from hecos.config.schemas.widgets_schema import WidgetsFileConfig
    
    system_dict  = {k: v for k, v in config_dict.items()
                    if k not in ("plugins", "extensions", "widgets")}
    plugins_dict = {
        "plugins":    config_dict.get("plugins", {}),
        "extensions": config_dict.get("extensions", {}),
    }
    widgets_dict = {
        "widgets": config_dict.get("widgets", {}),
    }

    try:
        system_model  = SystemConfig.model_validate(system_dict)
    except Exception as e:
        logger.error(f"[CONFIG] system.yaml validation failed: {e}")
        return False, None, None, None

    try:
        plugins_model = PluginsFileConfig.model_validate(plugins_dict)
    except Exception as e:
        logger.error(f"[CONFIG] plugins.yaml validation failed: {e}")
        return False, None, None, None

    try:
        widgets_model = WidgetsFileConfig.model_validate(widgets_dict)
    except Exception as e:
        logger.error(f"[CONFIG] widgets.yaml validation failed: {e}")
        return False, None, None, None

    from hecos.config.yaml_utils import save_yaml, save_dict_to_yaml

    system_save_dict = system_model.model_dump()
    system_save_dict.pop("agent", None)
    # CRITICAL SECURITY: Never write tokens into system.yaml (which is tracked by git)
    if "hpm" in system_save_dict and isinstance(system_save_dict["hpm"], dict):
        system_save_dict["hpm"].pop("github_token", None)
    save_dict_to_yaml(yaml_path, system_save_dict)

    save_yaml(plugins_path, plugins_model)
    save_yaml(widgets_path, widgets_model)

    new_lang = system_model.language
    if new_lang:
        try:
            from hecos.core.i18n import translator
            t_inst = translator.get_translator()
            if t_inst.language != new_lang:
                t_inst.set_language(new_lang)
                logger.info(f"[CONFIG] Language runtime updated to: {new_lang}")
        except Exception:
            pass

    logger.info("[CONFIG] Configuration saved successfully.")
    return True, system_model, plugins_model, widgets_model


_ATOMIC_DICT_KEYS = {"available_models", "available_personalities", "custom_replacements"}


def update_config_logic(current_config, new_data):
    import copy
    temp_config = copy.deepcopy(current_config)
    preserve_avail = not (isinstance(new_data, dict) and new_data.pop("_update_available_models", False))
    saved_ollama_avail = copy.deepcopy(current_config.get("backend", {}).get("ollama", {}).get("available_models"))
    saved_kobold_avail = copy.deepcopy(current_config.get("backend", {}).get("kobold", {}).get("available_models"))
    # Control Room pages are managed exclusively via /api/widgets/room/pages* endpoints;
    # prevent stale Central Hub window.cfg snapshots from overwriting them on unrelated saves.
    saved_room_pages = copy.deepcopy(current_config.get("widgets", {}).get("room_pages"))

    if isinstance(new_data, dict) and "hpm" in new_data and isinstance(new_data["hpm"], dict):
        new_data["hpm"].pop("github_token", None)
    deep_update(temp_config, new_data)

    if saved_room_pages is not None and isinstance(temp_config.get("widgets"), dict):
        temp_config["widgets"]["room_pages"] = saved_room_pages

    if preserve_avail:
        if saved_ollama_avail is not None and isinstance(temp_config.get("backend", {}).get("ollama"), dict):
            temp_config["backend"]["ollama"]["available_models"] = saved_ollama_avail
        if saved_kobold_avail is not None and isinstance(temp_config.get("backend", {}).get("kobold"), dict):
            temp_config["backend"]["kobold"]["available_models"] = saved_kobold_avail

    if "hpm" in temp_config and isinstance(temp_config["hpm"], dict):
        temp_config["hpm"]["github_token"] = ""
    
    from hecos.config.schemas.system_schema import SystemConfig
    from hecos.config.schemas.plugins_schema import PluginsFileConfig
    from hecos.config.schemas.widgets_schema import WidgetsFileConfig

    system_dict = {k: v for k, v in temp_config.items() if k not in ("plugins", "extensions", "widgets")}
    plugins_dict = {
        "plugins":    temp_config.get("plugins", {}),
        "extensions": temp_config.get("extensions", {}),
    }
    widgets_dict = {"widgets": temp_config.get("widgets", {})}

    new_system  = SystemConfig.model_validate(system_dict)
    new_plugins = PluginsFileConfig.model_validate(plugins_dict)
    new_widgets = WidgetsFileConfig.model_validate(widgets_dict)

    if hasattr(new_system, 'ai') and 'ai' in new_data and 'active_personality' in new_data['ai']:
        new_system.ai.active_personality = new_data['ai']['active_personality']

    return temp_config, new_system, new_plugins, new_widgets

def deep_update(base: dict, patch: dict):
    import copy
    for k, v in patch.items():
        if k in _ATOMIC_DICT_KEYS and isinstance(v, dict):
            base[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and k in base and isinstance(base[k], dict):
            deep_update(base[k], v)
        else:
            base[k] = v
