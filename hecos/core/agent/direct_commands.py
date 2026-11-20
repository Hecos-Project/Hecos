import re
from hecos.core.logging import logger
from hecos.core.processing import processore
from hecos.core.agent.persona_vision import PersonaVision
from hecos.core.agent.traces import AgentTracer
from hecos.core.agent.trace_labeler import tr, format_args_preview

_PLAN_DIRECT_SUBCOMMANDS = frozenset({
    "show",
    "status",
    "list",
    "info",
    "help",
    "mode",
    "clear",
    "cancel",
    "reject",
    "reset",
    "close",
    "approve",
    "accept",
    "ok",
})

_CODE_DIRECT_SUBCOMMANDS = frozenset({"status", "help", "info"})


def _apply_coder_preset_to_agent(agent, preferred_preset_id: str = "") -> str:
    """Activate a Coder Global Preset for the active session and refresh `agent.config` in place."""
    try:
        from hecos.core.global_presets import activate_soul_for_session, resolve_coder_preset_id
        from hecos.config.session_config_manager import merge_session_config

        target_id = resolve_coder_preset_id(preferred_preset_id)
        sid = getattr(agent, "session_id", None) or "default"
        soul = activate_soul_for_session(target_id, sid)
        if soul and isinstance(getattr(agent, "config", None), dict):
            base_cfg = (
                getattr(getattr(agent, "config_manager", None), "_base", None).config
                if getattr(getattr(agent, "config_manager", None), "_base", None) is not None
                else agent.config
            )
            merged = merge_session_config(base_cfg, sid)
            agent.config.clear()
            agent.config.update(merged)
        return target_id
    except Exception as e:
        logger.warning(f"[CommandInterceptor] Could not switch session preset to Coder: {e}")
        return preferred_preset_id or "hecos_coder"


def _build_plan_execution_prompt(plan: dict, extra_notes: str = "") -> str:
    from hecos.core.action_plans import get_action_plan_manager

    blueprint = get_action_plan_manager().format_plan_blueprint_for_coder(plan, max_chars=4500)
    extra_block = f"\nAdditional user instructions: {extra_notes}\n" if extra_notes else ""
    return (
        f"Execute the active Implementation Plan '{plan.get('title')}' (ID: {plan.get('plan_id')}) step by step.\n\n"
        f"{blueprint}\n"
        f"{extra_block}\n"
        "EXECUTION INSTRUCTIONS:\n"
        "1. Do NOT call `ACTION_PLANS__create_plan` again — the plan above is already active.\n"
        "2. Follow the Architectural Blueprint specs above and execute each pending/running step sequentially using real `EXECUTOR__*` tools on disk.\n"
        "3. After completing EACH step, call `ACTION_PLANS__update_step(step_index=<N>, status='done', notes='...')`.\n"
        "4. Once all steps are verified on disk, call `ACTION_PLANS__complete_plan(summary='...')` and summarize the created/modified file:/// links."
    )


class CommandInterceptor:
    """
    Intercepts and executes global direct commands (e.g. /cmd), bypassing the LLM.
    Also handles Architect/Coder orchestration commands (/plan <task>, /code [run|coder|<task>])
    and prompt enrichment for visual commands (/img, /photo).
    """

    @staticmethod
    def _intercept_plan_or_code(cmd_verb: str, cmd_arg: str, cmd_step: dict, agent):
        """
        Handle `/plan` and `/code` (`/coder`, `/sviluppa`):
        - Returns `(True, markdown_output)` for direct management commands (`/plan show`, `/plan mode`, `/plan clear`, `/code status`).
        - Returns `(False, rewritten_user_text)` when launching an Architect (`_turn_plan_only`) or Coder (`_turn_execute_plan` / `_turn_fast_code`) LLM turn.
        - Returns `None` if `cmd_verb` is not a plan/code command.
        """
        verb_low = cmd_verb.lower()
        if verb_low not in ("/plan", "/piano", "/code", "/coder", "/sviluppa"):
            return None

        raw_arg = (cmd_arg or "").strip()
        parts = raw_arg.split(maxsplit=1) if raw_arg else []
        first_sub = parts[0].lower() if parts else ""
        sub_rest = parts[1].strip() if len(parts) > 1 else ""

        # ── 1. /plan ... ──────────────────────────────────────────────────────
        if verb_low in ("/plan", "/piano"):
            if not first_sub or first_sub in _PLAN_DIRECT_SUBCOMMANDS:
                return None  # Let standard HDCS executor run `_cmd_plan` directly

            if first_sub in ("run", "execute", "start", "esegui", "avvia", "coder"):
                # Delegate `/plan run` or `/plan coder` to the `/code` execution flow
                verb_low = "/coder" if first_sub == "coder" else "/code"
                raw_arg = sub_rest if first_sub != "coder" else f"coder {sub_rest}".strip()
                parts = raw_arg.split(maxsplit=1) if raw_arg else []
                first_sub = parts[0].lower() if parts else ""
                sub_rest = parts[1].strip() if len(parts) > 1 else ""
            elif first_sub in ("revise", "edit", "update", "modify", "modifica", "aggiorna", "revisiona"):
                from hecos.core.action_plans import get_action_plan_manager

                mgr = get_action_plan_manager()
                sid = getattr(agent, "session_id", None) or ""
                active_plan = mgr.resolve_plan(source_id=sid)
                if not active_plan or active_plan.get("status") in ("completed", "cancelled"):
                    msg = tr(
                        "ℹ️ Nessun Piano d'Azione attivo da revisionare in questa chat. Crea prima un piano con `/plan <richiesta>`.",
                        "ℹ️ No active Action Plan to revise in this chat. Create a plan first with `/plan <request>`.",
                    )
                    AgentTracer.finish_step(cmd_step, status="ok", result_preview=tr("Nessun piano attivo", "No active plan"))
                    return True, msg
                if not sub_rest:
                    msg = tr(
                        f"✏️ Specifica le modifiche da apportare al piano **`{active_plan.get('title')}`**.\n\nEsempio: `/plan revise Aggiungi autenticazione JWT e grafici Chart.js`",
                        f"✏️ Specify the changes to apply to plan **`{active_plan.get('title')}`**.\n\nExample: `/plan revise Add JWT authentication and Chart.js charts`",
                    )
                    AgentTracer.finish_step(cmd_step, status="ok", result_preview=tr("Feedback mancante", "Missing revision feedback"))
                    return True, msg

                target_pid = str(active_plan.get("plan_id") or "")
                if isinstance(getattr(agent, "config", None), dict):
                    agent.config["_turn_plan_only"] = True
                    agent.config["_turn_revise_plan_id"] = target_pid
                    agent.config.setdefault("payload_control", {})["send_tools"] = True
                try:
                    from hecos.core.agent.trace_session import get_active_session
                    sess = get_active_session()
                    if sess is not None and isinstance(getattr(sess, "config", None), dict):
                        sess.config["_turn_plan_only"] = True
                        sess.config["_turn_revise_plan_id"] = target_pid
                except Exception:
                    pass

                AgentTracer.finish_step(
                    cmd_step,
                    status="ok",
                    result_preview=tr(
                        f"Modalità Architetto (Revisione Piano): aggiornamento '{active_plan.get('title')}'",
                        f"Architect Mode (Plan Revision): updating '{active_plan.get('title')}'",
                    ),
                )
                return False, f"Revise the active Implementation Plan ({target_pid}) with these requested changes:\n\n{sub_rest}"
            else:
                # `/plan <task>` -> Architect / Plan-First LLM turn!
                if isinstance(getattr(agent, "config", None), dict):
                    agent.config["_turn_plan_only"] = True
                    agent.config.pop("_turn_revise_plan_id", None)
                    agent.config.setdefault("payload_control", {})["send_tools"] = True
                try:
                    from hecos.core.agent.trace_session import get_active_session
                    sess = get_active_session()
                    if sess is not None and isinstance(getattr(sess, "config", None), dict):
                        sess.config["_turn_plan_only"] = True
                        sess.config.pop("_turn_revise_plan_id", None)
                except Exception:
                    pass

                AgentTracer.finish_step(
                    cmd_step,
                    status="ok",
                    result_preview=tr(
                        "Modalità Architetto (Plan First): creazione piano senza modifica file",
                        "Architect Mode (Plan First): generating Action Plan without file edits",
                    ),
                )
                return False, raw_arg

        # ── 2. /code | /coder | /sviluppa ─────────────────────────────────────
        if first_sub in _CODE_DIRECT_SUBCOMMANDS:
            return None  # Let standard HDCS executor run `_cmd_code` directly

        use_coder_preset = (verb_low == "/coder")
        explicit_preset = ""
        rem_arg = raw_arg

        # Parse optional `--preset <id>`, `--coder`, or leading `coder`
        m_preset = re.match(r"^(?:--preset|-p)\s+([A-Za-z0-9_.-]+)(?:\s+(.*))?$", rem_arg, re.IGNORECASE | re.DOTALL)
        if m_preset:
            use_coder_preset = True
            explicit_preset = m_preset.group(1).strip()
            rem_arg = (m_preset.group(2) or "").strip()
        elif first_sub in ("coder", "--coder", "-c"):
            use_coder_preset = True
            rem_arg = sub_rest
        else:
            try:
                from hecos.core.global_presets import get_soul
                if first_sub and "coder" in first_sub and get_soul(first_sub) is not None:
                    use_coder_preset = True
                    explicit_preset = first_sub
                    rem_arg = sub_rest
            except Exception:
                pass

        activated_preset_id = ""
        if use_coder_preset:
            activated_preset_id = _apply_coder_preset_to_agent(agent, explicit_preset)

        rem_low = rem_arg.lower().strip()
        is_plan_run_intent = (not rem_low) or (rem_low in ("run", "execute", "start", "esegui", "avvia", "plan"))

        from hecos.core.action_plans import get_action_plan_manager
        mgr = get_action_plan_manager()
        sid = getattr(agent, "session_id", None) or ""
        active_plan = mgr.resolve_plan(source_id=sid)

        if is_plan_run_intent:
            if active_plan and active_plan.get("status") not in ("completed", "cancelled"):
                mgr.approve_plan(active_plan["plan_id"])
                fresh_plan = mgr.get_plan(plan_id=active_plan["plan_id"]) or active_plan
                if isinstance(getattr(agent, "config", None), dict):
                    agent.config["_turn_execute_plan"] = fresh_plan["plan_id"]
                    agent.config.pop("_turn_plan_only", None)
                    agent.config.setdefault("payload_control", {})["send_tools"] = True
                if hasattr(agent, "max_iterations"):
                    agent.max_iterations = max(int(getattr(agent, "max_iterations", 15) or 15), 25)

                preset_note = f" [{activated_preset_id}]" if activated_preset_id else ""
                AgentTracer.finish_step(
                    cmd_step,
                    status="ok",
                    result_preview=tr(
                        f"Avvio esecuzione piano '{fresh_plan.get('title')}'{preset_note}",
                        f"Starting execution of plan '{fresh_plan.get('title')}'{preset_note}",
                    ),
                )
                return False, _build_plan_execution_prompt(fresh_plan)

            # No active plan found: return helpful status via _cmd_code
            from hecos.core.commands.builtins.plan_commands import _cmd_code
            out = _cmd_code(
                raw_args_str=raw_arg,
                config=getattr(agent, "config", None),
                config_manager=getattr(agent, "config_manager", None),
                session_id=sid,
            )
            if activated_preset_id:
                out = f"✅ **Preset switched to `{activated_preset_id}`** for this chat session.\n\n" + out
            AgentTracer.finish_step(cmd_step, status="ok", result_preview=tr("Stato Coder", "Coder status"))
            return True, out

        # Direct fast-track coding instruction: `/code <instruction>`
        if isinstance(getattr(agent, "config", None), dict):
            agent.config["_turn_fast_code"] = True
            agent.config.pop("_turn_plan_only", None)
            agent.config.setdefault("payload_control", {})["send_tools"] = True
        if hasattr(agent, "max_iterations"):
            agent.max_iterations = max(int(getattr(agent, "max_iterations", 15) or 15), 25)

        preset_note = f" [{activated_preset_id}]" if activated_preset_id else ""
        AgentTracer.finish_step(
            cmd_step,
            status="ok",
            result_preview=tr(
                f"Modalità Fast-Track Code attiva{preset_note}",
                f"Fast-Track Code execution active{preset_note}",
            ),
        )
        return False, rem_arg

    @staticmethod
    def intercept(user_text, agent):
        """
        Returns (True, response) if a command was intercepted and executed directly.
        Returns (False, rewritten_user_text_or_None) if the turn should proceed to the LLM loop.
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
            plan_or_code = CommandInterceptor._intercept_plan_or_code(cmd_verb, cmd_arg, cmd_step, agent)
            if plan_or_code is not None:
                return plan_or_code

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
