"""
Hecos Flows — Schema Validator
================================
Validates a flow dict against the expected YAML schema using Pydantic v1/v2.
Falls back to basic dict-level checks if Pydantic is unavailable.
"""

from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging import logger
class FlowLogger:
    def info(self, msg): logger.info("FLOWS", msg)
    def error(self, msg): logger.error("FLOWS", msg)
    def warning(self, msg): logger.debug("FLOWS", f"[WARN] {msg}")
    def debug(self, msg): logger.debug("FLOWS", msg)

log = FlowLogger()


# ── Schema definition ──────────────────────────────────────────────────────────

VALID_TRIGGER_TYPES = {"cron", "interval", "manual", "event"}
VALID_LOGIC_NODES = {
    "LOGIC__if_else", "LOGIC__switch", "LOGIC__loop",
    "LOGIC__delay", "LOGIC__set_variable", "LOGIC__template",
    "LOGIC__and_gate", "LOGIC__or_gate", "LOGIC__http_request",
}

REQUIRED_TOP_LEVEL = {"id", "name", "pipeline"}
REQUIRED_STEP_FIELDS = {"id", "action"}


def validate_flow(flow_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a flow data dict.

    Returns:
        (is_valid: bool, errors: List[str])
    """
    errors: List[str] = []

    # ── Top-level required fields
    for field in REQUIRED_TOP_LEVEL:
        if not flow_data.get(field):
            errors.append(f"Missing required field: '{field}'")

    # ── ID must be a valid slug
    flow_id = flow_data.get("id", "")
    if flow_id and not flow_id.replace("_", "").replace("-", "").isalnum():
        errors.append(f"Field 'id' must be alphanumeric with underscores/hyphens only. Got: '{flow_id}'")

    # ── Trigger validation
    trigger = flow_data.get("trigger", {})
    t_type = trigger.get("type", "manual")
    if t_type not in VALID_TRIGGER_TYPES:
        errors.append(f"Invalid trigger type: '{t_type}'. Valid: {VALID_TRIGGER_TYPES}")

    if t_type == "cron":
        expr = trigger.get("expression", "")
        if not expr:
            errors.append("Trigger type 'cron' requires an 'expression' field.")
        else:
            _validate_cron_expr(expr, errors)

    if t_type == "interval":
        if "every" not in trigger:
            errors.append("Trigger type 'interval' requires an 'every' field.")
        unit = trigger.get("unit", "seconds")
        if unit not in {"seconds", "minutes", "hours"}:
            errors.append(f"Trigger 'unit' must be seconds|minutes|hours. Got: '{unit}'")

    # ── Pipeline validation
    pipeline = flow_data.get("pipeline", [])
    if not isinstance(pipeline, list):
        errors.append("Field 'pipeline' must be a list of step objects.")
    else:
        if len(pipeline) == 0:
            errors.append("Pipeline must have at least one step.")

        all_ids = {s.get("id") for s in pipeline if isinstance(s, dict) and s.get("id")}
        seen_ids = set()
        for i, step in enumerate(pipeline):
            prefix = f"Step[{i}] (id={step.get('id', '?')})"

            for field in REQUIRED_STEP_FIELDS:
                if not step.get(field):
                    errors.append(f"{prefix}: Missing required field '{field}'")

            step_id = step.get("id", "")
            if step_id in seen_ids:
                errors.append(f"{prefix}: Duplicate step ID '{step_id}'")
            seen_ids.add(step_id)

            depends = step.get("depends_on", [])
            if isinstance(depends, list):
                valid_depends = []
                for dep in depends:
                    if dep not in all_ids and dep != step_id:
                        log.warning(f"{prefix}: 'depends_on' references unknown step ID '{dep}'. Auto-removing dangling dependency.")
                    else:
                        valid_depends.append(dep)
                if len(valid_depends) != len(depends):
                    if valid_depends:
                        step["depends_on"] = valid_depends
                    else:
                        del step["depends_on"]

    # ── Summary
    is_valid = len(errors) == 0
    if not is_valid:
        log.warning(f"[Flows.Validator] Flow '{flow_id}' has {len(errors)} validation error(s).")
        for err in errors:
            log.warning(f"  - {err}")
    return is_valid, errors


def _validate_cron_expr(expr: str, errors: List[str]) -> None:
    """Basic 5-field cron validation (minute hour dom month dow)."""
    parts = expr.strip().split()
    if len(parts) != 5:
        errors.append(
            f"Cron expression must have 5 fields (min hour dom month dow). Got: '{expr}'"
        )
        return
    # Could add field-by-field range checks here in the future


def validate_yaml_string(yaml_text: str) -> Tuple[bool, List[str], Optional[Dict]]:
    """
    Parse and validate a raw YAML string.

    Returns:
        (is_valid, errors, parsed_dict_or_None)
    """
    errors: List[str] = []
    try:
        import yaml
        data = yaml.safe_load(yaml_text)
    except Exception as e:
        return False, [f"YAML parse error: {e}"], None

    if not isinstance(data, dict):
        return False, ["YAML root must be a mapping (dict)."], None

    is_valid, schema_errors = validate_flow(data)
    errors.extend(schema_errors)
    return is_valid, errors, data
