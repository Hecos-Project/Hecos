"""
Hecos Flows — Main Module Entry Point
=======================================
Exposes the FlowsEngine class as the primary Hecos plugin interface,
and registers LLM-facing tools (list_flows, run_flow, create_flow_from_nlp, etc.)
"""

import logging
from typing import Any, Dict, Optional

log = logging.getLogger("HecosFlows")


class FlowsEngine:
    """
    Hecos Flows Engine — Visual orchestration layer.
    Lets users build, schedule, and run multi-step pipelines via NLP,
    node-graph canvas, or direct YAML editing.
    """

    def __init__(self):
        self.tag    = "FLOWS"
        self.desc   = (
            "Visual flow orchestration engine. Build multi-step automated pipelines "
            "with logic, scheduling, and data-passing between modules. "
            "Create via voice/text (NLP compiler), node-graph canvas, or YAML editor."
        )
        self.routing_instructions = (
            "FLOWS ORCHESTRATION: When the user wants to create a recurring automation, "
            "schedule tasks, or chain multiple actions together (e.g. 'every morning do X then Y then Z'), "
            "use the Flows engine. Call FLOWS__create_flow_from_nlp with the user's description."
        )
        self.status = "ONLINE"

        self.config_schema = {
            "enabled": {
                "type": "bool",
                "default": True,
                "description": "Enable/disable the Flows orchestration engine.",
            }
        }

        # Load schedules for all persisted flows on startup
        self._bootstrap_schedules()

    def _bootstrap_schedules(self):
        """Re-register all enabled flow triggers with APScheduler at startup."""
        try:
            from .engine import load_all_schedules
            load_all_schedules()
        except Exception as e:
            log.warning(f"[Flows] Could not load schedules at startup: {e}")

    # ── LLM-callable tools ─────────────────────────────────────────────────────

    def list_flows(self) -> str:
        """
        Returns a formatted list of all saved flows with their status and trigger.
        """
        try:
            from .storage import list_flows
            flows = list_flows()
            if not flows:
                return "[Flows] No flows saved yet. Use FLOWS__create_flow_from_nlp to create your first automation."

            lines = ["📋 **Saved Flows:**"]
            for f in flows:
                status_icon = "✅" if f["enabled"] else "⏸️"
                trigger_str = f["trigger_type"]
                if f["trigger_expr"]:
                    trigger_str += f": {f['trigger_expr']}"
                lines.append(
                    f"{status_icon} **{f['name']}** (`{f['id']}`)"
                    f" — {trigger_str} — {f['step_count']} steps"
                )
                if f.get("last_run"):
                    lines.append(f"   Last run: {f['last_run'][:19]}")
            return "\n".join(lines)
        except Exception as e:
            return f"[Flows] Error listing flows: {e}"

    def get_flow(self, flow_id: str) -> str:
        """
        Returns the YAML definition of a specific flow.
        :param flow_id: The flow ID (slug) to retrieve.
        """
        try:
            from .storage import get_flow_yaml
            yaml_text = get_flow_yaml(flow_id)
            if yaml_text is None:
                return f"[Flows] Flow '{flow_id}' not found."
            return f"```yaml\n{yaml_text}\n```"
        except Exception as e:
            return f"[Flows] Error: {e}"

    def create_flow_from_nlp(
        self,
        description: str,
        flow_name: Optional[str] = None,
    ) -> str:
        """
        Compiles a natural-language description into a Flow YAML and saves it.
        Returns a summary card confirming what was created.

        :param description: Plain-language description of the automation.
        :param flow_name: Optional short name for the flow.
        """
        try:
            from .compiler import compile_from_nlp
            from .storage import save_flow
            from .engine import schedule_flow

            yaml_text, summary, flow_dict = compile_from_nlp(
                description=description,
                flow_name=flow_name,
            )

            flow_id = save_flow(flow_dict, raw_yaml=yaml_text)
            schedule_flow(flow_dict)

            trigger = flow_dict.get("trigger", {})
            t_type  = trigger.get("type", "manual")
            t_expr  = trigger.get("expression", "")
            trigger_str = f"{t_type}: {t_expr}" if t_expr else t_type

            return (
                f"✅ **{summary}**\n\n"
                f"💾 Saved as: `{flow_id}`\n"
                f"⏱️ Trigger: `{trigger_str}`\n"
                f"📋 Steps: {len(flow_dict.get('pipeline', []))}\n\n"
                f"Open the Hecos Flows page to visualize and edit it on the node canvas."
            )
        except Exception as e:
            return f"[Flows] Compilation failed: {e}"

    def _resolve_flow_id(self, flow_id_or_name: str) -> str:
        """Resolve a user-provided name or slug to the actual flow ID.
        
        Tries exact match first, then normalised slug match,
        then case-insensitive display-name match against all saved flows.
        """
        from .storage import list_flows, slugify
        candidate = slugify(flow_id_or_name)  # e.g. 'zobbia 1' -> 'zobbia_1'
        flows = list_flows()
        ids = {f["id"] for f in flows}
        # 1. direct exact match
        if flow_id_or_name in ids:
            return flow_id_or_name
        # 2. slugified match
        if candidate in ids:
            return candidate
        # 3. case-insensitive display name match
        for f in flows:
            if f.get("name", "").lower().strip() == flow_id_or_name.lower().strip():
                return f["id"]
        # 4. best-effort: return the original so the caller surfaces a helpful error
        return flow_id_or_name

    def run_flow(self, flow_id: str) -> str:
        """
        Immediately executes a saved flow by its ID or display name.
        :param flow_id: The flow ID (slug) or display name to execute.
        """
        try:
            from .storage import get_flow
            from .engine import run_flow_async

            flow_id = self._resolve_flow_id(flow_id)
            flow_data = get_flow(flow_id)
            if flow_data is None:
                return f"[Flows] Flow '{flow_id}' not found."

            run_id = run_flow_async(flow_data)
            return (
                f"▶️ Flow **{flow_data.get('name', flow_id)}** started (run ID: `{run_id}`).\n"
                f"Open the Flows page → Log tab to monitor execution in real-time."
            )
        except Exception as e:
            return f"[Flows] Could not run flow '{flow_id}': {e}"

    def enable_flow(self, flow_id: str) -> str:
        """
        Enables a flow so its scheduler trigger becomes active.
        :param flow_id: The flow ID or display name to enable.
        """
        try:
            from .storage import update_flow_field, get_flow
            from .engine import schedule_flow

            flow_id = self._resolve_flow_id(flow_id)
            if not update_flow_field(flow_id, "enabled", True):
                return f"[Flows] Flow '{flow_id}' not found. Available flows: " + ", ".join(f["id"] for f in __import__('hecos.modules.flows.storage', fromlist=['list_flows']).list_flows())

            flow_data = get_flow(flow_id)
            if flow_data:
                schedule_flow(flow_data)

            return f"✅ Flow `{flow_id}` enabled and scheduled."
        except Exception as e:
            return f"[Flows] Error: {e}"

    def disable_flow(self, flow_id: str) -> str:
        """
        Disables a flow so it won't trigger automatically.
        :param flow_id: The flow ID or display name to disable.
        """
        try:
            from .storage import update_flow_field
            from .engine import unschedule_flow

            flow_id = self._resolve_flow_id(flow_id)
            if not update_flow_field(flow_id, "enabled", False):
                return f"[Flows] Flow '{flow_id}' not found."

            unschedule_flow(flow_id)
            return f"⏸️ Flow `{flow_id}` disabled."
        except Exception as e:
            return f"[Flows] Error: {e}"

    def delete_flow(self, flow_id: str) -> str:
        """
        Permanently deletes a flow.
        :param flow_id: The flow ID or display name to delete.
        """
        try:
            from .storage import delete_flow
            from .engine import unschedule_flow

            flow_id = self._resolve_flow_id(flow_id)
            unschedule_flow(flow_id)
            deleted = delete_flow(flow_id)
            if not deleted:
                return f"[Flows] Flow '{flow_id}' not found."
            return f"🗑️ Flow `{flow_id}` deleted permanently."
        except Exception as e:
            return f"[Flows] Error: {e}"

    def get_action_catalog(self) -> str:
        """
        Returns the full catalog of all available flow actions, grouped by category.
        """
        try:
            from .registry import get_catalog, _auto_register_hecos_modules
            _auto_register_hecos_modules()
            catalog = get_catalog()

            lines = ["⚡ **Available Flow Actions:**\n"]
            for category, actions in sorted(catalog.items()):
                lines.append(f"**{category}**")
                for a in sorted(actions, key=lambda x: x["name"]):
                    lines.append(f"  • `{a['name']}` {a['icon']} — {a['description'][:80]}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return f"[Flows] Error: {e}"


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[FlowsEngine] = None


def get_plugin() -> FlowsEngine:
    global _instance
    if _instance is None:
        _instance = FlowsEngine()
    return _instance


def info() -> Dict[str, str]:
    return {"tag": "FLOWS", "desc": get_plugin().desc}


def status() -> str:
    return get_plugin().status


def on_load(config: Dict) -> None:
    """Called by ModuleLoader at startup (if lazy_load=False or explicitly triggered)."""
    _ = get_plugin()
    log.info("[Flows] Module loaded and schedules initialized.")
