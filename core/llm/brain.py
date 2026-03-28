"""
MODULE: Brain - Dispatcher - Zentra Core v0.6
DESCRIPTION: Coordinates prompt construction and invokes the chosen backend.
"""

import json
import os
from core.logging import logger
from memory import brain_interface
from core.llm import client
from core.i18n import translator
from core.llm.manager import manager
from core.system.plugin_loader import get_tools_schema, get_legacy_schema

CONFIG_PATH = "config.json"
REGISTRY_PATH = "core/registry.json"

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"BRAIN: {translator.t('error')}: {e}")
        logger.debug("BRAIN", f"Error loading config: {e}")
        return None

def load_capabilities():
    if not os.path.exists(REGISTRY_PATH):
        logger.error("BRAIN: Registry not found.")
        logger.debug("BRAIN", f"Registry not found in {REGISTRY_PATH}")
        return translator.t("no_active_protocols")
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            prompt_skills = f"\n{translator.t('active_protocols_db')}\n"
            for tag, info in db.items():
                module_label = translator.t("module")
                commands_label = translator.t("commands")
                prompt_skills += f"- {module_label} {tag}: {info['description']}. {commands_label}: {list(info['commands'].keys())}\n"
            logger.debug("BRAIN", f"Capabilities loaded: {len(db)} modules")
            return prompt_skills
    except Exception as e:
        logger.error(f"BRAIN: Skills reading error: {e}")
        logger.debug("BRAIN", f"Capability reading error: {e}")
        return ""

def generate_self_awareness(personality_name):
    try:
        souls = [f for f in os.listdir("personality") if f.endswith('.txt')]
        core_modules = [f for f in os.listdir("core") if f.endswith('.py')]
        plugin_modules = [f for f in os.listdir("plugins") if f.endswith('.py')]
        
        awareness = f"\n{translator.t('structural_self_awareness')}\n"
        awareness += f"{translator.t('awareness_desc')}\n"
        awareness += f"- {translator.t('current_soul', name=personality_name)}\n"
        other_souls = ', '.join([a for a in souls if a != personality_name])
        awareness += f"- {translator.t('dormant_souls', souls=other_souls)}\n"
        awareness += f"- {translator.t('central_nervous_system', modules=', '.join(core_modules))}\n"
        awareness += f"- {translator.t('action_modules', modules=', '.join(plugin_modules))}\n"
        awareness += f"{translator.t('admin_structure_hint')}\n"
        
        logger.debug("BRAIN", f"Self-awareness generated: {len(awareness)} characters")
        return awareness
    except Exception as e:
        logger.error(f"BRAIN: Self-awareness perception error: {e}")
        logger.debug("BRAIN", f"Self-awareness error: {e}")
        return ""

def generate_response(user_text, external_config=None, tag=None):
    logger.debug("BRAIN", f"=== START generate_response ===")
    logger.debug("BRAIN", f"User text: '{user_text}'")
    logger.debug("BRAIN", f"external_config provided: {external_config is not None}")
    
    # If processor provides updated config, use it; otherwise, load from file
    if external_config:
        config = external_config
        logger.debug("BRAIN", "Using external_config")
    else:
        config = load_config()
        logger.debug("BRAIN", "Using file config")
        
    if not config:
        logger.error("BRAIN: Config not found!")
        logger.debug("BRAIN", "ERROR: missing config")
        return translator.t("error")
    
    logger.debug("BRAIN", f"Config loaded. Backend type: {config.get('backend', {}).get('type', 'unspecified')}")

    # 1. Retrieve personality
    personality_name = config.get('ai', {}).get('active_personality', 'zentra.txt')
    if not personality_name:
        personality_name = "zentra.txt"
    logger.debug("BRAIN", f"Active personality: {personality_name}")
    
    personality_path = os.path.join("personality", personality_name)
    personality_prompt = "You are Zentra, an advanced AI."
    if os.path.exists(personality_path):
        try:
            with open(personality_path, "r", encoding="utf-8") as f:
                personality_prompt = f.read()
            logger.debug("BRAIN", f"Personality loaded: {len(personality_prompt)} characters")
        except Exception as e:
            logger.error(f"BRAIN: Personality reading error: {e}")
            logger.debug("BRAIN", f"Personality reading error: {e}")

    # 2. Memory and self-awareness (respecting cognition config)
    cog = config.get('cognition', {})
    logger.debug("BRAIN", "Memory loading...")
    memory_context = brain_interface.get_context(config) if cog.get('include_identity_context', True) else ""
    logger.debug("BRAIN", f"Memory: {len(memory_context)} characters")
    
    logger.debug("BRAIN", "Self-awareness generation...")
    self_awareness = generate_self_awareness(personality_name) if cog.get('include_self_awareness', True) else ""
    logger.debug("BRAIN", f"Self-awareness: {len(self_awareness)} characters")
    
    # Build episodic history block (conversation context)
    history_block = ""
    if cog.get('memory_enabled', True) and cog.get('episodic_memory', True):
        max_h = int(cog.get('max_history_messages', 20))
        history_rows = brain_interface.get_history(limit=max_h, config=config)
        if history_rows:
            history_block = "\n[RECENT CONVERSATION HISTORY]\n"
            for role, msg in history_rows:
                label = "User" if role == "user" else "Zentra"
                history_block += f"{label}: {msg}\n"
        logger.debug("BRAIN", f"History injected: {len(history_rows)} messages")
    
    logger.debug("BRAIN", "Capabilities loading...")
    capabilities = load_capabilities()
    logger.debug("BRAIN", f"Capabilities: {len(capabilities)} characters")

    # 3. Rules and guidelines
    identity_rules = (
        f"{translator.t('identity_protocol')}\n"
        f"- {translator.t('rule_who_am_i')}\n"
    )
    file_manager_rules = (
        f"{translator.t('file_management_rules')}\n"
        f"- {translator.t('rule_list_files')}\n"
        f"- {translator.t('rule_read_file')}\n"
    )
    force_clause = (
        f"\n{translator.t('root_security_instruction')}\n"
        f"{translator.t('root_security_desc')}\n"
    )
    plugin_guidelines = (
        "\n### PLUGIN GUIDELINES ###\n"
        "- [SYSTEM: time] for the current time\n"
        "- [SYSTEM: open:notepad] to open programs\n"
        "- [SYSTEM: terminal] to open the command prompt\n"
        "- [SYSTEM: cmd:instruction] to execute shell commands\n"
        "- [FILE_MANAGER: list:desktop] to list files on the desktop\n"
        "- [FILE_MANAGER: read:document] to read a file\n"
        "- [DASHBOARD: resources] for CPU/RAM\n"
        "- [MEMORY: remember:text] to remember\n"
        "- [MEMORY: read:n] for history\n"
    )

    special_instructions = config.get('ai', {}).get('special_instructions', '').strip()
    special_instructions_block = f"\n### SPECIAL INSTRUCTIONS ###\n{special_instructions}\n" if special_instructions else ""
    
    # --- ROUTING ENGINE (DUAL ENGINE) ---
    routing_cfg = config.get('routing_engine', {})
    mode = routing_cfg.get('mode', 'auto')
    legacy_models_str = routing_cfg.get('legacy_models', '')
    
    # Temporary model resolution (to understand what we're about to use)
    from app.model_manager import ModelManager
    effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(config)
    modello_risolto_temp = manager.resolve_model(tag, config_override=config)
    current_model = (modello_risolto_temp or effective_default_model).lower()

    is_legacy = False
    if mode == 'forza_legacy':
        is_legacy = True
    elif mode == 'auto':
        legacy_list = [m.strip().lower() for m in legacy_models_str.split(',') if m.strip()]
        if any(legacy_m in current_model for legacy_m in legacy_list):
            is_legacy = True
            
    if is_legacy:
        logger.debug("BRAIN", f"Routing: DUAL ENGINE -> LEGACY MODE (Tag Engine) for {current_model}")
        tag_instructions = (
            f"\n{translator.t('tag_instructions_title')}\n"
            f"{translator.t('tag_instructions_desc')}\n"
            f"{get_legacy_schema()}\n"
        )
        tools = None
    else:
        logger.debug("BRAIN", f"Routing: DUAL ENGINE -> NATIVE MODE (JSON Calling) for {current_model}")
        tag_instructions = ""  # No manual tags needed for Native tools
        tools = get_tools_schema()

    system_prompt = (
        f"{personality_prompt}\n"
        f"{memory_context}\n"
        f"{history_block}\n"
        f"{self_awareness}\n"
        f"{capabilities}\n"
        "### OPERATIVE RULES ###\n"
        "1. Be consistent with your personality.\n\n"
        f"{identity_rules}"
        f"{file_manager_rules}"
        f"{force_clause}"
        f"{plugin_guidelines}"
        f"{tag_instructions}"
        f"{special_instructions_block}"
    )
    
    logger.debug("BRAIN", f"System prompt created: {len(system_prompt)} characters")
    
    # Check if roleplay plugin is active
    try:
        from plugins.roleplay.main import get_roleplay_prompt
        rp_prompt = get_roleplay_prompt()
        if rp_prompt:
            # Replaces system prompt with roleplay prompt
            system_prompt = rp_prompt
            tag = "ROLEPLAY" # Set tag for model dispatching
            logger.debug("BRAIN", "Roleplay mode active - prompt replaced and tag set")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Roleplay plugin error: {e}")

    # 4. Model resolution and Invocation of the unified LiteLLM client
    from app.model_manager import ModelManager
    effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(config)
    
    backend_config = config.get('backend', {}).get(effective_backend_type, {}).copy() # Copy to not pollute global config
    
    # Dynamic model resolution via LLMManager
    modello_risolto = manager.resolve_model(tag, config_override=config)
    if modello_risolto:
        backend_config['model'] = modello_risolto
        logger.debug("BRAIN", f"Model resolved for tag '{tag}': {modello_risolto}")
        
        # If resolved model (e.g. from plugin) is cloud, ensure client.py knows to send to provider
        is_cloud = any(modello_risolto.startswith(p + "/") for p in ["groq", "openai", "anthropic", "gemini", "cohere"])
        backend_config['backend_type'] = "cloud" if is_cloud else effective_backend_type
    else:
        # Ultra-safe fallback
        backend_config['model'] = effective_default_model
        backend_config['backend_type'] = effective_backend_type
        
    logger.debug("BRAIN", f"Backend chosen: {backend_config['backend_type']}")

    if 'model' not in backend_config or not backend_config['model'] or backend_config['model'] == 'N/D':
        logger.error(f"[CRITICAL] Model not specified in config.json for backend {effective_backend_type}!")
        logger.debug("BRAIN", f"ERROR: Missing model for backend {effective_backend_type}")
        return f"{translator.t('error')}: {translator.t('model_config_missing')}"

    logger.debug("BRAIN", f"LiteLLM call ({backend_config['backend_type']}) with model: {backend_config['model']}")
    
    # Single call to the unified client
    response = client.generate(system_prompt, user_text, backend_config, config.get('llm', {}), tools=tools)
    
    # 5. Save to memory (respecting cognition config)
    logger.debug("BRAIN", "Saving to memory...")
    brain_interface.save_message("user", user_text, config=config)
    
    # Structured response management (String or Message with tool_calls)
    if isinstance(response, str):
        logger.debug("BRAIN", f"Response received from backend: {len(response)} characters")
        brain_interface.save_message("assistant", response, config=config)
    else:
        # It's a Message object (used a tool)
        logger.debug("BRAIN", "Response is a tool call object.")
        tool_names = [call.function.name for call in getattr(response, 'tool_calls', [])]
        brain_interface.save_message("assistant", f"*(Tool call: {', '.join(tool_names)})*", config=config)
    
    logger.debug("BRAIN", f"=== END generate_response ===")
    return response