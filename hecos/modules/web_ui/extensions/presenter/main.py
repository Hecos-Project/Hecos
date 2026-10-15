import os
from flask import send_from_directory, request, jsonify
from hecos.core.logging import logger
from .config.store import load_presenter_config

def init_routes(app, root_dir: str = None):
    logger.info("[Presenter] Initializing routes...")
    cfg = load_presenter_config()

    # One-time migration from the old monolithic presenter_feed.jsonl
    try:
        from .feed import migrate_legacy_feed
        migrate_legacy_feed()
    except Exception as _mig_err:
        logger.warning(f"[Presenter] Legacy feed migration skipped: {_mig_err}")

    if not getattr(cfg, 'enabled', True):
        logger.info("[Presenter] Module is disabled in configuration.")
    else:
        from .engine import get_engine
        get_engine().start()
    
    _static_dir = os.path.join(os.path.dirname(__file__), "static")
    @app.route("/ext/presenter/static/<path:filename>")
    def presenter_static(filename):
        return send_from_directory(_static_dir, filename)

    @app.route("/api/ext/presenter/config", methods=["GET"])
    def get_presenter_config():
        from .config.store import load_presenter_config
        cfg = load_presenter_config()
        return jsonify({"ok": True, "config": cfg.model_dump()})

    @app.route("/api/ext/presenter/config", methods=["POST"])
    def post_presenter_config():
        try:
            from .config.store import load_presenter_config, save_presenter_config
            
            data = request.json or {}
            cfg = load_presenter_config()
            
            if 'enabled' in data: cfg.enabled = data['enabled']
            if 'allow_commands' in data: cfg.allow_commands = data['allow_commands']
            if 'panel_default' in data: cfg.panel_default = data['panel_default']
            if 'live_commentary' in data: cfg.live_commentary = data['live_commentary']
            if 'commentary_on_messages' in data: cfg.commentary_on_messages = data['commentary_on_messages']
            if 'verbosity' in data: cfg.verbosity = data['verbosity']
            if 'briefing_on_new_chat' in data: cfg.briefing_on_new_chat = data['briefing_on_new_chat']
            
            if 'voice' in data:
                v = data['voice']
                if 'preset_id' in v: cfg.voice.preset_id = v['preset_id']
                if 'max_tokens' in v: cfg.voice.max_tokens = v['max_tokens']
                
            save_presenter_config(cfg)
            
            from .engine import get_engine
            if cfg.enabled:
                get_engine().start()
            
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[Presenter] Error saving config: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/ext/presenter/test", methods=["POST"])
    def test_presenter():
        """Manual trigger for testing."""
        try:
            from .engine import get_engine
            from .feed import add_feed_entry
            from hecos.core.events import emit

            engine = get_engine()
            cfg = engine.cfg
            session_id = (request.json or {}).get("session_id")

            logger.info(f"[Presenter] TEST: enabled={cfg.enabled}, live_commentary={cfg.live_commentary}, preset_id={cfg.voice.preset_id}")
            logger.info(f"[Presenter] TEST: engine._running={engine._running}")

            add_feed_entry("test", "This is a direct test message from the Presenter.",
                           session_id=session_id, persist=cfg.feed.persist)
            emit("persona_switched", {"new_persona": "Test Persona"})
            logger.info("[Presenter] TEST: persona_switched event emitted.")

            return jsonify({"ok": True, "message": "Test triggered. Check chat for output.", "config": {
                "enabled": cfg.enabled,
                "live_commentary": cfg.live_commentary,
                "preset_id": cfg.voice.preset_id,
                "running": engine._running,
            }})
        except Exception as e:
            logger.error(f"[Presenter] TEST error: {e}")
            import traceback
            return jsonify({"ok": False, "error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route("/api/ext/presenter/briefing", methods=["GET"])
    def get_briefing():
        """System briefing: checks port, backend, Ollama, CDP, active persona."""
        items = []
        
        # Use the same config loading as the engine
        try:
            from hecos.core.llm.brain import load_config
            config = load_config() or {}
        except Exception as e:
            logger.warning(f"[Presenter] Briefing: could not load config via brain: {e}")
            try:
                import sys
                cfg_mgr = getattr(sys, 'hecos_config_manager', None)
                config = cfg_mgr.config if cfg_mgr else {}
            except Exception:
                config = {}

        # 1. Server port
        try:
            port = config.get("plugins", {}).get("WEB_UI", {}).get("port", 7070)
            items.append({"type": "system_info", "text": f"Hecos active on port {port}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing port error: {e}")

        # 2. Backend type & model
        try:
            backend_type = config.get("backend", {}).get("type", "ollama")
            model = config.get("backend", {}).get(backend_type, {}).get("model", "unknown")
            items.append({"type": "system_status", "text": f"Backend: {backend_type} · Model: {model}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing backend error: {e}")

        # 3. Ollama check
        try:
            backend_type = config.get("backend", {}).get("type", "ollama")
            if backend_type == "ollama":
                try:
                    import requests as _req
                    r = _req.get("http://localhost:11434/api/tags", timeout=2)
                    if r.status_code == 200:
                        models = r.json().get("models", [])
                        items.append({"type": "system_status", "text": f"Ollama online — {len(models)} models available"})
                    else:
                        items.append({"type": "system_warning", "text": "Ollama responded with an error"})
                except Exception:
                    items.append({"type": "system_warning", "text": "Ollama unreachable on localhost:11434"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing Ollama error: {e}")

        # 4. CDP Mode
        try:
            import socket
            def _is_port_open(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('127.0.0.1', port)) == 0

            cdp_port = int(config.get("plugins", {}).get("CDP", {}).get("port", 9222))
            
            if _is_port_open(cdp_port):
                items.append({"type": "system_status", "text": f"TCP Protocol: Active — Port {cdp_port} connected (CDP Mode)"})
            else:
                items.append({"type": "system_warning", "text": f"TCP/CDP Mode inactive. Browser automations disabled."})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing CDP error: {e}")

        # 5. Active Global Soul
        try:
            persona = config.get("ai", {}).get("active_personality", "")
            if persona and persona not in ("", "default"):
                persona_name = persona.replace(".yaml", "").replace("_", " ").title()
                items.append({"type": "system_info", "text": f"Active Global Soul: {persona_name}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing persona error: {e}")

        # 6. Presenter Global Preset & Presenter Soul
        try:
            p_cfg = load_presenter_config()
            if p_cfg.voice.preset_id:
                from hecos.core.global_presets.manager import get_soul
                soul = get_soul(p_cfg.voice.preset_id)
                if soul:
                    items.append({"type": "system_info", "text": f"Presenter Global Preset: {soul.meta.name}"})
                    p_soul = soul.persona.soul_file if (soul.persona and soul.persona.soul_file) else ""
                    if p_soul:
                        p_soul_name = p_soul.replace(".yaml", "").replace("_", " ").title()
                        items.append({"type": "system_info", "text": f"Presenter Soul: {p_soul_name}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing preset error: {e}")

        # 6b. Playbook Engine Status & Active Playbook Details
        try:
            from hecos.modules.playbooks.playbooks import storage as pb_storage
            all_pbs = pb_storage.list_playbooks()
            if all_pbs:
                active_pbs = [p for p in all_pbs if p.get("meta", {}).get("enabled")]
                if active_pbs:
                    for pb in active_pbs:
                        meta = pb.get("meta", {})
                        pb_name = meta.get("name", "Untitled Playbook")
                        pb_mode = (meta.get("mode") or pb.get("mode") or "training").capitalize()
                        tabs = pb.get("tabs", [])
                        enabled_tabs = [t for t in tabs if t.get("enabled", True)]
                        
                        items.append({
                            "type": "system_status",
                            "text": f"Playbook active: <strong>{pb_name}</strong> ({pb_mode} mode) — {len(enabled_tabs)} of {len(tabs)} tabs enabled"
                        })
                        
                        if enabled_tabs:
                            tab_targets = []
                            for t in enabled_tabs:
                                t_name = t.get("name", "Tab")
                                t_tgt = (t.get("target") or "presenter").upper()
                                tab_targets.append(f"{t_name} [{t_tgt}]")
                            targets_str = "  •  ".join(tab_targets)
                            items.append({
                                "type": "system_info",
                                "text": f"Playbook Targets: {targets_str}"
                            })
                else:
                    items.append({
                        "type": "system_info",
                        "text": f"Playbooks: {len(all_pbs)} installed, currently inactive (none enabled)"
                    })
        except Exception as e:
            logger.debug(f"[Presenter] Briefing Playbooks error: {e}")

        # 7. Tips
        hdcs_key_display = "Ctrl + Space"
        try:
            from hecos.modules.web_ui.routes_shortcuts import _load_user_shortcuts
            from flask_login import current_user
            username = current_user.username if hasattr(current_user, 'username') else "admin"
            actual_root = root_dir if root_dir else os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            user_shortcuts = _load_user_shortcuts(actual_root, username)
            hdcs_key = user_shortcuts["bindings"].get("ui.open_hdcs", "ctrl+space")
            hdcs_key_display = hdcs_key.replace("+", " + ").title()
        except Exception as e:
            logger.debug(f"[Presenter] Could not load shortcut for tip: {e}")

        items.append({"type": "tip", "text": f"Type / in chat or press {hdcs_key_display} to open the Command Palette (HDCS)"})

        logger.info(f"[Presenter] Briefing generated {len(items)} items")
        return jsonify({"ok": True, "items": items})

    @app.route("/api/ext/presenter/playbook_status", methods=["GET"])
    def get_playbook_status():
        """Returns the active playbook summary and tab targets for Presenter header pill & notifications."""
        try:
            from hecos.modules.playbooks.playbooks import storage as pb_storage
            all_pbs = pb_storage.list_playbooks()
            active_pbs = [p for p in all_pbs if p.get("meta", {}).get("enabled")]
            
            active_info = None
            if active_pbs:
                first = active_pbs[0]
                meta = first.get("meta", {})
                tabs = first.get("tabs", [])
                enabled_tabs = [t for t in tabs if t.get("enabled", True)]
                active_info = {
                    "id": meta.get("id"),
                    "name": meta.get("name", "Untitled Playbook"),
                    "icon": meta.get("icon", "fa-book-open"),
                    "mode": meta.get("mode") or first.get("mode") or "training",
                    "total_tabs": len(tabs),
                    "enabled_tabs": len(enabled_tabs),
                    "tabs": [
                        {
                            "id": t.get("id"),
                            "name": t.get("name"),
                            "target": t.get("target", "presenter"),
                            "enabled": t.get("enabled", True)
                        }
                        for t in tabs
                    ]
                }
            
            chat_id = request.args.get("chat_id", "default")
            sim_state = pb_storage.get_simulation_state(chat_id)
            if active_info and active_info.get("id"):
                active_pb = next((p for p in active_pbs if p.get("meta", {}).get("id") == active_info["id"]), None)
                if active_pb:
                    m = active_pb.get("mission", {})
                    active_info["mission"] = m
                    raw_user_role = m.get("user_role", "User")
                    raw_chat_role = m.get("chat_role", "Interlocutor")
                    if isinstance(raw_user_role, dict):
                        raw_user_role = raw_user_role.get("role") or raw_user_role.get("name") or "User"
                    if isinstance(raw_chat_role, dict):
                        raw_chat_role = raw_chat_role.get("role") or raw_chat_role.get("name") or "Interlocutor"
                    coach_role = m.get("coach_role", "Coach")
                    if isinstance(coach_role, dict):
                        coach_role = coach_role.get("role") or coach_role.get("name") or "Coach"

                    is_swapped = sim_state.get("swapped", False)
                    eff_user = raw_chat_role if is_swapped else raw_user_role
                    eff_chat = raw_user_role if is_swapped else raw_chat_role

                    sim_state["user_role"] = eff_user
                    sim_state["chat_role"] = eff_chat
                    sim_state["raw_user_role"] = raw_user_role
                    sim_state["raw_chat_role"] = raw_chat_role
                    sim_state["coach_role"] = coach_role
                    sim_state["swapped"] = is_swapped

                    active_info["effective_user_role"] = eff_user
                    active_info["effective_chat_role"] = eff_chat
                    active_info["coach_role"] = coach_role

            return jsonify({
                "ok": True,
                "installed": len(all_pbs) > 0,
                "total_installed": len(all_pbs),
                "has_active": active_info is not None,
                "active_playbook": active_info,
                "simulation": sim_state
            })
        except ImportError:
            return jsonify({"ok": True, "installed": False, "has_active": False, "active_playbook": None, "simulation": {"status": "idle"}})
        except Exception as e:
            logger.error(f"[Presenter] Playbook status error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/ext/presenter/feed", methods=["GET"])
    def get_feed():
        """Returns recent feed entries for the given chat session.

        Query params:
            chat_id (str): The session ID whose feed to return.
            limit   (int): Maximum number of entries (default 30).
        """
        try:
            from .feed import get_feed_entries
            session_id = request.args.get("chat_id") or None
            limit = request.args.get("limit", 30, type=int)
            entries = get_feed_entries(session_id=session_id, limit=limit)
            return jsonify({"ok": True, "entries": entries})
        except Exception as e:
            logger.error(f"[Presenter] Feed read error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/ext/presenter/simulation/<action>", methods=["GET", "POST"])
    def presenter_simulation_action(action):
        """Controls live playbook simulation: start, stop, pause, swap, roles, check, status."""
        try:
            from hecos.modules.playbooks.playbooks import storage as pb_storage
            from .feed import add_feed_entry

            data = request.get_json(silent=True) or {}
            chat_id = data.get("chat_id") or request.args.get("chat_id") or "default"
            active_pbs = [p for p in pb_storage.list_playbooks() if p.get("meta", {}).get("enabled")]
            active_pb = active_pbs[0] if active_pbs else None
            pb_id = data.get("playbook_id") or (active_pb.get("meta", {}).get("id") if active_pb else None)

            if action in ("start", "run", "play"):
                if not active_pb:
                    return jsonify({"ok": False, "error": "No active playbook found"}), 400
                sim_state = pb_storage.start_simulation(chat_id, pb_id)
                m = active_pb.get("mission", {})
                raw_u = m.get("user_role", "User")
                raw_c = m.get("chat_role", "Interlocutor")
                coach_role = m.get("coach_role", "Coach")
                is_swapped = sim_state.get("swapped", False)
                eff_u = raw_c if is_swapped else raw_u
                eff_c = raw_u if is_swapped else raw_c
                sim_state["user_role"] = eff_u
                sim_state["chat_role"] = eff_c
                sim_state["raw_user_role"] = raw_u
                sim_state["raw_chat_role"] = raw_c
                sim_state["coach_role"] = coach_role
                swap_txt = " (⇄ SWAPPED)" if is_swapped else ""
                add_feed_entry("playbook_event", f"▶ Simulation STARTED{swap_txt} — User: {eff_u} · Chat: {eff_c} · Coach: {coach_role}", session_id=chat_id)
                tabs_str = " • ".join(f"{t.get('name')} [{(t.get('target') or 'presenter').upper()}]" for t in active_pb.get("tabs", []) if t.get("enabled", True))
                if tabs_str:
                    add_feed_entry("playbook_event", f"🎯 Playbook Targets: {tabs_str}", session_id=chat_id)
                return jsonify({"ok": True, "action": action, "simulation": sim_state})

            elif action in ("stop", "end", "quit"):
                sim_state = pb_storage.stop_simulation(chat_id)
                add_feed_entry("playbook_event", "⏹ Simulation STOPPED — Playbook returned to idle knowledge mode.", session_id=chat_id)
                return jsonify({"ok": True, "action": action, "simulation": sim_state})

            elif action in ("pause", "freeze"):
                sim_state = pb_storage.pause_simulation(chat_id)
                add_feed_entry("playbook_event", "⏸ Simulation PAUSED.", session_id=chat_id)
                return jsonify({"ok": True, "action": action, "simulation": sim_state})

            elif action in ("swap", "invert"):
                sim_state = pb_storage.swap_roles(chat_id)
                pb = pb_storage.get_playbook(sim_state.get("playbook_id", "")) if sim_state.get("playbook_id") else active_pb
                m = pb.get("mission", {}) if pb else {}
                raw_u = m.get("user_role", "User")
                raw_c = m.get("chat_role", "Interlocutor")
                if isinstance(raw_u, dict): raw_u = raw_u.get("role") or raw_u.get("name") or "User"
                if isinstance(raw_c, dict): raw_c = raw_c.get("role") or raw_c.get("name") or "Interlocutor"
                swapped = sim_state.get("swapped", False)
                u_role = raw_c if swapped else raw_u
                c_role = raw_u if swapped else raw_c
                sim_state["user_role"] = u_role
                sim_state["chat_role"] = c_role
                sim_state["raw_user_role"] = raw_u
                sim_state["raw_chat_role"] = raw_c
                sim_state["swapped"] = swapped
                add_feed_entry("playbook_event", f"⇄ Roles SWAPPED — You: '{u_role}' · Chat AI: '{c_role}'", session_id=chat_id)
                return jsonify({"ok": True, "action": action, "simulation": sim_state})

            elif action == "roles":
                user_role = data.get("user_role")
                chat_role = data.get("chat_role")
                coach_role = data.get("coach_role")
                target_pid = pb_id or (active_pb.get("meta", {}).get("id") if active_pb else None)
                if target_pid:
                    mission_update = {}
                    if user_role is not None: mission_update["user_role"] = user_role
                    if chat_role is not None: mission_update["chat_role"] = chat_role
                    if coach_role is not None: mission_update["coach_role"] = coach_role
                    pb_storage.update_playbook(target_pid, mission=mission_update)
                    active_pb = pb_storage.get_playbook(target_pid)
                
                sim_state = pb_storage.get_simulation_state(chat_id)
                m = (active_pb.get("mission", {}) if active_pb else {})
                raw_u = m.get("user_role", user_role or "User")
                raw_c = m.get("chat_role", chat_role or "Interlocutor")
                if isinstance(raw_u, dict): raw_u = raw_u.get("role") or raw_u.get("name") or "User"
                if isinstance(raw_c, dict): raw_c = raw_c.get("role") or raw_c.get("name") or "Interlocutor"
                swapped = sim_state.get("swapped", False)
                eff_user = raw_c if swapped else raw_u
                eff_chat = raw_u if swapped else raw_c
                sim_state["user_role"] = eff_user
                sim_state["chat_role"] = eff_chat
                sim_state["raw_user_role"] = raw_u
                sim_state["raw_chat_role"] = raw_c
                if coach_role: sim_state["coach_role"] = coach_role
                
                add_feed_entry("playbook_event", f"🎭 Roles UPDATED — You: '{eff_user}' · Chat AI: '{eff_chat}'", session_id=chat_id)
                return jsonify({"ok": True, "action": "roles", "simulation": sim_state})

            elif action == "check":
                message = data.get("message", "")
                violations = pb_storage.check_forbidden_terms(message, pb_id)
                return jsonify({"ok": True, "violations": violations, "has_violations": len(violations) > 0})

            elif action == "status":
                sim_state = pb_storage.get_simulation_state(chat_id)
                return jsonify({"ok": True, "simulation": sim_state})

            return jsonify({"ok": False, "error": f"Unknown action: {action}"}), 400
        except Exception as e:
            logger.error(f"[Presenter] Simulation action error ({action}): {e}")
            return jsonify({"ok": False, "error": str(e)}), 500


