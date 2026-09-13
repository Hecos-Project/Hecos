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


def update_config_logic(current_config, new_data):
    import copy
    temp_config = copy.deepcopy(current_config)
    deep_update(temp_config, new_data)
    
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
    for k, v in patch.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            deep_update(base[k], v)
        else:
            base[k] = v
