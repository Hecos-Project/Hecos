import re
from hecos.core.logging import logger
from hecos.core.processing import processore
from hecos.core.agent.persona_vision import PersonaVision

class CommandInterceptor:
    """
    Intercepts and executes global direct commands (e.g. /cmd), bypassing the LLM.
    Also handles prompt enrichment for visual commands (/img, /photo).
    """
    
    @staticmethod
    def intercept(user_text, agent):
        """
        Returns (True, response) if a command was intercepted and executed.
        Returns (False, None) if no command was found.
        """
        testo_pulito = user_text.strip()
        if not testo_pulito.startswith("/"):
            return False, None
            
        try:
            agent._emit(f"Intercetto comando diretto: {testo_pulito.split()[0]}...", level="info")
            from hecos.core.commands.executor import get_executor
            executor = get_executor()
            
            # Check for persona image generation overrides (legacy support for /img)
            # If the user targets the bot visually, we enrich the prompt
            if testo_pulito.lower().startswith(("/img ", "/image ", "/photo ", "/foto ")):
                raw_prompt = testo_pulito.split(" ", 1)[1].strip() if " " in testo_pulito else ""
                clean_target = raw_prompt.lower()
                for unwanted in ["a photo of ", "a picture of ", "una foto di ", "un'immagine di ", "photo of ", "picture of "]:
                    clean_target = clean_target.replace(unwanted, "")
                    
                active_p = agent.config.get('ai', {}).get('active_personality', 'Hecos_System_Soul').replace('.yaml', '')
                persona_name_raw = active_p.replace('_', ' ').lower()
                persona_short = persona_name_raw.split(' ')[0]
                
                enrich_keywords = ["you", "yourself", "tua", "tuo", "tuoi", "tue", "te", "te stessa", "te stesso", persona_short, persona_name_raw]
                enrich_keywords = [k for k in enrich_keywords if k.strip()]
                pattern = r'\b(?:' + '|'.join(map(re.escape, enrich_keywords)) + r')\b'
                
                if re.search(pattern, raw_prompt.lower()):
                    visual_desc = PersonaVision.get_visual_description(agent.config)
                    if visual_desc:
                        agent._emit(f"Enriching prompt with persona YAML context: {persona_short}...", level="info")
                        target_action = re.sub(pattern, '', clean_target, flags=re.IGNORECASE)
                        target_action = re.sub(r'^\s*[,.]\s*', '', target_action).strip()
                        prompt_bypass = f"A photo of {visual_desc}, {target_action}" if target_action else f"A photo of {visual_desc}"
                        # Re-write the command string
                        cmd_part = testo_pulito.split()[0]
                        testo_pulito = f"{cmd_part} {prompt_bypass}"

            res = executor.execute(
                raw_input=testo_pulito,
                config=agent.config,
                config_manager=agent.config_manager,
                current_user_role=agent.current_user_role,
                current_user_id=agent.current_user_id,
                session_id=agent.session_id,
                sender_tab_id=agent.sender_tab_id,
                page_context="chat"
            )
            
            if not res.get("ok"):
                agent._emit(f"Command Error: {res.get('error')}", level="error")
            else:
                agent._emit(f"Direct command executed successfully.", level="success")
                
            return True, res["output"]
            
        except Exception as e:
            logger.error(f"[CommandInterceptor] Direct Command Bypass Error: {e}", exc_info=True)
            err_msg = f"❌ Error: {e}"
            return True, err_msg
