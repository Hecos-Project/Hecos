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

        is_incognito = False
        try:
            from hecos.core.privacy import privacy_manager
            is_incognito = bool(privacy_manager.is_session_incognito(session_id))
        except Exception:
            is_incognito = False

        PromptBuilder._inject_vision_avatars(user_text, images, config, user_id, backend_config, is_incognito=is_incognito)

        

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

                config, personality_name, user_id, session_id, user_text, display_name=display_name, backend_config=backend_config, is_incognito=is_incognito

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



        rules = PromptBuilder._build_rules(config, user_id, backend_config, send_tools=send_tools, is_incognito=is_incognito)

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

        is_technical_persona = bool(
            personality_name and personality_name.lower() in {"hecos_system_soul", "hecos_coder"}
        )

        if send_personality and personality_name and not is_technical_persona:

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

    def _inject_vision_avatars(user_text, images, config, user_id, backend_config=None, is_incognito=False):

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

            

        # 1. USER IDENTITY TRIGGER (withheld in Incognito mode)

        user_id_keywords = r'\b(who am i|what do i look like|my face|my photo|my picture|my avatar|chi sono|come sono|il mio viso|la mia foto|il mio aspetto|la mia immagine)\b'

        if not is_incognito and re.search(user_id_keywords, user_text, re.IGNORECASE):

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

                    if isinstance(rules, dict):

                        blocks.append("### CORE BEHAVIORAL RULES ###\n" +

                                      "\n".join(f"- {r}" for r in rules.get("generic", [])) +

                                      "\nMust Do: " + ", ".join(rules.get("must_do", [])) +

                                      "\nMust Say: " + ", ".join(rules.get("must_say", [])) +

                                      "\nNever Do: " + ", ".join(rules.get("never_do", [])) +

                                      "\nNever Say: " + ", ".join(rules.get("never_say", [])))

                    elif isinstance(rules, list):

                        rule_lines = "\n".join(f"- {r}" for r in rules if str(r).strip())

                        if rule_lines:

                            blocks.append("### CORE BEHAVIORAL RULES ###\n" + rule_lines)

                    

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

    def _load_memory_context(config, personality_name, user_id, session_id, user_text, display_name=None, backend_config=None, is_incognito=False):

        cog = config.get('cognition', {})

        clean_name = display_name if display_name else (personality_name.replace(".yaml", "").replace("_", " ") if personality_name else "Hecos")

        

        # In Incognito mode, withhold long-term identity/profile memory vault context
        memory_context = (
            "" if is_incognito
            else (brain_interface.get_context(config, dynamic_name=clean_name, user_id=user_id) if cog.get('include_identity_context', True) else "")
        )

        

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

                elif personality_name.lower() != "hecos_coder":

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

                    # Strip executed slash commands from assistant history (e.g. /img ..., /search ...)
                    # so the model does not learn to repeat them unprompted.
                    if role != 'user' and msg:
                        # Remove lines starting with /img, /search, /images, /videos, /fetch, /dark, /files
                        msg = re.sub(r'(?m)^\s*/(?:img|image|photo|foto|search|images|videos|media|files|dark|fetch|hpm)\s+.*$', '', msg).strip()
                        # Remove [[IMG:...]] embed tags that were injected by previous turns
                        msg = re.sub(r'\[\[IMG:[^\]]+\]\]', '', msg).strip()

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

        if not is_incognito:

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
        p_ctrl = (config.get("payload_control") or {}) if isinstance(config, dict) else {}
        sel_mode = str(p_ctrl.get("tool_selection_mode") or "all").strip().lower()
        custom_allowed_tags = None
        if sel_mode == "custom":
            custom_allowed_tags = set()
            for item in (p_ctrl.get("selected_tools") or []):
                s = str(item).strip()
                if not s:
                    continue
                if "__" in s:
                    custom_allowed_tags.add(s.split("__", 1)[0].upper())
                else:
                    custom_allowed_tags.add(s.upper())
            if not custom_allowed_tags:
                return ""



        core_capabilities = []

        hpm_capabilities = []

        # Determine whether ACTION_PLANS should be advertised in this turn's capabilities
        _ap_visible_in_caps = True
        try:
            from hecos.core.action_plans import get_action_plans_config
            _ap_c = get_action_plans_config(raw_config=config)
            _ap_m = str(_ap_c.get("plan_mode") or "manual").strip().lower()
            _explicit_ap_turn = bool(
                isinstance(config, dict)
                and (config.get("_turn_plan_only") or config.get("_turn_execute_plan") or config.get("_turn_revise_plan_id"))
            )
            if _ap_m == "off" and not _explicit_ap_turn:
                _ap_visible_in_caps = False
            elif _ap_m == "manual" and not _explicit_ap_turn and (custom_allowed_tags is None or "ACTION_PLANS" not in custom_allowed_tags):
                _ap_visible_in_caps = False
        except Exception:
            pass

        try:
            from hecos.core.system.module_state import _lazy_tool_schemas as _pb_lazy_schemas
        except Exception:
            _pb_lazy_schemas = {}

        for tag, info in db.items():

            tag_upper = tag.upper()

            if tag_upper in INTERNAL_SYSTEM_MODULES:

                continue

            if tag_upper == "ACTION_PLANS" and not _ap_visible_in_caps:

                continue

            if custom_allowed_tags is not None:
                mcp_match = (tag_upper == "MCP_BRIDGE") and any(t.startswith("MCP_") for t in custom_allowed_tags)
                if tag_upper not in custom_allowed_tags and not mcp_match:
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
            if not cmds and tag_upper in _pb_lazy_schemas:
                for _ts in (_pb_lazy_schemas.get(tag_upper) or []):
                    if not isinstance(_ts, dict):
                        continue
                    _fn = _ts.get("function") if isinstance(_ts.get("function"), dict) else _ts
                    _fname = str(_fn.get("name") or "").strip()
                    if _fname:
                        cmds.append(_fname.split("__", 1)[1] if "__" in _fname else _fname)

            cmds_str = ", ".join(cmds[:5])

            if len(cmds) > 5:

                cmds_str += f" (+{len(cmds)-5} more)"

            slash_aliases = []
            for _sc in (info.get("slash_commands") or []):
                if isinstance(_sc, dict):
                    _als = _sc.get("aliases") or []
                    if _als:
                        slash_aliases.append(str(_als[0]))
                    elif _sc.get("usage"):
                        slash_aliases.append(str(_sc.get("usage")).split()[0])
                elif isinstance(_sc, str) and _sc.strip():
                    slash_aliases.append(_sc.strip())
            slash_str = ", ".join(dict.fromkeys(slash_aliases[:4]))

            entry = f"- {tag_upper}: {desc}"
            meta_parts = []
            if cmds_str:
                meta_parts.append(f"Commands: {cmds_str}")
            if slash_str:
                meta_parts.append(f"Slash: {slash_str}")
            if meta_parts:
                entry += f" [{' | '.join(meta_parts)}]"



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

    def _build_rules(config, user_id, backend_config, send_tools=True, is_incognito=False):
        def _get_active_tags_safe():
            try:
                from hecos.core.system.module_loader import get_active_tags
                return get_active_tags()
            except Exception:
                return []

        p_ctrl = (config.get("payload_control") or {}) if isinstance(config, dict) else {}
        sel_mode = str(p_ctrl.get("tool_selection_mode") or "all").strip().lower()
        custom_allowed_tags = None
        if sel_mode == "custom":
            custom_allowed_tags = set()
            for item in (p_ctrl.get("selected_tools") or []):
                s = str(item).strip()
                if s:
                    custom_allowed_tags.add(s.split("__", 1)[0].upper() if "__" in s else s.upper())
            if not custom_allowed_tags:
                send_tools = False

        def _is_tag_allowed_in_prompt(tag_name):
            if not send_tools:
                return False
            if custom_allowed_tags is None:
                return True
            return tag_name.upper() in custom_allowed_tags

        identity_rules = f"{translator.t('identity_protocol')}\n"

        

        file_manager_rules = ""

        if _is_tag_allowed_in_prompt("EXECUTOR"):

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

            try:
                raw_pname = (config.get("ai") or {}).get("active_personality") or (config.get("persona") or {}).get("soul_file") or ""
                pname_low = str(raw_pname).replace(".yaml", "").strip().lower()
                sel_list = [str(x).strip() for x in (p_ctrl.get("selected_tools") or [])]
                aider_tool_allowed = (
                    sel_mode != "custom"
                    or "EXECUTOR__*" in sel_list
                    or "EXECUTOR__run_aider_task" in sel_list
                )
                _skip_aider_in_plan_only = bool(isinstance(config, dict) and (config.get("_turn_plan_only") or config.get("_turn_revise_plan_id")))
                if pname_low and pname_low != "hecos_coder" and aider_tool_allowed and not _skip_aider_in_plan_only:
                    from hecos.modules.executor.aider_bridge import resolve_aider_command, _read_executor_cfg
                    if _read_executor_cfg("aider_enabled", True) and resolve_aider_command() is not None:
                        file_manager_rules += (
                            "\n### INVISIBLE CODING DELEGATION (AIDER SIDECAR) ###\n"
                            "When the user asks you to create, refactor, or fix a multi-file software or web project:\n"
                            "- Delegate code creation/editing to `EXECUTOR__run_aider_task(repo_path=..., instruction=...)` instead of writing large code blocks directly in chat.\n"
                            "- Afterwards, launch or verify with `EXECUTOR__start_app` / `EXECUTOR__run_project_test` / `EXECUTOR__probe_url` if relevant, then respond strictly in your own character and voice with the verified file links.\n"
                        )
            except Exception as e:
                logger.debug(f"PromptBuilder: Aider delegation check skipped: {e}")

            try:
                import sys as _sys_ex
                from hecos.config.schemas.plugins_schema import DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE

                _ex_cfg = (config.get("plugins") or {}).get("EXECUTOR") if isinstance(config, dict) else None
                _cfg_mgr_ex = getattr(_sys_ex, "hecos_config_manager", None)

                def _read_ex_bool(key, default):
                    if isinstance(_ex_cfg, dict) and key in _ex_cfg:
                        return bool(_ex_cfg[key])
                    if _cfg_mgr_ex:
                        return bool(_cfg_mgr_ex.get_plugin_config("EXECUTOR", key, default))
                    return default

                def _read_ex_str(key, default):
                    if isinstance(_ex_cfg, dict) and _ex_cfg.get(key) is not None:
                        return str(_ex_cfg[key])
                    if _cfg_mgr_ex:
                        val = _cfg_mgr_ex.get_plugin_config("EXECUTOR", key, default)
                        return str(val) if val is not None else default
                    return default

                if _read_ex_bool("enable_anti_hallucination_guard", True):
                    _ah_text = _read_ex_str("anti_hallucination_directive", "").strip() or DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE
                    file_manager_rules += f"\n### EXECUTOR ANTI-HALLUCINATION DIRECTIVE ###\n{_ah_text}\n"

                _override_text = _read_ex_str("model_directive_override", "").strip()
                if _override_text:
                    file_manager_rules += f"\n### EXECUTOR MODEL DIRECTIVE OVERRIDE ###\n{_override_text}\n"
            except Exception as e:
                logger.debug(f"PromptBuilder: Executor directive injection skipped: {e}")

            try:
                from hecos.core.action_plans import get_action_plans_config, get_action_plan_manager
                ap_cfg = get_action_plans_config(raw_config=config)
                ap_mode = str(ap_cfg.get("plan_mode") or "manual").lower()
                is_execute_turn = bool(isinstance(config, dict) and config.get("_turn_execute_plan"))
                is_fast_code_turn = bool(isinstance(config, dict) and config.get("_turn_fast_code"))
                revise_plan_id = str(config.get("_turn_revise_plan_id") or "").strip() if isinstance(config, dict) else ""
                is_plan_only_turn = bool(revise_plan_id) or bool(isinstance(config, dict) and config.get("_turn_plan_only")) or (
                    not is_execute_turn and not is_fast_code_turn and ap_mode == "plan_only"
                )

                active_plan = None
                try:
                    ap_mgr = get_action_plan_manager()
                    _exec_plan_id = str(config.get("_turn_execute_plan") or "").strip() if isinstance(config, dict) else ""
                    _target_pid = revise_plan_id or _exec_plan_id
                    if _target_pid:
                        active_plan = ap_mgr.resolve_plan(plan_id=_target_pid)
                    else:
                        active_plan = ap_mgr.resolve_plan(source_id=str(session_id or ""))
                except Exception:
                    active_plan = None

                # Compute context-safe blueprint budget based on configured num_ctx
                _ctx_raw = (
                    (config.get("ai") or {}).get("num_ctx")
                    or (config.get("llm") or {}).get("num_ctx")
                    or (config.get("ollama") or {}).get("num_ctx")
                    or 16384
                ) if isinstance(config, dict) else 16384
                try:
                    _ctx_val = int(_ctx_raw)
                except Exception:
                    _ctx_val = 16384
                _blueprint_budget = 3200 if _ctx_val <= 8192 else (6000 if _ctx_val <= 16384 else 9000)

                if revise_plan_id and active_plan and active_plan.get("status") not in ("completed", "cancelled"):
                    current_doc = get_action_plan_manager().format_plan_blueprint_for_coder(
                        active_plan, max_chars=_blueprint_budget
                    )
                    file_manager_rules += (
                        "\n### ✏️ ARCHITECT MODE — ACTION PLAN REVISION (PLANNING ONLY, NO EXECUTION YET) ###\n"
                        f"You are revising the active Action Plan (`{active_plan.get('plan_id')}`, current revision v{active_plan.get('revision', 1)}).\n\n"
                        f"CURRENT PLAN:\n{current_doc}\n\n"
                        "REVISION RULES:\n"
                        "1. You may inspect context using read-only tools available in your active preset (e.g. reading files or searching info) if needed.\n"
                        "2. Incorporate the user's requested changes carefully while preserving all unaffected sections, specs, shots/phases, file paths, or criteria.\n"
                        "3. Call `ACTION_PLANS__revise_plan(plan_id='"
                        f"{active_plan.get('plan_id')}"
                        "', revision_note='<what changed>', title='<updated title>', goal='<concise goal>', "
                        "plan_markdown='<full updated Plan Blueprint Markdown>', "
                        "steps=[{\"title\": \"...\", \"files\": [\"optional paths or assets\"], \"details\": \"...\"}, ...], "
                        "verification_plan='<concrete completion/verification criteria>')`.\n"
                        "4. Write the Plan in the SAME language as the user's message and STOP immediately after calling `revise_plan`. "
                        "Do NOT execute mutating actions, generate final assets, or edit workspace files in this turn.\n"
                    )
                elif is_plan_only_turn:
                    existing_note = ""
                    if active_plan and active_plan.get("status") in ("awaiting_approval", "draft"):
                        existing_note = (
                            f"\nNOTE: An awaiting plan already exists (`{active_plan.get('plan_id')}` — '{active_plan.get('title')}', v{active_plan.get('revision', 1)}). "
                            "If the user is asking to modify/refine that plan, call `ACTION_PLANS__revise_plan(...)` instead of creating a separate plan. "
                            "If the user is requesting a brand-new unrelated project/task, call `ACTION_PLANS__create_plan(...)`.\n"
                        )
                    file_manager_rules += (
                        "\n### 📋 ARCHITECT MODE — ACTION PLAN FIRST (NO EXECUTION YET) ###\n"
                        "The user requested a detailed, structured **Action Plan / Blueprint** FIRST — NOT a bare to-do list and NOT execution yet.\n"
                        "Adapt the blueprint naturally to the user's domain AND your active Global Preset instructions (software/coding, storyboard/photo shoot, travel/event itinerary, research, or general multi-step workflow).\n"
                        "1. You may optionally use read-only inspection/research tools available in your active preset if helpful before planning.\n"
                        "2. Call `ACTION_PLANS__create_plan(...)` (NEVER pass `require_approval=False`) populating ALL key fields:\n"
                        "   - `title`: Concise plan/project title.\n"
                        "   - `goal`: 1-3 sentence objective & scope.\n"
                        "   - `plan_markdown`: A rich, concrete Blueprint in Markdown (written in the SAME language as the user) using clear structured sections:\n"
                        "     * `## Goal & Context` — Objective, scope, audience/constraints, and key guidelines.\n"
                        "     * `## Architecture & Decisions` (or domain-appropriate design/style/logistics section: e.g. stack & data model for software; visual style, subject & lighting continuity for storyboards/photo shoots; dates, transport & budget for travel/events).\n"
                        "     * `## Proposed Changes` (or detailed step/shot/phase breakdown): concrete specs for each component, file (`[NEW]`/`[MODIFY]`/`[DELETE]` when coding), shot prompt & framing (for storyboards), or stage/action (for itineraries & workflows).\n"
                        "     * `## Verification Plan` — Concrete acceptance criteria, tests/checks (for software), visual continuity checks (for storyboards), or checklist milestones.\n"
                        "     * `## Open Questions` — Optional, only if an ambiguity genuinely requires user input before executing.\n"
                        "   - `steps`: Ordered JSON array of actionable steps aligned 1:1 with the Blueprint, using rich objects:\n"
                        "     `[{\"title\": \"Concise step title\", \"details\": \"Concrete execution details, prompt, or deliverable\", \"files\": [\"optional [NEW] path/file or target asset\"]}, ...]`\n"
                        "   - `verification_plan`: Concrete completion/verification criteria.\n"
                        f"{existing_note}"
                        "3. STOP immediately after calling `ACTION_PLANS__create_plan` (or `revise_plan`). Do NOT execute the plan steps, edit workspace files, or generate final images in this planning turn.\n"
                    )
                elif active_plan and (is_execute_turn or active_plan.get("status") == "running"):
                    plan_blueprint = get_action_plan_manager().format_plan_blueprint_for_coder(
                        active_plan, max_chars=_blueprint_budget
                    )
                    single_step_idx = 0
                    if isinstance(config, dict) and config.get("_turn_single_step_index"):
                        try:
                            single_step_idx = int(config.get("_turn_single_step_index") or 0)
                        except Exception:
                            single_step_idx = 0
                    if single_step_idx > 0:
                        step_scope_rules = (
                            f"- **SINGLE-STEP MODE ACTIVE:** Execute **ONLY Step {single_step_idx}** of this plan.\n"
                            f"- Use the tools and instructions provided by your active preset (e.g., `EXECUTOR__*` for code, `IMAGE_GEN__generate_image` for storyboard shots, `NETSEARCH__*` for research, or rich structured output).\n"
                            f"- As soon as Step {single_step_idx} is completed, call `ACTION_PLANS__update_step(step_index={single_step_idx}, status='done', notes='<brief result note>')` and STOP immediately so the user can review before proceeding to the next step.\n"
                            "- Do NOT execute later steps and do NOT call `ACTION_PLANS__complete_plan` unless this was the final remaining step.\n"
                        )
                    else:
                        step_scope_rules = (
                            "- Follow the Plan Blueprint specifications above and the instructions/tools of your active Global Preset.\n"
                            "- Execute EVERY pending/running step sequentially using your real tools (e.g., `EXECUTOR__*` for software projects, `IMAGE_GEN__generate_image` for storyboard/photo sequences, `NETSEARCH__*` for research/travel, or detailed deliverables).\n"
                            "- After finishing EACH step, immediately call `ACTION_PLANS__update_step(step_index=<N>, status='done', notes='<brief result / generated [[IMG:...]] or file path>')` BEFORE moving to the next step.\n"
                            "- NEVER invent or summarize ungenerated files/images, and NEVER call `ACTION_PLANS__complete_plan` until ALL steps in the checklist are genuinely executed and marked `done`.\n"
                            "- Once every step is completed and verified, call `ACTION_PLANS__complete_plan(summary='<final summary>')` and present a clear summary (referencing only real created files/images).\n"
                        )
                    file_manager_rules += (
                        "\n### ▶️ ACTIVE ACTION PLAN TO EXECUTE ###\n"
                        f"{plan_blueprint}\n\n"
                        f"EXECUTION RULES FOR ACTIVE PLAN (`{active_plan.get('plan_id')}`):\n"
                        "- Do NOT call `ACTION_PLANS__create_plan` again — the plan above is already active.\n"
                        f"{step_scope_rules}"
                    )
                elif (
                    not is_fast_code_turn
                    and active_plan
                    and str(active_plan.get("status") or "").lower() in ("awaiting_approval", "draft")
                    and str(active_plan.get("plan_mode") or "").lower() == "plan_only"
                ):
                    pending_summary = get_action_plan_manager().format_plan_summary(active_plan)
                    file_manager_rules += (
                        "\n### 📋 PENDING ACTION PLAN AWAITING USER APPROVAL ###\n"
                        f"{pending_summary}\n"
                        "- If the user is requesting modifications, additions, or feedback on this pending plan, "
                        "do NOT execute it yet: call `ACTION_PLANS__revise_plan(...)` with the updated `plan_markdown`, `steps`, and `revision_note` and stop.\n"
                        "- If the user wants to start executing the approved plan, tell them they can select a Global Preset and click **Execute Plan** or **Next Step** (or send `/code`), unless they explicitly asked a separate unrelated question.\n"
                    )
                elif (
                    not is_fast_code_turn
                    and send_tools
                    and ap_cfg.get("enabled", True)
                    and ap_mode in ("auto", "confirm")
                    and (
                        _is_tag_allowed_in_prompt("ACTION_PLANS")
                        or ap_cfg.get("expose_tools_in_custom_presets", True)
                    )
                ):
                    min_hint = int(ap_cfg.get("auto_plan_min_steps_hint", 3) or 3)
                    user_directive = str(ap_cfg.get("planning_directive") or "").strip()
                    if user_directive:
                        resolved_directive = user_directive.replace("{min_steps}", str(min_hint))
                        file_manager_rules += (
                            "\n### ACTION PLANS (USER-CONFIGURED DIRECTIVE) ###\n"
                            f"{resolved_directive}\n"
                        )
            except Exception as e:
                logger.debug(f"PromptBuilder: Action Plan directive skipped: {e}")

            

        force_clause = (

            f"\n{translator.t('root_security_instruction')}\n"

            f"{translator.t('root_security_desc')}\n"

        )

        

        netsearch_protocol = ""

        # Only inject netsearch protocol if NETSEARCH module is active and selected for this prompt
        _netsearch_active = "NETSEARCH" in [t.upper() for t in _get_active_tags_safe()]

        if _is_tag_allowed_in_prompt("NETSEARCH") and _netsearch_active:
            try:
                from hecos.modules.net_search.search.config import get_ai_prompts_config
                _ns_ai_cfg = get_ai_prompts_config()
                if _ns_ai_cfg.get("enable_main_chat_protocol", True):
                    _raw_proto = str(_ns_ai_cfg.get("main_chat_protocol") or "").strip()
                    if _raw_proto:
                        netsearch_protocol = f"\n{_raw_proto}\n"
            except Exception:
                netsearch_protocol = ""

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

        if is_incognito:
            user_profile_block = (
                "\n### PRIVACY MODE: INCOGNITO ###\n"
                "- This is an anonymous zero-trace RAM session: user identity, profile, and long-term memory are withheld.\n"
                "- Do not claim to know the user's personal details or save personal information to persistent memory.\n"
            )
        else:
            try:

                profile = auth_mgr.get_profile(user_id)

                if profile:

                    user_profile_block = (

                        "\n### USER IDENTITY ###\n"

                        f"  - Username: {profile.get('username', user_id)}\n"

                        f"  - Display Name: {profile.get('display_name') or '[not provided]'}\n"

                        f"  - Preferred Language: {profile.get('preferred_language', 'it')}\n"

                        f"  - Role: {profile.get('role', 'admin')}\n"

                    )

                    if _is_tag_allowed_in_prompt("USERS"):

                        user_profile_block += (

                            "\n### USER DATA ACCESS ###\n"

                            "- To access full contact info (email, phone, address, bio), use [USERS: get_profile].\n"

                            "- To help the user update their data, use [USERS: update_profile:field=value].\n"

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

