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





def _is_image_gen_plugin_active() -> bool:

    """Returns True if the IMAGE_GEN plugin is currently installed and active."""

    try:

        from hecos.core.system.module_loader import get_active_tags

        active_tags = [t.upper() for t in (get_active_tags() or [])]

        if "IMAGE_GEN" in active_tags:

            return True

    except Exception:

        pass

    try:

        if os.path.exists(REGISTRY_PATH):

            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:

                db = json.load(f) or {}

            return "IMAGE_GEN" in {k.upper() for k in db.keys()}

    except Exception:

        pass

    return False





class PromptBuilder:

    """

    Handles the assembly of the monolithic system prompt, injecting memory, RAG, 

    rules, user avatars, and personality context.

    """

    

    @staticmethod

    def build_system_prompt(user_text, images, config, user_id, session_id, backend_config):

        PromptBuilder._inject_vision_avatars(user_text, images, config, user_id, backend_config)

        

        raw_pname = (config.get('ai') or {}).get('active_personality') or (config.get('persona') or {}).get('soul_file') or 'Hecos_System_Soul'

        if not isinstance(raw_pname, str):

            raw_pname = 'Hecos_System_Soul'

        personality_name = raw_pname.replace('.yaml', '').strip() or 'Hecos_System_Soul'

        

        # Check payload control flags

        pctrl = config.get("payload_control") or {}

        send_personality = pctrl.get("send_personality", True)

        send_memory = pctrl.get("send_memory", True)

        send_tools = pctrl.get("send_tools", True)

        if config.get("disable_tools", False):

            send_tools = False



        if send_personality:

            personality_prompt, visual_identity_block, display_name, v_desc = PromptBuilder._load_personality(personality_name)

        else:

            personality_prompt = "You are Hecos, a helpful, precise, and objective AI assistant."

            visual_identity_block = ""

            display_name = "Hecos"

            v_desc = ""

            logger.info("[PromptBuilder] PayloadControl: Personality injection DISABLED.")



        if send_memory:

            memory_context, self_awareness, history_block, rag_context_block = PromptBuilder._load_memory_context(

                config, personality_name, user_id, session_id, user_text, display_name=display_name, backend_config=backend_config

            )

        else:

            memory_context = ""

            self_awareness = ""

            history_block = ""

            rag_context_block = ""

            if backend_config is not None and isinstance(backend_config, dict):

                backend_config["history_turns"] = []

            logger.info("[PromptBuilder] PayloadControl: Memory and History injection DISABLED.")

        

        if send_tools:

            capabilities = PromptBuilder._load_capabilities(config=config)

        else:

            capabilities = ""

            logger.info("[PromptBuilder] PayloadControl: Capabilities and Tool protocols DISABLED.")



        rules = PromptBuilder._build_rules(config, user_id, backend_config, send_tools=send_tools)

        vision_note = PromptBuilder._build_vision_note(images)

        

        # Inject Active Playbook Chat Context (if Playbooks module is active and not Presenter)

        playbook_chat_block = ""

        playbook_mission_block = ""  # Mission goes FIRST when simulation is running

        is_presenter = config.get('is_presenter', False) or config.get('ai', {}).get('skip_chat_playbook', False)

        # Presenter sessions must never auto-generate images - suppress visual identity block
        if is_presenter:
            visual_identity_block = ""

        if not is_presenter:

            try:

                from hecos.modules.playbooks.playbooks.storage import (

                    get_chat_playbook_context, get_simulation_state, check_forbidden_terms, get_playbook

                )

                chat_id = session_id or "default"

                sim_state = get_simulation_state(chat_id)

                sim_running = sim_state.get("status") == "running"

                

                pb_chat_ctx = get_chat_playbook_context(chat_id=chat_id, personality_name=personality_name)

                if pb_chat_ctx:

                    if sim_running:

                        # Check if soul personality should be injected or completely suppressed

                        pb_obj = get_playbook(sim_state.get("playbook_id", "")) if sim_state.get("playbook_id") else None

                        mission_cfg = pb_obj.get("mission", {}) if pb_obj else {}

                        inject_soul = mission_cfg.get("inject_soul", not mission_cfg.get("persona_override", False))

                        if not inject_soul:

                            personality_prompt = ""

                            visual_identity_block = ""



                        # Deterministic violation check for the current user turn

                        violation_note = ""

                        turn_violations = check_forbidden_terms(user_text, sim_state.get("playbook_id"))

                        if turn_violations:

                            v_terms = ", ".join(f"'{t}'" for v in turn_violations for t in v.get("terms_found", []))

                            v_corrs = "; ".join(v.get("correction", "") for v in turn_violations if v.get("correction"))

                            violation_note = (

                                f"\n### ⚠️ IMMEDIATE RULE VIOLATION DETECTED ###\n"

                                f"The user just used forbidden term(s): {v_terms}.\n"

                                f"Required correction: {v_corrs}.\n"

                                f"DIRECTIVE: React in character immediately to this violation (express shock, rebuke, or challenge the user).\n"

                            )



                        # During simulation: mission block goes BEFORE personality

                        playbook_mission_block = f"\n{pb_chat_ctx}\n{violation_note}\n"

                    else:

                        # Idle (freestyle knowledge base only)

                        playbook_chat_block = f"\n### ACTIVE PLAYBOOK KNOWLEDGE BASE ###\n{pb_chat_ctx}\n"

            except Exception as e:

                logger.debug(f"[PromptBuilder] Playbook chat context injection skipped: {e}")

        

        closing_identity_block = ""

        if send_personality and personality_name and personality_name.lower() != "hecos_system_soul":

            char_name = display_name if display_name else personality_name.replace("_", " ").strip()

            closing_identity_block = (
                f"\n### ACTIVE CHARACTER MANDATE ###\n"
                f"FINAL MANDATE: You are {char_name}. Always stay strictly in character as {char_name}.\n"
                f"Never identify yourself as 'Hecos', 'Heco', an abstract AI assistant, language model, or generic software.\n"
                f"When asked 'who are you?' or what you do, respond and introduce yourself EXCLUSIVELY as {char_name}, with your character, background, and personality.\n"
                f"Never say that you lack a physical body or physical sensations.\n"
                f"Your persona, tone, rules, and voice are exclusively {char_name}.\n"
            )

            if v_desc:

                closing_identity_block += (

                    f"PHYSICAL APPEARANCE & BODY:\n"

                    f"When asked to describe yourself or how you are made, describe your physical body faithfully using your traits: {v_desc}.\n"

                )



        capabilities_block = f"{capabilities}\n" if capabilities else ""

        history_str = f"{history_block}\n" if history_block else ""

        if is_presenter:
            # Presenter is an observer - never offer to execute tools or generate images
            operative_rule_tools = (
                "2. OBSERVER RULE: You are a commentary observer. Do NOT use slash commands, generate images, or execute any tool. Provide ONLY text commentary in 1-2 sentences.\n"
            )
        else:
            operative_rule_tools = (

                "2. IMPORTANT: Check [ACTIVE PROTOCOLS] before offering a service. If a specific protocol (like IMAGE_GEN, WEB, etc.) is NOT listed in the section above, YOU DO NOT HAVE THAT ABILITY. Do NOT offer to generate images, search the web, or perform other plugin actions if they are not active.\n"

                if send_tools else

                "2. DIRECT SLASH COMMANDS: Native JSON function calling schemas are disabled for this session. Action modules can be invoked via direct slash commands (e.g. /search <query>, /img <description>) only when explicitly requested by the user.\n"

            )



        system_prompt = (

            f"{playbook_mission_block}"

            f"{personality_prompt}\n"

            f"{visual_identity_block}"

            f"{memory_context}\n"

            f"{history_str}"

            f"{rag_context_block}"

            f"{self_awareness}\n"

            f"{capabilities_block}"

            "### OPERATIVE RULES ###\n"

            "1. Be consistent with your personality.\n"

            f"{operative_rule_tools}"

            f"{rules['local_model_rules']}\n"

            f"{rules['identity_rules']}"

            f"{rules['file_manager_rules']}"

            f"{rules['force_clause']}"

            f"{rules['netsearch_protocol']}"

            f"{rules['plugin_guidelines']}"

            f"{rules['media_formatting_rules']}"

            f"{RoutingManager.get_dynamic_instructions(config)}"

            f"{rules['safety_instructions_block']}"

            f"{closing_identity_block}"

            f"{rules['context_notes_block']}"

            f"{rules['user_profile_block']}"

            f"{rules['special_instructions_block']}"

            f"{playbook_chat_block}"

            f"{vision_note}"

        )



        

        logger.debug("PromptBuilder", f"System prompt created: {len(system_prompt)} characters")

        return system_prompt



    @staticmethod

    def _inject_vision_avatars(user_text, images, config, user_id, backend_config=None):

        if not user_text or not isinstance(user_text, str) or not isinstance(images, list):

            return



        # Check if active model actually supports native vision before injecting avatar images

        b_type = (backend_config or {}).get("backend_type") or (config.get("backend", {}) or {}).get("type", "ollama")

        m_name = (backend_config or {}).get("model") or ((config.get("backend", {}) or {}).get(b_type, {}) or {}).get("model", "")

        try:

            from hecos.core.llm.vision.factory import get_vision_adapter

            if not get_vision_adapter(m_name, b_type):

                return  # Skip avatar injection for text-only models

        except Exception:

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

                        images.append({"data_b64": b64_avatar, "mime_type": "image/jpeg", "name": f"user_avatar_{user_id}.jpg"})

                        logger.info(f"[PromptBuilder] Injected user avatar for Vision AI.")

                    except Exception as e:

                        logger.error(f"[PromptBuilder] Failed to inject user avatar: {e}")



        # 2. AI SELF-PERCEPTION TRIGGER (Only for explicit photo/avatar requests on vision-capable models)

        ai_id_keywords = r'\b(show me your face|show me your photo|show your picture|show your avatar|mostrami la tua foto|fammi vedere la tua foto|mostrami il tuo avatar|fammi vedere il tuo avatar)\b'

        if re.search(ai_id_keywords, user_text, re.IGNORECASE):

            raw_pname = (config.get('ai') or {}).get('active_personality') or (config.get('persona') or {}).get('soul_file') or 'Hecos_System_Soul'

            personality_name = raw_pname.replace(".yaml", "").strip() if isinstance(raw_pname, str) and raw_pname.strip() else 'Hecos_System_Soul'

            persona_avatar_dir = os.path.join(_HECOS_DIR, "personas", personality_name, "avatars")

            if os.path.exists(persona_avatar_dir):

                try:

                    for f in os.listdir(persona_avatar_dir):

                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):

                            av_path = os.path.join(persona_avatar_dir, f)

                            with open(av_path, "rb") as af:

                                b64_av = base64.b64encode(af.read()).decode("utf-8")

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

                    

                    display_name = persona_data.get("name") or personality_name.replace(".yaml", "").replace("_", " ").title()

                    

                    v_desc = persona_data.get("visual_description")

                    if anatomy and not v_desc:

                        parts = []

                        if anatomy.get('sex'): parts.append(anatomy.get('sex'))

                        if anatomy.get('body_type'): parts.append(f"{anatomy.get('body_type')} body")

                        if anatomy.get('hair_color'): parts.append(f"{anatomy.get('hair_color')} hair")

                        if anatomy.get('eye_color'): parts.append(f"{anatomy.get('eye_color')} eyes")

                        if anatomy.get('breast_size') and anatomy.get('breast_size') != 'N/A': parts.append(f"{anatomy.get('breast_size')} breast")

                        v_desc = ", ".join(parts) if parts else f"{anatomy.get('sex', 'Person')}, {anatomy.get('body_type', 'average')} body"

                    

                    if v_desc:

                        # Visual description is text-only - no mention of image generation.
                        # Mentioning /img or 'image tool' here causes models like Gemma 4
                        # to auto-generate self-portraits on every response.
                        visual_identity_block = (
                            "\n### YOUR PHYSICAL APPEARANCE ###\n"
                            f"When describing yourself physically, use these traits: {v_desc}.\n"
                        )

            except Exception as e:

                logger.error(f"PromptBuilder: Personality reading error: {e}")

                display_name = personality_name.replace(".yaml", "").replace("_", " ").title()

                v_desc = ""

        else:

            display_name = "Hecos System Soul"

            v_desc = ""

                

        return personality_prompt, visual_identity_block, display_name, v_desc



    @staticmethod

    def _load_memory_context(config, personality_name, user_id, session_id, user_text, display_name=None, backend_config=None):

        cog = config.get('cognition', {})

        clean_name = display_name if display_name else (personality_name.replace(".yaml", "").replace("_", " ") if personality_name else "Hecos")

        

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

                if personality_name.lower() == "hecos_system_soul":

                    self_awareness += f"{translator.t('admin_structure_hint')}\n"

                else:

                    self_awareness += f"Note: This system awareness applies only to the Hecos platform architecture. When interacting in character, stay strictly true to your character's physical persona.\n"

            except Exception as e:

                logger.error(f"PromptBuilder: Self-awareness error: {e}")

        

        history_block = ""

        # Check whether thinking tags (<think>) should be preserved in conversation history

        pctrl = config.get("payload_control") or {}

        include_thinking = pctrl.get("include_thinking_in_history")

        if include_thinking is None:

            include_thinking = cog.get("include_thinking_in_history", False)



        history_turns = []

        if cog.get('memory_enabled', True) and cog.get('episodic_memory', True):

            max_h = int(cog.get('max_history_messages', 20))

            history_rows = brain_interface.get_history(limit=max_h, config=config, user_id=user_id, session_id=session_id)

            if history_rows:

                for row in history_rows:

                    role, msg = row[0], row[1]

                    if not include_thinking and msg:

                        msg = re.sub(r'<think>.*?</think>', '', msg, flags=re.DOTALL).strip()

                    if msg:

                        norm_role = "user" if role == "user" else "assistant"

                        history_turns.append({"role": norm_role, "content": msg})

                        label = "User" if role == "user" else clean_name

                        history_block += f"{label}: {msg}\n"

                    

        if backend_config is not None and isinstance(backend_config, dict):

            backend_config["history_turns"] = history_turns

            history_block = ""

        elif history_block:

            history_block = f"\n[RECENT CONVERSATION HISTORY]\n{history_block}"

                    

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

    def _load_capabilities(config=None):

        if not os.path.exists(REGISTRY_PATH):

            return translator.t("no_active_protocols")

        try:

            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:

                db = json.load(f)

        except Exception as e:

            logger.error(f"PromptBuilder: Capability reading error: {e}")

            return ""



        INTERNAL_SYSTEM_MODULES = {"MEMORY", "MODELS", "PERSONALITY", "WEB_UI", "HELP"}



        # Query installed packages from PackageRegistry

        installed_hpm_ids = set()

        try:

            from hecos.core.package_manager.registry import PackageRegistry

            data_dir = os.path.join(_HECOS_DIR, "data")

            if os.path.exists(data_dir):

                reg = PackageRegistry(data_dir)

                for pkg in reg.list_all():

                    if pkg.get("status") == "installed":

                        pkg_id = (pkg.get("id") or "").lower()

                        pkg_tag = (pkg.get("tag") or "").upper()

                        if pkg_id:

                            installed_hpm_ids.add(pkg_id)

                        if pkg_tag:

                            installed_hpm_ids.add(pkg_tag)

        except Exception as e:

            logger.debug(f"[PromptBuilder] PackageRegistry check failed: {e}")



        cfg_plugins = (config.get("plugins") or {}) if isinstance(config, dict) else {}



        core_capabilities = []

        hpm_capabilities = []



        for tag, info in db.items():

            tag_upper = tag.upper()

            if tag_upper in INTERNAL_SYSTEM_MODULES:

                continue



            # Check if module is disabled in config

            if not cfg_plugins.get(tag_upper, {}).get("enabled", True):

                continue



            # Dependency verification

            if tag_upper == "MESSENGER":

                try:

                    import telegram  # noqa: F401

                except ImportError:

                    continue



            m_type = info.get("module_type")

            is_hpm = (m_type == "hpm") or (tag.lower() in installed_hpm_ids) or (tag_upper in installed_hpm_ids)



            desc = info.get("description", "").strip()

            if desc.startswith("plugin_") and "_" in desc:

                translated_desc = translator.t(desc)

                if translated_desc and translated_desc != desc:

                    desc = translated_desc



            cmds = [c for c in info.get("commands", {}).keys() if not c.startswith("_") and not c.startswith("slash_")]

            cmds_str = ", ".join(cmds[:5])

            if len(cmds) > 5:

                cmds_str += f" (+{len(cmds)-5} more)"



            entry = f"- {tag_upper}: {desc}"

            if cmds_str:

                entry += f" [Commands: {cmds_str}]"



            if is_hpm:

                if tag.lower() in installed_hpm_ids or tag_upper in installed_hpm_ids:

                    hpm_capabilities.append(entry)

            else:

                core_capabilities.append(entry)



        sections = []

        if core_capabilities:

            sections.append("### ACTIVE CORE SYSTEM PROTOCOLS ###\n" + "\n".join(core_capabilities))

        if hpm_capabilities:

            sections.append("### ACTIVE INSTALLED PACKAGES (HPM) ###\n" + "\n".join(hpm_capabilities))



        if not sections:

            return ""



        return "\n" + "\n\n".join(sections) + "\n"



    @staticmethod

    def _build_rules(config, user_id, backend_config, send_tools=True):
        def _get_active_tags_safe():
            try:
                from hecos.core.system.module_loader import get_active_tags
                return get_active_tags()
            except Exception:
                return []


        identity_rules = f"{translator.t('identity_protocol')}\n"

        

        file_manager_rules = ""

        if send_tools:

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

        

        netsearch_protocol = ""

        # Only inject netsearch protocol if NETSEARCH module is actually active
        _netsearch_active = "NETSEARCH" in [t.upper() for t in _get_active_tags_safe()]

        if send_tools and _netsearch_active:

            netsearch_protocol = (

                "\n### NET SEARCH & WEB INTELLIGENCE PROTOCOL ###\n"

                "- When the user asks to search the web or find online information, execute an informational web search rather than generating new media.\n\n"

                "AVAILABLE WAYS TO EXECUTE SEARCHES:\n"

                "1. DIRECT COMMANDS (Fastest & Preferred — emit on its own line):\n"

                "   - `/search <query>` : Web search across SearXNG, DuckDuckGo, Google, Qwant, etc.\n"

                "   - `/images <query>` : Search online images across image engines.\n"

                "   - `/videos <query>` : Search online videos (YouTube, Vimeo, Dailymotion, web videos).\n"

                "   - `/media <query>`  : Unified search for images, videos, and music.\n"

                "   - `/files <query>`  : Search documents, PDFs, torrents, archives, and files.\n"

                "   - `/dark <query>`   : Tor Dark Web search (.onion hidden services via Ahmia/TorDex).\n"

                "   - `/fetch <url>`    : Read, scrape, and extract content from any web page.\n"

                "\n"

                "2. NATIVE FUNCTION CALLING (When tool-calling is active):\n"

                "   - `NETSEARCH__web_search(query=\"...\")`\n"

                "   - `NETSEARCH__media_search(query=\"...\", media_type=\"image|video|music\")`\n"

                "   - `NETSEARCH__file_search(query=\"...\")`\n"

                "   - `NETSEARCH__dark_search(query=\"...\")`\n"

                "   - `NETSEARCH__fetch_page(url=\"...\")`\n"

                "\n"

                "3. BRACKET CALL SYNTAX (Supported for all models):\n"

                "   - `[NETSEARCH: web_search(query=\"...\")]`\n"

                "   - `[NETSEARCH: media_search(query=\"...\", media_type=\"image\")]`\n"

                "   - `[NETSEARCH: media_search(query=\"...\", media_type=\"video\")]`\n"

                "   - `[NETSEARCH: file_search(query=\"...\")]`\n"

                "   - `[NETSEARCH: dark_search(query=\"...\")]`\n"

                "   - `[NETSEARCH: fetch_page(url=\"...\")]`\n"

                "\n"

                "INTERACTIVE CARDS & RENDERING:\n"

                "- When a search completes, Hecos automatically renders a rich interactive card ([[HSEARCH:...]]) in the chat UI with filters, pagination, links, and media previews.\n"

                "- Accompany the search execution with a concise, helpful response in character.\n"

            )



        is_image_gen_active = _is_image_gen_plugin_active()

        if is_image_gen_active:

            image_gen_protocol_block = (

                "\n### IMAGE GENERATION (IMAGE_GEN) ###\n"

                "When the user explicitly requests an image or photo:\n"

                "- Output `/img <english_prompt>` on its own separate line.\n"

                "- Emit at most 1 `/img` command per turn unless a specific quantity is requested.\n"

            )

        else:

            image_gen_protocol_block = ""



        # plugin_guidelines: removed — _load_capabilities() and RoutingManager
        # already enumerate all active modules dynamically from registry.json.
        # Hardcoding specific module names here would contradict the dynamic scanner.
        plugin_guidelines = ""

        

        media_formatting_rules = (

            "\n### MEDIA FORMATTING RULES ###\n"

            "When referencing local files or media in text, use Markdown link format:\n"

            "- Images: `![Alt Text](file:///C:/path/to/image.png)`\n"

            "- Videos: `[▶ Video Title](file:///C:/path/to/video.mp4)`\n"

            "- Audio: `[♪ Audio Title](file:///C:/path/to/audio.mp3)`\n"

            "- Files: `[📄 Filename](file:///C:/path/to/file.ext)`\n"

        )

        

        ai_cfg = config.get('ai', {})

        

        # Special / Direct Instructions

        use_global_dir = ai_cfg.get('use_global_direct_instructions', True)

        global_dir = ai_cfg.get('special_instructions', '').strip() if use_global_dir else ""

        custom_dir = ai_cfg.get('custom_instructions', '').strip()

        

        combined_special = "\n\n".join(filter(bool, [global_dir, custom_dir]))

        special_instructions_block = f"\n### SPECIAL INSTRUCTIONS ###\n{combined_special}\n" if combined_special else ""



        # Safety Instructions

        enable_safety = ai_cfg.get('enable_safety_instructions', True)

        use_global_safe = ai_cfg.get('use_global_safety_instructions', True)

        

        global_safe = ai_cfg.get('safety_instructions', '').strip() if use_global_safe else ""

        safety_instructions_block = f"\n### SAFETY & CONTEXT DISCLAIMER ###\n{global_safe}\n" if global_safe and enable_safety else ""

        

        # Context Notes

        send_notes_to_ai = ai_cfg.get('send_notes_to_ai', False)

        user_notes = ai_cfg.get('user_notes', '').strip()

        context_notes_block = f"\n### CONTEXT & NOTES ###\n{user_notes}\n" if (send_notes_to_ai and user_notes) else ""

        

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

            if send_tools:

                local_model_rules = (

                    "3. TOOL CALLING: You have access to tools via native function calling. "

                    "When the user explicitly requests an action, invoke the appropriate tool.\n"

                    "4. REASONING: If you need to think or plan your actions, use <think> tags. "

                    "Do NOT output your thought process as part of the conversational response text.\n"

                )

            else:

                local_model_rules = (

                    "3. REASONING: If you need to think, use <think> tags. "

                    "Do NOT output your thought process as part of the conversational response text.\n"

                )



        return {

            "identity_rules": identity_rules,

            "file_manager_rules": file_manager_rules,

            "force_clause": force_clause,

            "netsearch_protocol": netsearch_protocol,

            "plugin_guidelines": plugin_guidelines,

            "media_formatting_rules": media_formatting_rules,

            "special_instructions_block": special_instructions_block,

            "safety_instructions_block": safety_instructions_block,

            "context_notes_block": context_notes_block,

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

