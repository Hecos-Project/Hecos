"""
MODULE: Brain - Dispatcher - Hecos v0.6
DESCRIPTION: Coordinates prompt construction and invokes the chosen backend.
"""

import json
import os
from hecos.core.logging import logger
from hecos.core.llm import client
from hecos.core.i18n import translator
from hecos.core.llm.manager import manager
from hecos.core.system.module_loader import get_tools_schema

# --- NEW REFACTORED MANAGERS ---
from hecos.core.llm.prompt_builder import PromptBuilder
from hecos.core.llm.history_manager import HistoryManager

# Anchor to hecos/ folder for config path
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(_HECOS_DIR, "config", "data", "system.yaml")

def load_config():
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"BRAIN: {translator.t('error')}: {e}")
        logger.debug("BRAIN", f"Error loading config: {e}")
        return None

def generate_response(user_text, external_config=None, tag=None, images=None, agent_context=None, save_history=True, user_id="admin", session_id=None, sender_tab_id=None):
    logger.debug("BRAIN", f"=== START generate_response ===")
    logger.debug("BRAIN", f"User text: '{user_text}'")
    
    # 1. Config loading
    if external_config:
        config = external_config
        logger.debug("BRAIN", "Using external_config")
    else:
        config = load_config()
        logger.debug("BRAIN", "Using file config")
        
    if not config:
        logger.error("BRAIN: Config not found!")
        return translator.t("error")
    
    # 2. Model resolution
    from app.model_manager import ModelManager
    effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(config)
    
    backend_config = config.get('backend', {}).get(effective_backend_type, {}).copy() # Copy to not pollute global config
    modello_risolto = manager.resolve_model(tag, config_override=config)
    
    if modello_risolto:
        backend_config['model'] = modello_risolto
        logger.debug("BRAIN", f"Model resolved for tag '{tag}': {modello_risolto}")
        is_cloud = any(modello_risolto.startswith(p + "/") for p in ["groq", "openai", "anthropic", "gemini", "cohere"])
        backend_config['backend_type'] = "cloud" if is_cloud else effective_backend_type
    else:
        backend_config['model'] = effective_default_model
        backend_config['backend_type'] = effective_backend_type
        
    if 'model' not in backend_config or not backend_config['model'] or backend_config['model'] == 'N/D':
        logger.error(f"[CRITICAL] Model not specified in config.json for backend {effective_backend_type}!")
        return f"{translator.t('error')}: {translator.t('model_config_missing')}"

    # 3. Prompt Building
    system_prompt = PromptBuilder.build_system_prompt(user_text, images, config, user_id, session_id, backend_config)
    
    # 4. LiteLLM Invocation
    logger.debug("BRAIN", f"LiteLLM call ({backend_config['backend_type']}) with model: {backend_config['model']}")
    tools = get_tools_schema()
    
    response = client.generate(
        system_prompt, 
        user_text, 
        backend_config, 
        config.get('llm', {}), 
        tools=tools, 
        images=images, 
        extra_messages=agent_context
    )
    
    # 5. History Persistence
    personality_name = config.get('ai', {}).get('active_personality', 'Hecos_System_Soul').replace('.yaml', '')
    HistoryManager.save_interaction(
        user_text, response, save_history, config, user_id, session_id, sender_tab_id, personality_name, backend_config
    )
    
    logger.debug("BRAIN", f"=== END generate_response ===")
    return response