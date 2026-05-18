"""
MODULE: Brain - Dispatcher - Hecos v0.6
DESCRIPTION: Coordinates prompt construction and invokes the chosen backend.
"""

import json
import os
from hecos.core.logging import logger
from hecos.memory import brain_interface
from hecos.core.llm import client
from hecos.core.i18n import translator
from hecos.core.llm.manager import manager
from hecos.core.system.module_loader import get_tools_schema, get_legacy_schema, get_active_tags
from hecos.config import load_yaml
from hecos.config.schemas.routing_schema import RoutingOverrides

# --- NEW IMPORTS FOR FASE 6 ---
import re
import base64
from hecos.core.auth.auth_manager import auth_mgr
from hecos.memory.user_vault_manager import get_vault_path

# --- PROJECT ROOT CALCULATION ---
# Anchored to hecos/ folder
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(_HECOS_DIR, "config", "data", "system.yaml")
REGISTRY_PATH = os.path.join(_HECOS_DIR, "core", "registry.json")
PERSONALITY_DIR = os.path.join(_HECOS_DIR, "personality")
CORE_DIR = os.path.join(_HECOS_DIR, "core")
ROUTING_OVERRIDES_PATH = os.path.join(_HECOS_DIR, "config", "data", "routing_overrides.yaml")

class RoutingManager:
    """
    Manages the 3-tier hybrid routing system:
    1. Plugin Manifest (Default)
    2. User Overrides (YAML)
    3. Core Defaults (Fallback)
    """
    @staticmethod
    def get_dynamic_instructions(config):
        try:
            # 1. Load active plugin tags
            active_tags = get_active_tags()
            
            # 2. Load instructions from registry
            registry_data = {}
            if os.path.exists(REGISTRY_PATH):
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    registry_data = json.load(f)
            
            # 3. Load user overrides
            overrides = {}
            if os.path.exists(ROUTING_OVERRIDES_PATH):
                try:
                    overrides_model = load_yaml(ROUTING_OVERRIDES_PATH, RoutingOverrides)
                    overrides = overrides_model.overrides
                except Exception as e:
                    logger.debug(f"BRAIN: Error loading routing overrides: {e}")

            # 4. Merge logic
            merged_instructions = []
            for tag in active_tags:
                tag_upper = tag.upper()
                # Priority: YAML Override > Registry (Manifest)
                instruction = overrides.get(tag_upper)
                
                if not instruction and tag_upper in registry_data:
                    instruction = registry_data[tag_upper].get("routing_instructions")
                
                if instruction:
                    merged_instructions.append(f"- [{tag_upper}] {instruction}")

            if merged_instructions:
                block = "\n### DYNAMIC ROUTING RULES ###\n"
                block += "These rules define how to choose targets or modes for specific tools. FOLLOW THEM STRICTLY.\n"
                block += "\n".join(merged_instructions) + "\n"
                return block
            return ""
        except Exception as e:
            logger.error(f"BRAIN: Routing Manager error: {e}")
            return ""

def load_config():
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
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
        from hecos.core.system.module_loader import get_active_tags
        active_plugins = get_active_tags()
        
        # Simplified listing to save tokens
        souls_count = len([f for f in os.listdir(PERSONALITY_DIR) if f.endswith('.yaml')])
        core_count  = len([f for f in os.listdir(CORE_DIR) if f.endswith('.py')])
        
        awareness = f"\n{translator.t('structural_self_awareness')}\n"
        awareness += f"{translator.t('awareness_desc')}\n"
        awareness += f"- {translator.t('current_soul', name=personality_name)}\n"
        awareness += f"- Total personality modules available: {souls_count}\n"
        awareness += f"- Active Action Modules: {', '.join(active_plugins) if active_plugins else 'none'}\n"
        awareness += f"- Core Subsystems: {core_count} integrated modules\n"
        awareness += f"{translator.t('admin_structure_hint')}\n"
        
        logger.debug("BRAIN", f"Self-awareness generated for {len(active_plugins)} active plugins")
        return awareness
    except Exception as e:
        logger.error(f"BRAIN: Self-awareness perception error: {e}")
        logger.debug("BRAIN", f"Self-awareness error: {e}")
        return ""

def generate_response(user_text, external_config=None, tag=None, images=None, agent_context=None, save_history=True, user_id="admin", session_id=None):
    logger.debug("BRAIN", f"=== START generate_response ===")
    logger.debug("BRAIN", f"User text: '{user_text}'")
    logger.debug("BRAIN", f"external_config provided: {external_config is not None}")
    
    # --------------------------------------------------
    
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

    # --- FASE 6: AI Vision - Avatar Auto-Injection (User & AI) ---
    if user_text and isinstance(user_text, str):
        # 1. USER IDENTITY TRIGGER
        user_id_keywords = r'\b(who am i|what do i look like|my face|my photo|my picture|my avatar|chi sono|come sono|il mio viso|la mia foto|il mio aspetto|la mia immagine)\b'
        if re.search(user_id_keywords, user_text, re.IGNORECASE):
            profile = auth_mgr.get_profile(user_id)
            if profile and profile.get("avatar_path"):
                vault = get_vault_path(user_id)
                avatar_file = os.path.join(vault, "avatar.jpg")
                if os.path.exists(avatar_file):
                    try:
                        with open(avatar_file, "rb") as af:
                            b64_avatar = base64.b64encode(af.read()).decode("utf-8")
                        if images is None: images = []
                        images.append({"data_b64": b64_avatar, "mime_type": "image/jpeg", "name": f"user_avatar_{user_id}.jpg"})
                        logger.info(f"[BRAIN] Injected user avatar for Vision AI.")
                    except Exception as e:
                        logger.error(f"[BRAIN] Failed to inject user avatar: {e}")

        # 2. AI SELF-PERCEPTION TRIGGER
        ai_id_keywords = r'\b(how do you look|describe yourself|describe your face|your photo|your picture|your avatar|che aspetto hai|descriviti|il tuo volto|la tua foto|come sei fatt[oa])\b'
        if re.search(ai_id_keywords, user_text, re.IGNORECASE):
            personality_name = config.get('ai', {}).get('active_personality', 'Hecos_System_Soul.yaml').replace(".yaml", "")
            persona_avatar_dir = os.path.join(_HECOS_DIR, "assets", "avatars", personality_name)
            if os.path.exists(persona_avatar_dir):
                try:
                    # Find first image in the persona folder
                    for f in os.listdir(persona_avatar_dir):
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            av_path = os.path.join(persona_avatar_dir, f)
                            with open(av_path, "rb") as af:
                                b64_av = base64.b64encode(af.read()).decode("utf-8")
                            if images is None: images = []
                            import mimetypes
                            mime, _ = mimetypes.guess_type(av_path)
                            images.append({"data_b64": b64_av, "mime_type": mime or "image/png", "name": f"ai_avatar_{personality_name}{os.path.splitext(f)[1]}"})
                            logger.info(f"[BRAIN] Injected AI persona avatar ({personality_name}) for self-perception.")
                            
                            # Reinforce consistency for image generation
                            if "foto" in user_text.lower() or "photo" in user_text.lower() or "immagine" in user_text.lower():
                                user_text += "\n\n(Note: I have attached my own persona avatar to this request. I will analyze my visual features from this image to inspire any image generation prompt if the user is asking for a picture of me, ensuring visual consistency.)"
                            break
                except Exception as e:
                    logger.error(f"[BRAIN] Failed to inject AI avatar: {e}")
    # --------------------------------------------------
    # 1. Retrieve personality
    personality_name = config.get('ai', {}).get('active_personality', 'Hecos_System_Soul.yaml')
    if not personality_name:
        personality_name = "Hecos_System_Soul.yaml"
    logger.debug("BRAIN", f"Active personality: {personality_name}")
    
    personality_path = os.path.join(PERSONALITY_DIR, personality_name)
    personality_prompt = "You are Hecos, an advanced AI."
    visual_identity_block = ""
    
    # --- ROBUST FALLBACK CHECK ---
    if not os.path.exists(personality_path):
        logger.warning(f"BRAIN: Active personality '{personality_name}' missing! Falling back to 'Hecos_System_Soul.yaml'.")
        personality_name = "Hecos_System_Soul.yaml"
        personality_path = os.path.join(PERSONALITY_DIR, personality_name)

    if os.path.exists(personality_path):
        try:
            import yaml as pyyaml
            with open(personality_path, "r", encoding="utf-8") as f:
                persona_data = pyyaml.safe_load(f)
                personality_prompt = persona_data.get("system_prompt", "You are Hecos, an advanced AI.")
                
                # --- NEW: Visual Identity awareness ---
                v_desc = persona_data.get("visual_description")
                if v_desc:
                    visual_identity_block = (
                        "\n### YOUR PHYSICAL ASPECT / VISUAL IDENTITY ###\n"
                        f"When asked to describe yourself or when you generate an image of yourself, always use these visual traits: {v_desc}. "
                        "If you call the image generation tool to produce a photo of you, use this detailed description as the base for the prompt.\n"
                    )
            logger.debug("BRAIN", f"Personality loaded: {len(personality_prompt)} characters (Visual awareness: {bool(v_desc)})")
        except Exception as e:
            logger.error(f"BRAIN: Personality reading error: {e}")
            logger.debug("BRAIN", f"Personality reading error: {e}")

    # 2. Memory and self-awareness (respecting cognition config)
    cog = config.get('cognition', {})
    logger.debug("BRAIN", "Memory loading...")
    
    # Calculate clean name for identity context
    clean_name = personality_name.replace(".yaml", "").replace("_", " ") if personality_name else "Hecos"
    
    memory_context = brain_interface.get_context(config, dynamic_name=clean_name, user_id=user_id) if cog.get('include_identity_context', True) else ""
    logger.debug("BRAIN", f"Memory: {len(memory_context)} characters")
    
    logger.debug("BRAIN", "Self-awareness generation...")
    self_awareness = generate_self_awareness(personality_name) if cog.get('include_self_awareness', True) else ""
    logger.debug("BRAIN", f"Self-awareness: {len(self_awareness)} characters")
    
    # Build episodic history block (conversation context)
    history_block = ""
    if cog.get('memory_enabled', True) and cog.get('episodic_memory', True):
        max_h = int(cog.get('max_history_messages', 20))
        history_rows = brain_interface.get_history(limit=max_h, config=config, user_id=user_id)
        if history_rows:
            history_block = "\n[RECENT CONVERSATION HISTORY]\n"
            for role, msg in history_rows:
                label = "User" if role == "user" else clean_name
                history_block += f"{label}: {msg}\n"
        logger.debug("BRAIN", f"History injected: {len(history_rows)} messages")
    
    logger.debug("BRAIN", "Capabilities loading...")
    capabilities = load_capabilities()
    logger.debug("BRAIN", f"Capabilities: {len(capabilities)} characters")

    # 3. Rules and guidelines
    identity_rules = (
        f"{translator.t('identity_protocol')}\n"
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
    # Concisely inject folder mappings to guide the AI without using absolute paths in guidelines
    desktop_map = external_config.get("plugins", {}).get("FILE_MANAGER", {}).get("mappings", {}).get("desktop", "desktop") if external_config else "desktop"



    plugin_guidelines = (
        "\n### PLUGIN GUIDELINES ###\n"
        "- PRIORITY: Always respond with TEXT first. Only use a tool if the user explicitly asks for an action.\n"
        "- [SYSTEM: time] - Get current local time\n"
        "- [SYSTEM: open:prog_name] - Open notepad, chrome, etc.\n"
        "- [SYSTEM: terminal] - Open Windows CMD prompt window\n"
        "- [SYSTEM: explore:folder] - Open folder graphically\n"
        "- [FILE_MANAGER: list:folder] - List files for analysis\n"
        "- [DASHBOARD: resources] - Get hardware telemetry\n"
    )



    special_instructions = config.get('ai', {}).get('special_instructions', '').strip()
    special_instructions_block = f"\n### SPECIAL INSTRUCTIONS ###\n{special_instructions}\n" if special_instructions else ""

    safety_instructions = config.get('ai', {}).get('safety_instructions', '').strip()
    enable_safety = config.get('ai', {}).get('enable_safety_instructions', True)
    safety_instructions_block = f"\n### SAFETY & CONTEXT DISCLAIMER ###\n{safety_instructions}\n" if safety_instructions and enable_safety else ""

    # --- USER IDENTITY CONTEXT (OPTIMIZED) ---
    # Identity details to ensure personalization. Detailed contact info
    # is moved to the USER:get_profile tool to save tokens (Lazy Load).
    user_profile_block = ""
    try:
        profile = auth_mgr.get_profile(user_id)
        if profile:
            user_profile_block = (
                "\n### USER IDENTITY ###\n"
                f"  - Username: {profile.get('username', user_id)}\n"
                f"  - Display Name: {profile.get('display_name') or '[not provided]'}\n"
                f"  - Preferred Language: {profile.get('preferred_language', 'it')}\n"
                f"  - Role: {profile.get('role', 'admin')}\n"
                "\n### USER DATA ACCESS ###\n"
                "- To access full contact info (email, phone, address, bio), use [USER: get_profile].\n"
                "- To help the user update their data, use [USER: update_profile:field=value].\n"
            )
    except Exception as _pe:
        logger.debug(f"BRAIN: Could not load user identity for context: {_pe}")

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

    # --- VISION CAPABILITY NOTE ---
    # If images are attached to this call, explicitly tell the AI it can see them.
    # This overrides the 'check ACTIVE PROTOCOLS' rule, since Vision is a native
    # client capability (not a plugin) and is NOT listed in the registry.
    vision_note = ""
    if images:
        vision_note = (
            "\n### VISION INPUT ###\n"
            "You have native visual analysis capability. One or more images have been "
            "attached to this message. Analyse them directly and describe their contents "
            "in your response. Do NOT say you cannot see or do not have a visual module.\n"
        )

    system_prompt = (
        f"{personality_prompt}\n"
        f"{visual_identity_block}"
        f"{memory_context}\n"
        f"{history_block}\n"
        f"{self_awareness}\n"
        f"{capabilities}\n"
        "### OPERATIVE RULES ###\n"
        "1. Be consistent with your personality.\n"
        "2. IMPORTANT: Check [ACTIVE PROTOCOLS] before offering a service. If a specific protocol (like IMAGE_GEN, WEB, etc.) is NOT listed in the section above, YOU DO NOT HAVE THAT ABILITY. Do NOT offer to generate images, search the web, or perform other plugin actions if they are not active.\n\n"
        f"{identity_rules}"
        f"{file_manager_rules}"
        f"{force_clause}"
        f"{plugin_guidelines}"
        f"{RoutingManager.get_dynamic_instructions(config)}"
        f"{safety_instructions_block}"
        f"{user_profile_block}"
        f"{special_instructions_block}"
        f"{vision_note}"
    )

    
    logger.debug("BRAIN", f"System prompt created: {len(system_prompt)} characters")
    
    # (RP check moved before prompt assembly to preserve rules/capabilities)

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
    response = client.generate(system_prompt, user_text, backend_config, config.get('llm', {}), tools=tools, images=images, extra_messages=agent_context)
    
    # 5. Save to memory (respecting cognition config)
    logger.debug("BRAIN", "Saving to memory...")
    
    # Filter error messages (don't save them to history to avoid loops/bloat)
    is_error = False
    if isinstance(response, str) and (response.startswith("⚠️") or "Error" in response):
        is_error = True
    
    if not is_error and save_history:
        brain_interface.save_message("user", user_text, config=config, user_id=user_id, session_id=session_id)
        
        # Structured response management (String or Message with tool_calls)
        if isinstance(response, str):
            logger.debug("BRAIN", f"Response received from backend: {len(response)} characters")
            brain_interface.save_message("assistant", response, config=config, user_id=user_id, session_id=session_id)
        else:
            # It's a Message object (used a tool)
            logger.debug("BRAIN", "Response is a tool call object.")
            tool_names = [call.function.name for call in getattr(response, 'tool_calls', [])]
            brain_interface.save_message("assistant", f"*(Tool call: {', '.join(tool_names)})*", config=config, user_id=user_id, session_id=session_id)
    elif not save_history:
        logger.debug("BRAIN", "save_history is False; skipping history persistence for this Agentic Loop turn.")
    else:
        logger.debug("BRAIN", "AI response is an error; skipping history persistence.")
    
    logger.debug("BRAIN", f"=== END generate_response ===")
    return response