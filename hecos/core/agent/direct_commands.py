import re
from hecos.core.logging import logger
from hecos.core.processing import processore
from hecos.core.agent.persona_vision import PersonaVision
from hecos.core.agent.traces import AgentTracer
from hecos.core.agent.trace_labeler import tr, format_args_preview


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

        cmd_verb = testo_pulito.split()[0]
        cmd_arg = testo_pulito[len(cmd_verb):].strip()
        cmd_step = AgentTracer.start_step(
            kind="command",
            label=tr(f"Comando Diretto · {cmd_verb}", f"Direct Command · {cmd_verb}"),
            args_preview=format_args_preview(cmd_arg, 60) if cmd_arg else "",
            icon="fa-bolt",
            level="tool",
            module_name=tr("Comando Diretto", "Direct Command"),
        )

        try:
            from hecos.core.commands.executor import get_executor
            executor = get_executor()

            # Check for persona image generation overrides (legacy support for /img)
            # If the user targets the bot visually, we enrich the prompt
            if testo_pulito.lower().startswith(("/img ", "/image ", "/photo ", "/foto ")):
                raw_prompt = testo_pulito.split(" ", 1)[1].strip() if " " in testo_pulito else ""
                clean_target = raw_prompt.lower()
                for unwanted in ["a photo of ", "a picture of ", "una foto di ", "un'immagine di ", "photo of ", "picture of "]:
                    clean_target = clean_target.replace(unwanted, "")

                raw_p = (agent.config.get('ai') or {}).get('active_personality') or (agent.config.get('persona') or {}).get('soul_file') or 'Hecos_System_Soul'
                active_p = raw_p.replace('.yaml', '').strip() if isinstance(raw_p, str) and raw_p.strip() else 'Hecos_System_Soul'
                persona_name_raw = active_p.replace('_', ' ').lower()
                persona_short = persona_name_raw.split(' ')[0]

                enrich_keywords = ["you", "yourself", "tua", "tuo", "tuoi", "tue", "te", "te stessa", "te stesso", persona_short, persona_name_raw]
                enrich_keywords = [k for k in enrich_keywords if k.strip()]
                pattern = r'\b(?:' + '|'.join(map(re.escape, enrich_keywords)) + r')\b'

                if re.search(pattern, raw_prompt.lower()):
                    visual_desc = PersonaVision.get_visual_description(agent.config)
                    if visual_desc:
                        AgentTracer.progress(
                            tr(
                                f"Arricchimento prompt con profilo visivo ({persona_short})",
                                f"Enriching prompt with persona visual profile ({persona_short})",
                            ),
                            level="info",
                        )
                        target_action = re.sub(pattern, '', clean_target, flags=re.IGNORECASE)
                        target_action = re.sub(r'^\s*[,.]\s*', '', target_action).strip()
                        prompt_bypass = f"A photo of {visual_desc}, {target_action}" if target_action else f"A photo of {visual_desc}"
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
                err_txt = str(res.get("error") or tr("Errore comando", "Command error"))
                AgentTracer.finish_step(cmd_step, status="error", result_preview=err_txt)
            else:
                AgentTracer.finish_step(
                    cmd_step,
                    status="ok",
                    result_preview=tr("Comando eseguito", "Command executed"),
                )

            return True, res["output"]

        except Exception as e:
            logger.error(f"[CommandInterceptor] Direct Command Bypass Error: {e}", exc_info=True)
            err_msg = f"❌ Error: {e}"
            AgentTracer.finish_step(cmd_step, status="error", result_preview=str(e))
            return True, err_msg
