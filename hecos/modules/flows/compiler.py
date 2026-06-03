"""
Hecos Flows — NLP Compiler
============================
Translates a natural-language description (Italian or English, voice or text)
into a valid Flow YAML using the configured LLM.

The LLM is given a rigid system prompt with the schema specification so it
always outputs a well-formed YAML that the validator can accept.
"""

import json
from typing import Dict, Any, Optional, Tuple

from hecos.core.logging import logger
class FlowLogger:
    def info(self, msg): logger.info("FLOWS", msg)
    def error(self, msg): logger.error("FLOWS", msg)
    def warning(self, msg): logger.debug("FLOWS", f"[WARN] {msg}")
    def debug(self, msg): logger.debug("FLOWS", msg)

log = FlowLogger()


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are the Hecos Flow Compiler. Your ONLY task is to convert a natural-language automation description into a valid Hecos Flow YAML.

=== FLOW YAML SCHEMA ===
id: <slug, lowercase_underscore, max 64 chars>        # REQUIRED
name: <display name with emoji>                         # REQUIRED
description: <short description>
version: 1
enabled: true

trigger:
  type: <cron | interval | manual>
  expression: "0 7 * * *"   # for cron (minute hour dom month dow)
  # OR for interval:
  every: 30
  unit: <seconds | minutes | hours>

variables:
  key: value   # optional static variables

pipeline:      # REQUIRED, list of steps
  - id: <unique_step_id>                               # REQUIRED
    action: <MODULE__method>                            # REQUIRED
    params:
      key: "{{ variable }}"   # Jinja2 template references supported
    output_as: <variable_name>   # optional: store action result
    depends_on: [<step_id>]      # optional: list of step IDs this depends on

=== AVAILABLE ACTIONS ===
# ── Audio ──────────────────────────────────────────────────────────────────────
AUDIO__speak: params: {text: "..."}  — Make Hecos speak via TTS
AUDIO__play_alarm: params: {sound: "default"}  — Play an alarm beep

# ── Reminder ───────────────────────────────────────────────────────────────────
REMINDER__set_reminder: params: {title: "...", when: "YYYY-MM-DD HH:MM or 'in X minutes'"}  — Schedule a reminder with TTS + notification
REMINDER__list_reminders: params: {}  — List active reminders → output_as reminders
REMINDER__cancel_reminder: params: {reminder_id: "..."}  — Cancel a reminder by ID

# ── Weather ────────────────────────────────────────────────────────────────────
WEATHER__get_current_weather: params: {city: "..."}  — Current weather → output_as weather_data
WEATHER__get_weather_forecast: params: {city: "..."}  — 7-day forecast → output_as forecast

# ── Mail ───────────────────────────────────────────────────────────────────────
MAIL__send_email: params: {to: "...", subject: "...", body: "..."}  — Send email

# ── Messenger ──────────────────────────────────────────────────────────────────
MESSENGER__send_message: params: {platform: "whatsapp", to: "+39...", text: "..."}  — Send WhatsApp/Telegram/Discord

# ── Calendar ───────────────────────────────────────────────────────────────────
CALENDAR__list_events: params: {}  — List upcoming events → output_as events
CALENDAR__add_event: params: {title: "...", start: "YYYY-MM-DD HH:MM", end: "YYYY-MM-DD HH:MM"}  — Create an event

# ── Web / Search ───────────────────────────────────────────────────────────────
WEB__search_and_read: params: {query: "...", num_results: 3}  — Web search → output_as articles
WEB__fetch_page_content: params: {url: "..."}  — Read a page → output_as page_text

# ── Executor (system tools) ───────────────────────────────────────────────────
EXECUTOR__get_time: params: {}  — Get current local time → output_as current_time
EXECUTOR__get_date: params: {}  — Get current date → output_as current_date
EXECUTOR__run_python_code: params: {code: "..."}  — Run safe Python code → output_as result

# ── Logic (native, no plugin needed) ──────────────────────────────────────────
LOGIC__if_else: params: {condition: "{{ var }} < 15", true_branch: {action: "...", params: {}}, false_branch: {action: "...", params: {}}}
LOGIC__delay: params: {seconds: 5}
LOGIC__set_variable: params: {name: "my_var", value: "{{ other_var }}"}

=== RULES ===
1. Output ONLY the YAML — no markdown fences, no explanation, no commentary.
2. Every step MUST have a unique 'id' (lowercase_underscore, e.g. step_greet).
3. Use depends_on to define order. Steps with no depends_on run first.
4. Use output_as when a step's result is needed by a later step.
5. Use Jinja2 {{ variable_name }} to reference outputs from previous steps.
6. For conditional logic (if/else), use LOGIC__if_else.
7. For weather-based clothing advice: get weather first, then LOGIC__if_else on temperature.
8. The 'id' field must be a slug (no spaces, no special chars, max 64).
9. DO NOT invent action names. ONLY use the actions listed above.
10. Respond with ONLY valid YAML. Any non-YAML text will cause a fatal error.
"""


_SUMMARY_PROMPT = """Given this Hecos Flow YAML, write a concise 1-sentence Italian summary for the user (max 120 chars). 
Start with "Ho creato il flusso:". List the key steps separated by →. End with the trigger info if it's scheduled.
YAML:
{yaml}
"""


# ── Compiler ───────────────────────────────────────────────────────────────────

def compile_from_nlp(
    description: str,
    flow_name: Optional[str] = None,
    config: Optional[Dict] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Compile a natural-language description into a Flow YAML using the LLM.

    Args:
        description: User's natural-language description of the desired automation.
        flow_name:   Optional name override for the flow.
        config:      Hecos config dict (for LLM provider selection).

    Returns:
        Tuple of (yaml_string, summary_card_text, flow_dict)

    Raises:
        ValueError: If the LLM output cannot be parsed or validated.
    """
    user_prompt = description
    if flow_name:
        user_prompt = f"Flow name: {flow_name}\n\n{description}"

    yaml_text = _call_llm(_SYSTEM_PROMPT, user_prompt, config)

    # Clean markdown fences if LLM added them anyway
    yaml_text = _strip_markdown_fences(yaml_text)

    # Validate
    from .validator import validate_yaml_string
    is_valid, errors, flow_dict = validate_yaml_string(yaml_text)

    if not is_valid:
        log.warning(f"[Flows.Compiler] LLM output has validation errors: {errors}")
        # Attempt auto-fix by asking LLM again
        fix_prompt = (
            f"The YAML you generated has the following errors:\n" +
            "\n".join(f"- {e}" for e in errors) +
            f"\n\nOriginal YAML:\n{yaml_text}\n\nPlease output a corrected YAML only."
        )
        yaml_text = _call_llm(_SYSTEM_PROMPT, fix_prompt, config)
        yaml_text = _strip_markdown_fences(yaml_text)
        is_valid, errors, flow_dict = validate_yaml_string(yaml_text)

        if not is_valid:
            raise ValueError(
                f"LLM could not generate a valid flow after retry. Errors: {'; '.join(errors)}"
            )

    # Generate summary card
    summary = _generate_summary(yaml_text, config)

    log.info(f"[Flows.Compiler] Compiled flow '{flow_dict.get('id')}' successfully.")
    return yaml_text, summary, flow_dict


def _call_llm(system_prompt: str, user_message: str, config: Optional[Dict]) -> str:
    """Call the configured Hecos LLM provider."""
    try:
        from hecos.app.config import ConfigManager
        cfg = config if config is not None else ConfigManager().config
        from hecos.core.llm import manager

        # Use the singleton LLM manager directly (it is already loaded)
        mgr = manager.manager if hasattr(manager, 'manager') else manager.LLMManager()
        model_name = mgr.resolve_model(tag="FLOWS", config_override=cfg)
        if not model_name:
            raise RuntimeError("No LLM model configured for flows. Set a model in Settings → LLM.")

        log.debug(f"[Flows.Compiler] Resolved model: {model_name}")
        log.debug(f"[Flows.Compiler] User prompt ({len(user_message)} chars): {user_message[:200]}...")

        is_cloud = any(model_name.startswith(p + "/") for p in ["groq", "openai", "anthropic", "gemini", "cohere"])
        is_kobold = model_name.startswith("kobold/")

        if is_cloud:
            backend_type = "cloud"
        elif is_kobold:
            backend_type = "kobold"
        else:
            backend_type = "ollama"

        subconfig = dict(cfg.get("backend", {}).get(backend_type, {}))
        subconfig["backend_type"] = backend_type
        subconfig["model"] = model_name
        subconfig["temperature"] = 0.1

        from hecos.core.llm.client import generate
        response = generate(
            system_prompt=system_prompt,
            user_message=user_message,
            config_or_subconfig=subconfig,
        )

        if isinstance(response, str) and (response.startswith("⚠️") or response.startswith("[SYSTEM]")):
            raise RuntimeError(response)

        result = response.strip() if isinstance(response, str) else ""
        log.debug(f"[Flows.Compiler] Raw LLM response ({len(result)} chars): {result[:300]}...")
        return result
    except Exception as e:
        raise RuntimeError(f"[Flows.Compiler] LLM call failed: {e}")


def _generate_summary(yaml_text: str, config: Optional[Dict]) -> str:
    """Generate a short Italian summary card for the compiled flow."""
    try:
        prompt = _SUMMARY_PROMPT.format(yaml=yaml_text[:1500])
        return _call_llm("You are a concise assistant. Reply only with the summary sentence.", prompt, config)
    except Exception:
        return "Ho creato il flusso richiesto con successo."


def _strip_markdown_fences(text: str) -> str:
    """Remove ```yaml ... ``` or ``` ... ``` wrappers from LLM output."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


# ── Rule-based fallback parser ─────────────────────────────────────────────────

def compile_from_template(template_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a flow from a pre-defined template (offline/no-LLM fallback).
    Templates are stored as YAML files in hecos/modules/flows/templates/.
    """
    import os
    import yaml

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    path = os.path.join(templates_dir, f"{template_name}.yaml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"[Flows.Compiler] Template not found: {template_name}")

    from jinja2 import Template
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    rendered = Template(raw).render(**params)
    return yaml.safe_load(rendered)
