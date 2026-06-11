"""
HDCS — Builtin Flow Commands
Direct commands for interacting with Hecos Flows without the LLM:
/flow list, /flow run <name>, /flow trigger <name>, /flow status <name>
"""

import logging
import os

_log = logging.getLogger("HecosFlowCommands")


def _get_flows_dir(config=None) -> str:
    base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace", "flows"))
    return base


def _list_flows(raw_args_str="", config=None, **kwargs) -> str:
    """List all available flows in the workspace."""
    flows_dir = _get_flows_dir(config)
    if not os.path.isdir(flows_dir):
        return "❌ Directory flows non trovata."

    files = sorted(f for f in os.listdir(flows_dir) if f.endswith(".yaml") or f.endswith(".yml"))
    if not files:
        return "📂 Nessun flusso trovato in `workspace/flows/`.\n\nCrea un flusso dalla pagina **Flows**."

    lines = [f"## 📂 Flussi disponibili ({len(files)})\n"]
    for f in files:
        name = f.replace(".yaml", "").replace(".yml", "")
        # Try to read trigger from yaml
        try:
            import yaml
            with open(os.path.join(flows_dir, f), "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            trigger = data.get("trigger", {})
            trigger_type = trigger.get("type", "manual") if isinstance(trigger, dict) else str(trigger)
            enabled = "✅" if data.get("enabled", True) else "⏸️"
            lines.append(f"- {enabled} `{name}` *(trigger: {trigger_type})*")
        except Exception:
            lines.append(f"- 📄 `{name}`")

    lines.append(f"\n*Esegui con:* `/flow run <nome>`")
    return "\n".join(lines)


def _run_flow(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Run a flow by name, bypassing the LLM."""
    name = raw_args_str.strip()
    if not name:
        return "**Uso:** `/flow run <nome_flusso>`\n\nEsempio: `/flow run la_casa_misteriosa`"

    flows_dir = _get_flows_dir(config)
    # Try with and without extension
    candidates = [
        os.path.join(flows_dir, name + ".yaml"),
        os.path.join(flows_dir, name + ".yml"),
        os.path.join(flows_dir, name),
    ]
    flow_path = next((p for p in candidates if os.path.isfile(p)), None)

    if not flow_path:
        return (
            f"❌ Flusso non trovato: `{name}`\n\n"
            f"Usa `/flow list` per vedere i flussi disponibili."
        )

    try:
        from hecos.modules.flows.executor import FlowExecutor
        cfg = config or (config_manager.config if config_manager else None)
        executor = FlowExecutor(config=cfg)
        result = executor.run_from_file(flow_path)
        return f"✅ Flusso `{name}` eseguito.\n\n{result}"
    except ImportError:
        # Fallback: try direct execution via flows runner
        try:
            import subprocess, sys
            result = subprocess.run(
                [sys.executable, "-m", "hecos.modules.flows.run", flow_path],
                capture_output=True, text=True, timeout=60
            )
            out = result.stdout.strip() or result.stderr.strip() or "Nessun output."
            return f"✅ Flusso `{name}` avviato.\n\n```\n{out[:1000]}\n```"
        except Exception as e:
            return f"❌ Errore esecuzione flusso `{name}`: {e}"
    except Exception as e:
        _log.error(f"[HDCS Flow] run error: {e}", exc_info=True)
        return f"❌ Errore esecuzione flusso `{name}`: {e}"


def _flow_status(raw_args_str="", config=None, **kwargs) -> str:
    """Show the last run status of a flow."""
    name = raw_args_str.strip()
    if not name:
        return "**Uso:** `/flow status <nome_flusso>`"

    flows_dir = _get_flows_dir(config)
    log_dir = os.path.join(os.path.dirname(flows_dir), "logs", "flows")

    # Look for latest log file for this flow
    if os.path.isdir(log_dir):
        logs = sorted(
            [f for f in os.listdir(log_dir) if name in f],
            reverse=True
        )
        if logs:
            log_path = os.path.join(log_dir, logs[0])
            try:
                with open(log_path, "r", encoding="utf-8") as fh:
                    content = fh.read()[-2000:]
                return f"## 📊 Status: `{name}`\n\n```\n{content}\n```"
            except Exception:
                pass

    return f"ℹ️ Nessun log trovato per il flusso `{name}`."


def _flow_trigger(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Manually trigger a flow (same as run, explicit alias)."""
    return _run_flow(raw_args_str=raw_args_str, config=config, config_manager=config_manager, **kwargs)


# ── Command descriptors ───────────────────────────────────────────────────────

FLOW_COMMANDS = [
    {
        "id": "flow_list",
        "aliases": ["/flow list", "/flows", "/flow ls"],
        "description": "Elenca tutti i flussi disponibili nel workspace",
        "usage": "/flow list",
        "example": "/flow list",
        "icon": "📂",
        "category": "FLOWS",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "output_target": "contextual",
        "_handler": _list_flows,
    },
    {
        "id": "flow_run",
        "aliases": ["/flow run", "/flow exec"],
        "description": "Esegue un flusso direttamente, senza l'LLM",
        "usage": "/flow run <nome_flusso>",
        "example": "/flow run check_weather_alert",
        "icon": "▶️",
        "category": "FLOWS",
        "requires_auth": "any",
        "requires_args": True,
        "output_target": "contextual",
        "_handler": _run_flow,
    },
    {
        "id": "flow_trigger",
        "aliases": ["/flow trigger", "/trigger"],
        "description": "Attiva manualmente il trigger di un flusso",
        "usage": "/flow trigger <nome_flusso>",
        "example": "/flow trigger morning_routine",
        "icon": "⚡",
        "category": "FLOWS",
        "requires_auth": "any",
        "requires_args": True,
        "output_target": "contextual",
        "_handler": _flow_trigger,
    },
    {
        "id": "flow_status",
        "aliases": ["/flow status", "/flow log"],
        "description": "Mostra l'ultimo log di esecuzione di un flusso",
        "usage": "/flow status <nome_flusso>",
        "example": "/flow status check_weather_alert",
        "icon": "📊",
        "category": "FLOWS",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "output_target": "contextual",
        "_handler": _flow_status,
    },
]
