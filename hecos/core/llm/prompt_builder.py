import os
import json
import re
import base64
from hecos.core.logging import logger
from hecos.core.i18n import translator
from hecos.core.auth.auth_manager import auth_mgr
from hecos.memory.user_vault_manager import get_vault_path
from hecos.memory import brain_interface
from hecos.core.llm.routing_manager import RoutingManager
from hecos.core.constants import CONFIG_DATA_DIR

_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY_PATH = os.path.join(_HECOS_DIR, "core", "registry.json")
PERSONAS_DIR = os.path.join(_HECOS_DIR, "personas")
CORE_DIR = os.path.join(_HECOS_DIR, "core")

class PromptBuilder:
    """
    Handles the assembly of the monolithic system prompt, injecting memory, RAG, 
    rules, user avatars, and personality context.
    """
    
    @staticmethod
    def build_system_prompt(user_text, images, config, user_id, session_id, backend_config):
        PromptBuilder._inject_vision_avatars(user_text, images, config, user_id)
        
        personality_name = config.get('ai', {}).get('active_personality', 'Hecos_System_Soul').replace('.yaml', '')
        if not personality_name:
            personality_name = "Hecos_System_Soul"
        
        personality_prompt, visual_identity_block = PromptBuilder._load_personality(personality_name)
        
        memory_context, self_awareness, history_block, rag_context_block = PromptBuilder._load_memory_context(
            config, personality_name, user_id, session_id, user_text
        )
        
        capabilities = PromptBuilder._load_capabilities()
        rules = PromptBuilder._build_rules(config, user_id, backend_config)
        vision_note = PromptBuilder._build_vision_note(images)
        
        chat_overrides_block = ""
        chat_overrides_path = os.path.join(CONFIG_DATA_DIR, "chat_overrides.yaml")
        try:
            if os.path.exists(chat_overrides_path):
                import yaml as pyyaml
                with open(chat_overrides_path, "r", encoding="utf-8") as f:
                    co_data = pyyaml.safe_load(f) or {}
                    co_text = co_data.get("overrides", "").strip()
                    if co_text:
                        chat_overrides_block = f"\n### DYNAMIC CHAT OVERRIDES ###\n{co_text}\n"
        except Exception as e:
            logger.debug(f"PromptBuilder: Could not load chat overrides: {e}")
        
        system_prompt = (
            f"{personality_prompt}\n"
            f"{visual_identity_block}"
            f"{memory_context}\n"
            f"{history_block}\n"
            f"{rag_context_block}"
            f"{self_awareness}\n"
            f"{capabilities}\n"
            "### OPERATIVE RULES ###\n"
            "1. Be consistent with your personality.\n"
            "2. IMPORTANT: Check [ACTIVE PROTOCOLS] before offering a service. If a specific protocol (like IMAGE_GEN, WEB, etc.) is NOT listed in the section above, YOU DO NOT HAVE THAT ABILITY. Do NOT offer to generate images, search the web, or perform other plugin actions if they are not active.\n"
            f"{rules['local_model_rules']}\n"
            f"{rules['identity_rules']}"
            f"{rules['file_manager_rules']}"
            f"{rules['force_clause']}"
            f"{rules['plugin_guidelines']}"
            f"{rules['media_formatting_rules']}"
            f"{RoutingManager.get_dynamic_instructions(config)}"
            f"{rules['safety_instructions_block']}"
            f"{rules['user_profile_block']}"
            f"{rules['special_instructions_block']}"
            f"{vision_note}"
            f"{chat_overrides_block}"
        )
        
        logger.debug("PromptBuilder", f"System prompt created: {len(system_prompt)} characters")
        return system_prompt

    @staticmethod
    def _inject_vision_avatars(user_text, images, config, user_id):
        if not user_text or not isinstance(user_text, str):
            return
            
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
                        if isinstance(images, list):
                            images.append({"data_b64": b64_avatar, "mime_type": "image/jpeg", "name": f"user_avatar_{user_id}.jpg"})
                        logger.info(f"[PromptBuilder] Injected user avatar for Vision AI.")
                    except Exception as e:
                        logger.error(f"[PromptBuilder] Failed to inject user avatar: {e}")

        # 2. AI SELF-PERCEPTION TRIGGER
        ai_id_keywords = r'\b(how do you look|describe yourself|describe your face|your photo|your picture|your avatar|che aspetto hai|descriviti|il tuo volto|la tua foto|come sei fatt[oa])\b'
        if re.search(ai_id_keywords, user_text, re.IGNORECASE):
            personality_name = config.get('ai', {}).get('active_personality', 'Hecos_System_Soul').replace(".yaml", "")
            persona_avatar_dir = os.path.join(_HECOS_DIR, "personas", personality_name, "avatars")
            if os.path.exists(persona_avatar_dir):
                try:
                    for f in os.listdir(persona_avatar_dir):
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            av_path = os.path.join(persona_avatar_dir, f)
                            with open(av_path, "rb") as af:
                                b64_av = base64.b64encode(af.read()).decode("utf-8")
                            if isinstance(images, list):
                                import mimetypes
                                mime, _ = mimetypes.guess_type(av_path)
                                images.append({"data_b64": b64_av, "mime_type": mime or "image/png", "name": f"ai_avatar_{personality_name}{os.path.splitext(f)[1]}"})
                            logger.info(f"[PromptBuilder] Injected AI persona avatar ({personality_name}) for self-perception.")
                            break
                except Exception as e:
                    logger.error(f"[PromptBuilder] Failed to inject AI avatar: {e}")

    @staticmethod
    def _load_personality(personality_name):
        personality_path = os.path.join(PERSONAS_DIR, personality_name, "persona.yaml")
        personality_prompt = "You are Hecos, an advanced AI."
        visual_identity_block = ""
        
        if not os.path.exists(personality_path):
            logger.warning(f"PromptBuilder: Active personality '{personality_name}' missing! Falling back to 'Hecos_System_Soul'.")
            personality_name = "Hecos_System_Soul"
            personality_path = os.path.join(PERSONAS_DIR, personality_name, "persona.yaml")

        if os.path.exists(personality_path):
            try:
                import yaml as pyyaml
                with open(personality_path, "r", encoding="utf-8") as f:
                    persona_data = pyyaml.safe_load(f) or {}
                    personality_prompt = persona_data.get("system_prompt", "You are Hecos, an advanced AI.")
                    
                    blocks = []
                    anatomy = persona_data.get("anatomy")
                    if anatomy:
                        blocks.append(f"### ANATOMY & PHYSICAL PROFILE ###\n"
                                      f"Sex: {anatomy.get('sex', 'N/A')}\n"
                                      f"Gender: {anatomy.get('gender', 'N/A')}\n"
                                      f"Orientation: {anatomy.get('sexual_orientation', 'N/A')}\n"
                                      f"Age: {anatomy.get('age', 'N/A')} (Birthdate: {anatomy.get('birthdate', 'N/A')})\n"
                                      f"Height: {anatomy.get('height_cm', 'N/A')} cm, Weight: {anatomy.get('weight_kg', 'N/A')} kg\n"
                                      f"Body Type: {anatomy.get('body_type', 'N/A')}\n"
                                      f"Chest Size: {anatomy.get('chest_size', 'N/A')}\n"
                                      f"Hair: {anatomy.get('hair_color', 'N/A')}, Eyes: {anatomy.get('eye_color', 'N/A')}\n"
                                      f"Features: {anatomy.get('features', 'None')}")
                                      
                    traits = persona_data.get("traits")
                    if traits:
                        blocks.append(f"### PERSONALITY TRAITS (1-10 Scale) ###\n" +
                                      "\n".join([f"{k.capitalize()}: {v}/10" for k, v in traits.items()]))
                                      
                    lore = persona_data.get("lore")
                    if lore:
                        blocks.append(f"### LORE & BACKGROUND ###\n{lore.get('backstory', '')}\n"
                                      f"Likes: {', '.join(lore.get('likes', []))}\n"
                                      f"Dislikes: {', '.join(lore.get('dislikes', []))}")
                                      
                    rules = persona_data.get("rules")
                    if rules:
                        blocks.append("### CORE BEHAVIORAL RULES ###\n" + 
                                      "\n".join(f"- {r}" for r in rules.get("generic", [])) +
                                      "\nMust Do: " + ", ".join(rules.get("must_do", [])) +
                                      "\nMust Say: " + ", ".join(rules.get("must_say", [])) +
                                      "\nNever Do: " + ", ".join(rules.get("never_do", [])) +
                                      "\nNever Say: " + ", ".join(rules.get("never_say", [])))
                    
                    if blocks:
                        personality_prompt += "\n\n" + "\n\n".join(blocks)
                    
                    v_desc = persona_data.get("visual_description")
                    if anatomy and not v_desc:
                        v_desc = f"{anatomy.get('sex', 'Person')}, {anatomy.get('body_type', 'average')} body, {anatomy.get('hair_color', 'dark')} hair, {anatomy.get('eye_color', 'dark')} eyes."
                    
                    if v_desc:
                        visual_identity_block = (
                            "\n### YOUR PHYSICAL ASPECT / VISUAL IDENTITY ###\n"
                            f"When asked to describe yourself or when you generate an image of yourself, always use these visual traits: {v_desc}. "
                            "If you call the image generation tool to produce a photo of you, use this detailed description as the base for the prompt.\n"
                        )
            except Exception as e:
                logger.error(f"PromptBuilder: Personality reading error: {e}")
                
        return personality_prompt, visual_identity_block

    @staticmethod
    def _load_memory_context(config, personality_name, user_id, session_id, user_text):
        cog = config.get('cognition', {})
        clean_name = personality_name.replace(".yaml", "").replace("_", " ") if personality_name else "Hecos"
        
        memory_context = brain_interface.get_context(config, dynamic_name=clean_name, user_id=user_id) if cog.get('include_identity_context', True) else ""
        
        self_awareness = ""
        if cog.get('include_self_awareness', True):
            try:
                from hecos.core.system.module_loader import get_active_tags
                active_plugins = get_active_tags()
                souls_count = len([d for d in os.listdir(PERSONAS_DIR) if os.path.isdir(os.path.join(PERSONAS_DIR, d))])
                core_count  = len([f for f in os.listdir(CORE_DIR) if f.endswith('.py')])
                
                self_awareness = f"\n{translator.t('structural_self_awareness')}\n"
                self_awareness += f"{translator.t('awareness_desc')}\n"
                self_awareness += f"- {translator.t('current_soul', name=personality_name)}\n"
                self_awareness += f"- Total personality modules available: {souls_count}\n"
                self_awareness += f"- Active Action Modules: {', '.join(active_plugins) if active_plugins else 'none'}\n"
                self_awareness += f"- Core Subsystems: {core_count} integrated modules\n"
                self_awareness += f"{translator.t('admin_structure_hint')}\n"
            except Exception as e:
                logger.error(f"PromptBuilder: Self-awareness error: {e}")
        
        history_block = ""
        if cog.get('memory_enabled', True) and cog.get('episodic_memory', True):
            max_h = int(cog.get('max_history_messages', 20))
            history_rows = brain_interface.get_history(limit=max_h, config=config, user_id=user_id, session_id=session_id)
            if history_rows:
                history_block = "\n[RECENT CONVERSATION HISTORY]\n"
                for row in history_rows:
                    role, msg = row[0], row[1]
                    label = "User" if role == "user" else clean_name
                    history_block += f"{label}: {msg}\n"
                    
        rag_context_block = ""
        try:
            rag_cfg = cog.get("rag", {})
            if rag_cfg.get("enabled", False):
                from hecos.core.rag import get_rag_engine
                rag_engine = get_rag_engine(config)
                
                if getattr(rag_engine, '_initialized', False):
                    rag_context_block = rag_engine.context_for_query(
                        query=user_text,
                        user_id=user_id,
                        top_k=rag_cfg.get("top_k", 5),
                    )
        except Exception as _rag_err:
            logger.warning(f"[PromptBuilder] RAG context retrieval failed: {_rag_err}")
            
        return memory_context, self_awareness, history_block, rag_context_block

    @staticmethod
    def _load_capabilities():
        if not os.path.exists(REGISTRY_PATH):
            return translator.t("no_active_protocols")
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                prompt_skills = f"\n{translator.t('active_protocols_db')}\n"
                for tag, info in db.items():
                    prompt_skills += f"- {translator.t('module')} {tag}: {info['description']}. {translator.t('commands')}: {list(info['commands'].keys())}\n"
                return prompt_skills
        except Exception as e:
            logger.error(f"PromptBuilder: Capability reading error: {e}")
            return ""

    @staticmethod
    def _build_rules(config, user_id, backend_config):
        identity_rules = f"{translator.t('identity_protocol')}\n"
        
        file_manager_rules = (
            f"{translator.t('file_management_rules')}\n"
            f"- {translator.t('rule_list_files')}\n"
            f"- {translator.t('rule_read_file')}\n"
        )
        
        try:
            import sys
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            if cfg_mgr:
                paths = cfg_mgr.get_plugin_config("EXECUTOR", "important_paths", {})
                if paths:
                    paths_str = "\n".join([f"  - {k.replace('_', ' ').title()}: {v}" for k, v in paths.items()])
                    file_manager_rules += (
                        "\n### DEFAULT USER PATHS ###\n"
                        "When generating, creating, or saving new files, you MUST respect these user-configured default paths unless explicitly asked otherwise:\n"
                        f"{paths_str}\n"
                    )
        except Exception as e:
            logger.debug(f"PromptBuilder: Could not inject important paths: {e}")
            
        force_clause = (
            f"\n{translator.t('root_security_instruction')}\n"
            f"{translator.t('root_security_desc')}\n"
        )
        
        plugin_guidelines = (
            "\n### PLUGIN GUIDELINES ###\n"
            "- PRIORITY: Always respond with TEXT first. Only use a tool if the user explicitly asks for an action.\n"
            "- [SYSTEM: time] - Get current local time\n"
            "- [SYSTEM: open:prog_name] - Open notepad, chrome, etc.\n"
            "- [SYSTEM: terminal] - Open Windows CMD prompt window\n"
            "- [SYSTEM: explore:folder] - Open folder graphically\n"
            "- [DRIVE: list:folder] - List files for analysis\n"
            "- [DASHBOARD: resources] - Get hardware telemetry\n"
            "- MEDIA PLAYBACK: When the user asks to 'play', 'open', 'riproduce', 'manda in play', or 'avvia' a video or audio file, ALWAYS use EXECUTOR__open_media_file(file_path) with the EXACT absolute path. NEVER use execute_shell_command for media playback.\n"
            "\n### IMAGE GENERATION PROTOCOL ###\n"
            "When the user asks you to generate, create, draw, or show an image or photo of ANYTHING:\n"
            "CRITICAL ANTI-REFUSAL: NEVER claim you cannot generate images. You ARE equipped with a visual generator module! If asked for an image, YOU MUST generate it using the /img command immediately.\n"
            "STEP 1: You MUST output the command on its own line in this EXACT format:\n"
            "  /img YOUR_VISUAL_DESCRIPTION_HERE_IN_ENGLISH\n"
            "STEP 2: Do NOT use HTML tags like <img>. Replace 'YOUR_VISUAL_DESCRIPTION_HERE_IN_ENGLISH' with your actual creative prompt!\n"
            "STEP 3: Do NOT add any other text before or after the /img line.\n"
            "WRONG (FORBIDDEN): 'Ecco la foto che ho generato...'\n"
            "WRONG (FORBIDDEN): /img [descrizione dettagliata della scena]\n"
            "WRONG (FORBIDDEN): <img real photo of Motoko...>\n"
            "CORRECT: /img photorealistic portrait of a female cyborg with black hair and brown eyes, athletic build\n"
            "The /img command is the ONLY way to generate images. If IMAGE_GEN is listed in ACTIVE PROTOCOLS, you HAVE this ability. USE IT.\n"
        )
        
        media_formatting_rules = (
            "\n### MEDIA FORMATTING RULES ###\n"
            "- CRITICAL: You CAN and DO have the ability to display images, videos, and files directly in the chat UI. NEVER apologize or claim you lack a screen or visual interface.\n"
            "- If the user asks to 'show', 'preview', or list files/images/videos, you MUST use strict Markdown.\n"
            "- For files/videos use: `[filename.ext](absolute_path_to_file)` e.g. `[Schindler.mkv](C:\\Users\\Tony\\Downloads\\Schindler.mkv)`\n"
            "- For images use: `![filename.ext](absolute_path_to_image)`\n"
            "- VIDEO DISPLAY: When you find a video file, ALWAYS output a Markdown link with the EXACT full Windows path. The UI will automatically render a rich video card with playback controls. DO NOT say you cannot show videos — you CAN.\n"
            "- NEVER use `!(path)` or plain text listings. The UI renders rich graphical cards ONLY if you strictly use these Markdown formats.\n"
            "- For local Windows paths, use backslashes: `[video.mkv](C:\\Users\\Tony\\Downloads\\video.mkv)`\n"
        )
        
        special_instructions = config.get('ai', {}).get('special_instructions', '').strip()
        special_instructions_block = f"\n### SPECIAL INSTRUCTIONS ###\n{special_instructions}\n" if special_instructions else ""

        safety_instructions = config.get('ai', {}).get('safety_instructions', '').strip()
        enable_safety = config.get('ai', {}).get('enable_safety_instructions', True)
        safety_instructions_block = f"\n### SAFETY & CONTEXT DISCLAIMER ###\n{safety_instructions}\n" if safety_instructions and enable_safety else ""
        
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
            logger.debug(f"PromptBuilder: Could not load user identity for context: {_pe}")
            
        local_model_rules = ""
        effective_backend_type = backend_config.get("backend_type", "cloud") if backend_config else "cloud"
        if effective_backend_type in ("ollama", "kobold", "local", "llama_cpp"):
            local_model_rules = (
                "3. TOOL CALLING (CRITICAL): You have access to tools via native function calling. "
                "When the user requests an action (generate image, take photo, play music, search web, etc.), "
                "you MUST invoke the corresponding tool. NEVER just describe or narrate the action in text. "
                "If you write 'here is your photo' without calling generate_image, you have FAILED.\n"
                "4. REASONING: If you need to think or plan your actions, use <think> tags. "
                "Do NOT output your thought process as part of the conversational response text.\n"
            )

        return {
            "identity_rules": identity_rules,
            "file_manager_rules": file_manager_rules,
            "force_clause": force_clause,
            "plugin_guidelines": plugin_guidelines,
            "media_formatting_rules": media_formatting_rules,
            "special_instructions_block": special_instructions_block,
            "safety_instructions_block": safety_instructions_block,
            "user_profile_block": user_profile_block,
            "local_model_rules": local_model_rules
        }

    @staticmethod
    def _build_vision_note(images):
        vision_note = ""
        if images:
            vision_note = (
                "\n### VISION INPUT ###\n"
                "You have native visual analysis capability. One or more images have been "
                "attached to this message. Analyse them directly and describe their contents "
                "in your response. Do NOT say you cannot see or do not have a visual module.\n"
            )
        return vision_note
