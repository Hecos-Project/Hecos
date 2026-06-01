"""
Hecos Flows — Storage
=====================
CRUD operations for flow YAML files stored in workspace/flows/.
Each flow is a single .yaml file named after its flow ID (slug).
"""

import os
import re
import yaml
import datetime
from typing import Optional, Dict, List, Any

from hecos.core.logging import logger
class FlowLogger:
    def info(self, msg): logger.info("FLOWS", msg)
    def error(self, msg): logger.error("FLOWS", msg)
    def warning(self, msg): logger.debug("FLOWS", f"[WARN] {msg}")
    def debug(self, msg): logger.debug("FLOWS", msg)

log = FlowLogger()

# ── Locate workspace/flows directory ──────────────────────────────────────────

def _get_flows_dir() -> str:
    """Returns the absolute path to workspace/flows/, creating it if needed."""
    try:
        from hecos.core.constants import ROOT_DIR
        flows_dir = os.path.join(ROOT_DIR, "workspace", "flows")
    except Exception:
        flows_dir = os.path.join(os.getcwd(), "workspace", "flows")
    os.makedirs(flows_dir, exist_ok=True)
    return flows_dir


# ── Slug utilities ─────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert a display name to a safe file/ID slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:64]


def _path_for(flow_id: str) -> str:
    return os.path.join(_get_flows_dir(), f"{flow_id}.yaml")


# ── CRUD ───────────────────────────────────────────────────────────────────────

def list_flows() -> List[Dict[str, Any]]:
    """
    Returns a summary list of all flows.
    Each item: { id, name, description, enabled, trigger_type, last_run, version }
    """
    flows_dir = _get_flows_dir()
    result = []
    for fname in sorted(os.listdir(flows_dir)):
        if not fname.endswith(".yaml"):
            continue
        flow_id = fname[:-5]
        try:
            data = _load_yaml_file(os.path.join(flows_dir, fname))
            result.append({
                "id":           data.get("id", flow_id),
                "name":         data.get("name", flow_id),
                "description":  data.get("description", ""),
                "enabled":      data.get("enabled", True),
                "trigger_type": data.get("trigger", {}).get("type", "manual"),
                "trigger_expr": data.get("trigger", {}).get("expression", ""),
                "step_count":   len(data.get("pipeline", [])),
                "version":      data.get("version", 1),
                "last_run":     data.get("_meta", {}).get("last_run", None),
                "created_at":   data.get("_meta", {}).get("created_at", None),
            })
        except Exception as e:
            log.warning(f"[Flows.Storage] Could not read {fname}: {e}")
    return result


def get_flow(flow_id: str) -> Optional[Dict[str, Any]]:
    """Load a single flow by ID. Returns None if not found."""
    path = _path_for(flow_id)
    if not os.path.exists(path):
        return None
    return _load_yaml_file(path)


def get_flow_yaml(flow_id: str) -> Optional[str]:
    """Return raw YAML string for a flow."""
    path = _path_for(flow_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_flow(flow_data: Dict[str, Any], raw_yaml: Optional[str] = None) -> str:
    """
    Save a flow to disk. Accepts either a dict (will be serialized) or a raw YAML string.
    Returns the flow_id.
    """
    if not flow_data.get("id"):
        name = flow_data.get("name", "unnamed_flow")
        flow_data["id"] = slugify(name)

    flow_id = flow_data["id"]
    path = _path_for(flow_id)

    # Update metadata
    now = datetime.datetime.now().isoformat()
    meta = flow_data.get("_meta", {})
    if not meta.get("created_at"):
        meta["created_at"] = now
    meta["updated_at"] = now
    flow_data["_meta"] = meta

    if raw_yaml:
        # Parse the YAML to inject meta, then re-serialize
        try:
            parsed = yaml.safe_load(raw_yaml)
            if isinstance(parsed, dict):
                parsed["_meta"] = meta
                parsed["id"] = flow_id
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(parsed, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            else:
                # Fallback: write as-is
                with open(path, "w", encoding="utf-8") as f:
                    f.write(raw_yaml)
        except Exception:
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw_yaml)
    else:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(flow_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    log.info(f"[Flows.Storage] Saved flow: {flow_id}")
    return flow_id


def delete_flow(flow_id: str) -> bool:
    """Delete a flow file. Returns True on success."""
    path = _path_for(flow_id)
    if os.path.exists(path):
        os.remove(path)
        log.info(f"[Flows.Storage] Deleted flow: {flow_id}")
        return True
    return False


def update_flow_field(flow_id: str, field: str, value: Any) -> bool:
    """Update a single top-level field (e.g. enabled, _meta.last_run)."""
    data = get_flow(flow_id)
    if data is None:
        return False
    if "." in field:
        parts = field.split(".", 1)
        sub = data.setdefault(parts[0], {})
        sub[parts[1]] = value
    else:
        data[field] = value
    save_flow(data)
    return True


# ── Internal helpers ────────────────────────────────────────────────────────────

def _load_yaml_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
