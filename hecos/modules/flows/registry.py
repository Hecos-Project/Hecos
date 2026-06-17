"""
Hecos Flows — Action Registry
==============================
Central catalog of all actions available inside a Flow pipeline.

Usage:
    from hecos.modules.flows.registry import register_action, get_catalog, execute_action

To register an action from any module:
    @register_action(
        name="AUDIO__speak",
        description="Make Hecos speak a message aloud via TTS.",
        params={"text": "string"},
    )
    def _speak(text: str): ...

The engine calls execute_action("AUDIO__speak", {"text": "..."}) at runtime.
"""

from typing import Any, Callable, Dict, List, Optional
from hecos.core.logging import logger

class FlowLogger:
    def info(self, msg): logger.info("FLOWS", msg)
    def error(self, msg): logger.error("FLOWS", msg)
    def warning(self, msg): logger.debug("FLOWS", f"[WARN] {msg}")
    def debug(self, msg): logger.debug("FLOWS", msg)

log = FlowLogger()

# ── Internal store ─────────────────────────────────────────────────────────────

_REGISTRY: Dict[str, Dict[str, Any]] = {}


# ── Decorator ──────────────────────────────────────────────────────────────────

def register_action(
    name: str,
    description: str = "",
    params: Optional[Dict[str, str]] = None,
    category: str = "GENERAL",
    icon: str = "⚡",
):
    """
    Decorator to register a Python callable as a Hecos Flow action.

    Args:
        name:        Unique action identifier in MODULE__method format (e.g. AUDIO__speak).
        description: Human-readable description shown in the canvas & YAML autocompletion.
        params:      Dict of {param_name: type_hint_string} for documentation purposes.
        category:    Visual grouping in the node palette (e.g. "AUDIO", "LOGIC", "MAIL").
        icon:        Emoji icon shown on the node card.
    """
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[name] = {
            "name":        name,
            "description": description,
            "params":      params or {},
            "category":    category,
            "icon":        icon,
            "fn":          fn,
        }
        log.debug(f"[Flows.Registry] Registered action: {name}")
        return fn
    return decorator


# ── Bootstrap built-in LOGIC actions ──────────────────────────────────────────

def _bootstrap_builtin_actions():
    """Register the core logic nodes that the engine handles natively."""

    builtin = [
        {
            "name": "LOGIC__if_else",
            "description": "Evaluates a Jinja2 logical expression and branches to true_branch or false_branch.",
            "params": {
                "condition":    "string (Jinja2 logical expression — use the Logic Builder above)",
                "true_branch":  "dict (action + params to run if condition is True)",
                "false_branch": "dict (action + params to run if condition is False)",
            },
            "category": "LOGIC",
            "icon": "🔀",
        },
        {
            "name": "LOGIC__switch",
            "description": "Routes execution to the branch whose key matches the evaluated expression value.",
            "params": {
                "expression": "string (Jinja2 expression that evaluates to a string key)",
                "branches":   "dict (key → action definition)",
                "default":    "dict (optional fallback action)",
            },
            "category": "LOGIC",
            "icon": "🔀",
        },
        {
            "name": "LOGIC__loop",
            "description": "Iterates over a list variable and executes the body action for each item.",
            "params": {
                "over":   "string (Jinja2 reference to a list variable, e.g. '{{ items }}')",
                "as_var": "string (loop variable name, e.g. 'item')",
                "body":   "dict (action + params executed on each iteration)",
            },
            "category": "LOGIC",
            "icon": "🔁",
        },
        {
            "name": "CONTROL__start",
            "description": "Explicit entry point for the flow. Flows containing this node will only execute nodes connected to it.",
            "params": {"priority": "integer"},
            "category": "LOGIC",
            "icon": "▶️",
        },
        {
            "name": "LOGIC__delay",
            "description": "Waits for the specified number of seconds before proceeding.",
            "params": {"seconds": "number"},
            "category": "LOGIC",
            "icon": "⏱️",
        },
        {
            "name": "LOGIC__set_variable",
            "description": "Sets or updates a flow-scoped variable. ⚠️ The 'name' field acts as the variable output name.",
            "params": {
                "name":  "string (Variable Name - REQUIRED, e.g. score)",
                "value": "any (Static value or Jinja2 expression, e.g. '{{ input_data }}')",
            },
            "category": "LOGIC",
            "icon": "📌",
        },
        {
            "name": "LOGIC__template",
            "description": "Renders a Jinja2 template string using flow variables and stores the result.",
            "params": {
                "template":  "string (Jinja2 template)",
                "output_as": "string (variable name to store result in)",
            },
            "category": "LOGIC",
            "icon": "📝",
        },
        {
            "name": "LOGIC__and_gate",
            "description": "Proceeds only if ALL listed conditions (Jinja2 boolean expressions) are True.",
            "params": {
                "conditions": "list[string] (Jinja2 boolean expressions)",
                "on_success": "dict (action to run if all conditions pass)",
                "on_fail":    "dict (optional action to run if any condition fails)",
            },
            "category": "LOGIC",
            "icon": "🔒",
        },
        {
            "name": "LOGIC__or_gate",
            "description": "Proceeds if AT LEAST ONE condition (Jinja2 boolean expression) is True.",
            "params": {
                "conditions": "list[string] (Jinja2 boolean expressions)",
                "on_success": "dict (action to run if any condition passes)",
                "on_fail":    "dict (optional action to run if all conditions fail)",
            },
            "category": "LOGIC",
            "icon": "🔓",
        },
        {
            "name": "LOGIC__http_request",
            "description": "Makes an HTTP request and stores the JSON response as a flow variable.",
            "params": {
                "method":    "string (GET, POST, PUT, DELETE)",
                "url":       "string (target URL, supports Jinja2)",
                "headers":   "dict (optional headers)",
                "body":      "dict|string (optional request body for POST/PUT)",
                "output_as": "string (variable name to store parsed JSON response)",
            },
            "category": "LOGIC",
            "icon": "🌐",
        },
        {
            "name": "LOGIC__abort",
            "description": "Immediately aborts the current flow execution.",
            "params": {
                "reason": "string (optional reason to log)"
            },
            "category": "LOGIC",
            "icon": "🛑",
        },
        {
            "name": "TRIGGER__cron",
            "description": "Schedules the flow using a cron expression (e.g. '0 7 * * *' = daily at 07:00).",
            "params": {"expression": "string (cron expression)"},
            "category": "TRIGGER",
            "icon": "🕐",
        },
        {
            "name": "TRIGGER__interval",
            "description": "Runs the flow every N seconds/minutes/hours.",
            "params": {
                "every":  "integer",
                "unit":   "string (seconds | minutes | hours)",
            },
            "category": "TRIGGER",
            "icon": "🔄",
        },
        {
            "name": "TRIGGER__manual",
            "description": "Flow runs only when explicitly triggered by the user or the FLOWS__run_flow command.",
            "params": {},
            "category": "TRIGGER",
            "icon": "▶️",
        },
    ]

    for action in builtin:
        _REGISTRY[action["name"]] = {
            "name":        action["name"],
            "description": action["description"],
            "params":      action["params"],
            "category":    action["category"],
            "icon":        action["icon"],
            "fn":          None,   # handled natively by the engine
        }


_bootstrap_builtin_actions()


def _flows_run_flow(flow_id: str, wait: bool = True, pass_context: bool = True, cascade_stop: bool = True, **kwargs):
    try:
        from hecos.modules.flows.storage import get_flow
        from hecos.modules.flows.engine import run_flow, is_run_aborted, register_child_run
        import time
        import uuid

        target_flow = get_flow(flow_id)
        if not target_flow:
            log.error(f"FLOWS__run_flow: Flow '{flow_id}' not found.")
            return False

        if pass_context:
            target_flow["variables"] = {**(target_flow.get("variables") or {}), **kwargs}

        sub_run_id = f"sub_{uuid.uuid4().hex[:8]}"
        parent_run_id = kwargs.get("_run_id")

        # Register the child so abort_run() on the parent cascades to it
        if cascade_stop and parent_run_id:
            register_child_run(parent_run_id, sub_run_id)

        if wait:
            # Run synchronously
            run_flow(target_flow, run_id=sub_run_id)
            return True
        else:
            # Run asynchronously in a daemon thread
            import threading
            t = threading.Thread(target=run_flow, args=(target_flow, sub_run_id), daemon=True)
            t.start()
            return True

    except Exception as e:
        log.error(f"Cannot run flow {flow_id}: {e}")
        return False

_REGISTRY["FLOWS__run_flow"] = {
    "name": "FLOWS__run_flow",
    "description": "Executes another flow as a sub-flow. cascade_stop ensures stopping the parent also stops this sub-flow.",
    "params": {
        "flow_id":      "string (ID of the target flow to run)",
        "wait":         "boolean (true=wait for sub-flow to finish before proceeding)",
        "pass_context": "boolean (true=pass current variables to the sub-flow)",
        "cascade_stop": "boolean (true=stopping the parent also stops this sub-flow — default: true)",
    },
    "category": "FLOWS",
    "icon": "🔄",
    "fn": _flows_run_flow,
}


# ── USER__ask_input ────────────────────────────────────────────────────────────

def _user_ask_input(
    prompt: str = "Please respond:",
    speak: bool = True,
    intercept_mode: str = "auto",   # "auto" | "explicit" | "api_only"
    multi_run_priority: str = "first",  # "first" | "all"
    **kwargs
):
    """
    Pauses the flow and waits for a user response via chat or voice.

    intercept_mode:
      - "auto"      → any chat message while this run is waiting is treated as the answer
      - "explicit"  → user must prefix with @flow (e.g. "@flow yes")
      - "api_only"  → only /api/flows/<run_id>/input endpoint counts (manual or programmatic)

    multi_run_priority:
      - "first"  → if multiple flows are waiting, the oldest (first) one gets the reply
      - "all"    → broadcast the same reply to all waiting flows simultaneously
    """
    import time

    run_id = kwargs.get("_run_id", "unknown")
    timeout_seconds = int(kwargs.get("_timeout_seconds", 0))
    start_time = kwargs.get("_start_time", time.time())

    try:
        from hecos.modules.flows.engine import (
            register_pending_input,
            get_pending_input_value,
            is_run_aborted,
            get_event_bus,
        )

        # 1. Post the prompt to chat
        try:
            from hecos.memory.brain_interface import save_message
            save_message(
                role="assistant",
                message=prompt,
                user_id="admin",
                session_id=None,
                persona_name="Flows",
                broadcast_sse=True,
            )
        except Exception as e:
            log.warning(f"[USER__ask_input] Could not write to chat: {e}")

        # 2. Speak aloud if requested
        if speak:
            try:
                from hecos.core.audio import voice
                voice.speak(prompt)
            except Exception as e:
                log.warning(f"[USER__ask_input] TTS failed: {e}")

        # 3. Register this run as waiting for input + emit SSE event
        event = register_pending_input(
            run_id,
            kwargs.get("_flow_id", "unknown"),
            intercept_mode=intercept_mode,
            multi_run_priority=multi_run_priority
        )
        bus = get_event_bus()
        bus.emit(run_id, {
            "type":           "step_waiting_input",
            "run_id":         run_id,
            "prompt":         prompt,
            "intercept_mode": intercept_mode,
            "ts":             __import__("datetime").datetime.now().isoformat(),
        })

        # 4. Block the thread until answer arrives or timeout
        effective_timeout = None
        if timeout_seconds and timeout_seconds > 0:
            elapsed = time.time() - start_time
            remaining = timeout_seconds - elapsed
            if remaining > 0:
                effective_timeout = remaining
            else:
                effective_timeout = 0.1  # already expired

        answered = event.wait(timeout=effective_timeout)

        # 5. If aborted during wait, raise
        if is_run_aborted(run_id):
            from hecos.modules.flows.engine import FlowAbortException
            raise FlowAbortException("Flow aborted while waiting for user input.")

        # 6. Retrieve the value
        value = get_pending_input_value(run_id)

        if not answered or value is None:
            log.warning(f"[USER__ask_input] Timed out waiting for input on run '{run_id}'.")
            return ""

        # 7. Echo reply into chat as a user message
        try:
            from hecos.memory.brain_interface import save_message
            save_message(
                role="user",
                message=value,
                user_id="admin",
                session_id=None,
                persona_name=None,
                broadcast_sse=True,
            )
        except Exception:
            pass

        log.info(f"[USER__ask_input] Got answer for run '{run_id}': {value[:80]}")
        return value

    except Exception as e:
        log.error(f"[USER__ask_input] Error: {e}")
        raise


_REGISTRY["USER__ask_input"] = {
    "name": "USER__ask_input",
    "description": (
        "Pauses the flow and waits for a user response (typed or spoken). "
        "The answer is stored in the output variable and can be used by LOGIC__if_else. "
        "intercept_mode controls how the answer is captured from chat."
    ),
    "params": {
        "prompt":             "string (Question to ask the user — shown in chat and spoken aloud)",
        "speak":              "boolean (Speak the prompt via TTS — default: true)",
        "intercept_mode":     "select:auto|explicit|api_only (How to capture the user reply from chat)",
        "multi_run_priority": "select:first|all (If multiple flows wait at once: answer only the first, or all)",
        "timeout_seconds":    "integer (Seconds to wait before giving up — 0 = wait forever)",
        "on_timeout_continue":"boolean (Continue with empty string on timeout instead of failing)",
    },
    "category": "USER",
    "icon": "🎤",
    "fn": _user_ask_input,
}


def _setup_audio_wrappers():
    def _audio_speak(text: str = "", **kwargs):
        try:
            from hecos.core.audio import voice
            voice.speak(text, _run_id=kwargs.get("_run_id"), _timeout=kwargs.get("_timeout_seconds"), _start=kwargs.get("_start_time"))
        except Exception as e:
            log.error(f"Cannot speak: {e}")
        return text

    def _audio_play_alarm(sound: str = "default", **kwargs):
        import os
        import time
        from hecos.modules.flows.engine import is_run_aborted

        run_id = kwargs.get("_run_id")
        timeout = kwargs.get("_timeout_seconds", 0)
        start_time = kwargs.get("_start_time", time.time())

        def _should_stop():
            if run_id and is_run_aborted(run_id): return True
            if timeout and timeout > 0 and (time.time() - start_time) > timeout: return True
            return False

        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

        try:
            if not sound or sound == "default":
                from hecos.core.audio import beep_generator
                beep_generator._play_beep_on_device(None)
                return True

            path = os.path.join(base_dir, "assets", "sounds", sound)

            if not os.path.exists(path):
                log.error(f"Cannot play alarm, file not found: {path}")
                from hecos.core.audio import beep_generator
                beep_generator._play_beep_on_device(None)
                return False

            played = False

            # Strategy 1: sounddevice + wave (headless-safe, no display required)
            if path.lower().endswith(".wav"):
                try:
                    import wave
                    import numpy as np
                    import sounddevice as sd
                    with wave.open(path, 'rb') as wf:
                        raw = wf.readframes(wf.getnframes())
                        data = np.frombuffer(raw, dtype=np.int16)
                        sd.play(data.astype("float32") / 32768.0, samplerate=wf.getframerate())
                        duration = len(data) / wf.getframerate() / wf.getnchannels()
                        end_time = time.time() + duration
                        while time.time() < end_time:
                            if _should_stop():
                                sd.stop()
                                break
                            time.sleep(0.05)
                    played = True
                except Exception as e_sd:
                    log.debug(f"[Flows.Alarm] sounddevice failed ({e_sd}), trying pygame...")

            # Strategy 2: pygame.mixer (works for mp3/wav/ogg, no display needed)
            if not played:
                try:
                    import pygame.mixer as mixer
                    if not mixer.get_init():
                        mixer.init()
                    mixer.music.load(path)
                    mixer.music.play()
                    while mixer.music.get_busy():
                        if _should_stop():
                            mixer.music.stop()
                            break
                        time.sleep(0.1)
                    played = True
                except Exception as e_pg:
                    log.warning(f"[Flows.Alarm] pygame.mixer failed ({e_pg}), trying winsound...")

            # Strategy 3: winsound (Windows-only, WAV only, last resort)
            if not played:
                if not _should_stop():
                    try:
                        import winsound
                        if path.lower().endswith(".wav"):
                            winsound.PlaySound(path, winsound.SND_FILENAME)
                            played = True
                    except Exception as e_ws:
                        log.error(f"[Flows.Alarm] All playback strategies failed. Last error: {e_ws}")

        except Exception as e:
            log.error(f"Cannot play alarm: {e}")
        return True

    _REGISTRY["AUDIO__speak"] = {
        "name": "AUDIO__speak",
        "description": "Make Hecos speak a message aloud via TTS.",
        "params": {"text": "string"},
        "category": "AUDIO",
        "icon": "🔊",
        "fn": _audio_speak,
    }
    _REGISTRY["AUDIO__play_alarm"] = {
        "name": "AUDIO__play_alarm",
        "description": "Play an alarm sound.",
        "params": {"sound": "string (default)"},
        "category": "AUDIO",
        "icon": "🔔",
        "fn": _audio_play_alarm,
    }

_setup_audio_wrappers()


def _setup_system_wrappers():
    def _system_chat_message(text: str = "", **kwargs):
        try:
            from hecos.memory.brain_interface import save_message
            # Since flows run in background threads, default to 'admin' user
            uid = "admin"
            try:
                from flask import request
                from flask_login import current_user
                if request and current_user.is_authenticated:
                    uid = current_user.username
            except RuntimeError:
                pass  # Working outside of request context
            
            save_message(
                role="assistant",
                message=text,
                user_id=uid,
                session_id=None,   # uses privacy_manager session
                persona_name="Flows",
                broadcast_sse=True   # push to chat in real time
            )
            log.info(f"[Flows.Chat] Message written: {text}")
        except Exception as e:
            log.error(f"[Flows.Chat] Cannot write chat message: {e}")
        return text

    _REGISTRY["SYSTEM__chat_message"] = {
        "name": "SYSTEM__chat_message",
        "description": "Appends a text message to the Hecos chat history.",
        "params": {"text": "string (message to write)"},
        "category": "SYSTEM",
        "icon": "💬",
        "fn": _system_chat_message,
    }

    def _system_speak_and_chat(text: str = "", **kwargs):
        # First send to chat
        _system_chat_message(text)
        # Then speak aloud
        try:
            from hecos.core.audio import voice
            voice.speak(text)
        except Exception as e:
            log.error(f"[Flows.Audio] Cannot speak: {e}")
        return text

    _REGISTRY["SYSTEM__speak_and_chat"] = {
        "name": "SYSTEM__speak_and_chat",
        "description": "Appends a message to the chat AND speaks it aloud.",
        "params": {"text": "string (message to speak and write)"},
        "category": "SYSTEM",
        "icon": "🗣️",
        "fn": _system_speak_and_chat,
    }

_setup_system_wrappers()


def _setup_ai_wrappers():
    def _ai_prompt(prompt: str = "", save_to_chat: bool = True):
        """
        Sends a prompt directly to the Hecos AI brain (AgentExecutor) and
        returns the full response text. The flow blocks here until the AI
        has finished thinking — the response is then available via output_as.
        """
        if not prompt:
            log.warning("[Flows.AI] AI__prompt called with empty prompt.")
            return ""
        try:
            from hecos.modules.web_ui.server import get_state_manager
            from hecos.core.agent.loop import AgentExecutor

            sm = get_state_manager()

            # Retrieve config_manager stored on the Flask app at startup
            cfg_mgr = None
            try:
                from flask import current_app
                cfg_mgr = getattr(current_app._get_current_object(), "hecos_config_manager", None)
            except RuntimeError:
                pass  # Working outside Flask request context (flow background thread)

            # Fallback: stored on sys by the main application
            if cfg_mgr is None:
                import sys
                cfg_mgr = getattr(sys, "hecos_config_manager", None)

            # Final fallback: create a fresh ConfigManager from disk
            if cfg_mgr is None:
                try:
                    from hecos.app.config import ConfigManager
                    cfg_mgr = ConfigManager()
                except Exception as e:
                    log.error(f"[Flows.AI] Could not instantiate ConfigManager: {e}")

            if cfg_mgr is None:
                log.error("[Flows.AI] Config manager not available — cannot call AI.")
                return "[AI__prompt error: config_manager not found]"

            agent = AgentExecutor(
                config=cfg_mgr.config,
                config_manager=cfg_mgr,
                state_manager=sm,
                trace_callback=lambda msg, level="info": log.debug(f"[Flows.AI.trace] {msg}"),
                current_user_id="admin",  # flows run outside HTTP context
            )

            log.info(f"[Flows.AI] Sending prompt to AI: {prompt[:80]}...")
            
            full_text, _voice = agent.run_agentic_loop(prompt, voice_status=False)
                
            log.info(f"[Flows.AI] AI response received ({len(full_text)} chars).")

            # Optionally persist the exchange to chat history so user can review it
            if save_to_chat:
                try:
                    from hecos.memory.brain_interface import save_message
                    save_message(role="user",      message=f"[Flow] {prompt}", user_id="admin", session_id=None, persona_name="Flows", broadcast_sse=True)
                    save_message(role="assistant", message=full_text,          user_id="admin", session_id=None, persona_name="Flows", broadcast_sse=True)
                except Exception as e:
                    log.warning(f"[Flows.AI] Could not save chat history: {e}")

            return full_text

        except TimeoutError:
            raise
        except Exception as e:
            log.error(f"[Flows.AI] Error calling AgentExecutor: {e}")
            return f"[AI__prompt error: {e}]"

    _REGISTRY["AI__prompt"] = {
        "name": "AI__prompt",
        "description": (
            "Send a natural-language prompt to the Hecos AI brain and capture the response. "
            "The flow blocks until the AI finishes. Use output_as to store the response as "
            "a variable for subsequent nodes."
        ),
        "params": {
            "prompt":              "string — the question or instruction to send to the AI",
            "save_to_chat":        "bool (optional, default true) — whether to write the prompt+response to the chat history",
            "timeout_seconds":     "integer (optional) — max time to wait before aborting the flow. 0 = infinite.",
            "on_timeout_continue": "bool (optional, default false) — if true, proceeds returning '[AI Timeout]' instead of stopping the flow",
        },
        "category": "AI",
        "icon": "🧠",
        "fn": _ai_prompt,
    }

_setup_ai_wrappers()



# ── Auto-registration from Hecos modules ──────────────────────────────────────

def _auto_register_hecos_modules():
    """
    Scan active Hecos modules and register their public methods as Flow actions.
    This uses the existing registry.json commands catalog as the source of truth.
    """
    try:
        from hecos.core.system import module_loader
        from hecos.core.system.module_loader import get_plugin_module

        registry_path = module_loader.REGISTRY_PATH
        import json, os
        if not os.path.exists(registry_path):
            return

        with open(registry_path, encoding="utf-8") as f:
            reg = json.load(f)

        CATEGORY_MAP = {
            "AUDIO": "AUDIO", "REMINDER": "TIME", "CALENDAR": "TIME",
            "MAIL": "MAIL", "MESSENGER": "MESSAGING", "WEATHER": "DATA",
            "EXECUTOR": "SYSTEM", "BROWSER": "BROWSER", "WEB": "BROWSER",
            "WEBCAM": "VISION", "AUTOMATION": "AUTOMATION", "MEMORY": "MEMORY",
            "IMAGE_GEN": "MEDIA", "MEDIA_PLAYER": "MEDIA",
        }
        ICON_MAP = {
            "AUDIO": "🔊", "REMINDER": "⏰", "CALENDAR": "📅",
            "MAIL": "📧", "MESSENGER": "💬", "WEATHER": "🌤️",
            "EXECUTOR": "⚙️", "BROWSER": "🌐", "WEB": "🌐",
            "WEBCAM": "📷", "AUTOMATION": "🖱️", "MEMORY": "🧠",
            "IMAGE_GEN": "🎨", "MEDIA_PLAYER": "🎵",
        }

        KNOWN_PARAMS = {
            "EXECUTOR__execute_slash_command": {"command": "string"},
            "EXECUTOR__execute_background_command": {"command": "string"},
            "EXECUTOR__execute_shell_command": {"command": "string"},
            "EXECUTOR__run_python_code": {"code": "string"},
            "EXECUTOR__read_file": {"file_path": "string", "start_line": "integer", "end_line": "integer"},
            "EXECUTOR__write_file": {"file_path": "string", "content": "string", "mode": "string"},
            "EXECUTOR__patch_file": {"file_path": "string", "old_text": "string", "new_text": "string"},
            "EXECUTOR__delete_file": {"file_path": "string"},
            "EXECUTOR__create_dir": {"directory_path": "string"},
            "EXECUTOR__list_dir": {"directory_path": "string"},
            "EXECUTOR__kill_process": {"name": "string"},
            # ── Mail ──────────────────────────────────────────────────────────────
            "MAIL__send_email": {
                "to":            "string (recipient email or contact name)",
                "subject":       "string (email subject — overridden if template_id is set)",
                "body":          "string (email body — overridden if template_id is set)",
                "cc":            "string (optional CC addresses)",
                "bcc":           "string (optional BCC addresses)",
                "is_html":       "boolean (true = body is HTML)",
                "template_id":   "string (optional — ID of an email template to use)",
                "template_vars": "dict   (optional — variable values to interpolate in the template, e.g. {\"nome\": \"Mario\"})",
            },
            # ── Messenger ─────────────────────────────────────────────────────────
            "MESSENGER__send_message": {
                "to":            "string (recipient — prefix with platform, e.g. 'telegram:@username')",
                "text":          "string (message text — overridden if template_id is set)",
                "platform":      "string (optional — 'telegram' | 'whatsapp' | 'discord')",
                "template_id":   "string (optional — ID of a messenger template to use)",
                "template_vars": "dict   (optional — variable values to interpolate in the template)",
            },
            "WEATHER__get_forecast": {"location": "string"},
        }

        for module_tag, module_info in reg.items():
            commands = module_info.get("commands", {})
            category = CATEGORY_MAP.get(module_tag, "PLUGINS")
            icon = ICON_MAP.get(module_tag, "⚡")

            for cmd_name, cmd_desc in commands.items():
                action_name = f"{module_tag}__{cmd_name}"
                if action_name not in _REGISTRY:
                    _REGISTRY[action_name] = {
                        "name":        action_name,
                        "description": cmd_desc,
                        "params":      KNOWN_PARAMS.get(action_name, {}),
                        "category":    category,
                        "icon":        icon,
                        "fn":          None,   # resolved at execute time via module_loader
                    }

        log.info(f"[Flows.Registry] Auto-registered {len(_REGISTRY)} actions from Hecos modules.")
    except Exception as e:
        log.warning(f"[Flows.Registry] Auto-registration incomplete: {e}")


# ── Public API ─────────────────────────────────────────────────────────────────

def get_catalog() -> List[Dict[str, Any]]:
    """Return all registered actions grouped by category (serializable, no fn)."""
    catalog: Dict[str, List] = {}
    for action in _REGISTRY.values():
        cat = action["category"]
        entry = {k: v for k, v in action.items() if k != "fn"}
        
        # Automatically inject execution-level parameters for non-trigger actions
        if cat != "TRIGGER":
            params_copy = dict(entry.get("params", {}))
            if "timeout_seconds" not in params_copy:
                params_copy["timeout_seconds"] = "integer (0 to disable)"
            if "on_timeout_continue" not in params_copy:
                params_copy["on_timeout_continue"] = "boolean (skip error and continue)"
            entry["params"] = params_copy
            
        catalog.setdefault(cat, []).append(entry)
    return catalog


def get_action(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single action definition by name."""
    return _REGISTRY.get(name)


def execute_action(name: str, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """
    Execute a registered action with the given parameters.
    Falls back to dynamic module_loader lookup for Hecos plugin actions.

    Priority for class-based plugins:
      1. module.tools.<method>(**params)   [class-based singleton e.g. REMINDER, MAIL]
      2. module.<method>(**params)         [legacy/module-level functions]
    """
    entry = _REGISTRY.get(name)

    if entry and entry.get("fn"):
        # Directly registered Python callable
        return entry["fn"](**params)

    # Dynamic dispatch via module_loader
    if "__" in name:
        module_tag, method_name = name.split("__", 1)
        try:
            from hecos.core.system.module_loader import get_plugin_module
            plugin_mod = get_plugin_module(module_tag, legacy=False)
            if plugin_mod is None:
                plugin_mod = get_plugin_module(module_tag, legacy=True)

            if plugin_mod:
                # Priority 1: class-based plugin — try module.tools.<method>
                tools_instance = getattr(plugin_mod, "tools", None)
                if tools_instance is not None:
                    method = getattr(tools_instance, method_name, None)
                    if callable(method):
                        log.debug(f"[Flows] Dispatching {name} via module.tools")
                        return method(**params)

                # Priority 2: module-level function (legacy / free-function plugins)
                method = getattr(plugin_mod, method_name, None)
                if callable(method):
                    log.debug(f"[Flows] Dispatching {name} via module-level function")
                    return method(**params)

                # Nothing found — emit a helpful error
                available = [m for m in dir(tools_instance or plugin_mod) if not m.startswith("_")]
                log.error(
                    f"[Flows] Plugin '{module_tag}' loaded but method '{method_name}' not found. "
                    f"Available: {available}"
                )
                raise AttributeError(
                    f"[Flows] '{module_tag}' has no method '{method_name}'. "
                    f"Available: {available}"
                )
            else:
                log.error(f"[Flows] Plugin '{module_tag}' is not loaded and could not be lazy-loaded.")

        except (AttributeError, KeyError) as e:
            raise RuntimeError(f"[Flows] Cannot dispatch {name}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"[Flows] Failed to execute {name}: {e}") from e

    raise KeyError(f"[Flows] Unknown action: '{name}'. Check the action catalog.")

