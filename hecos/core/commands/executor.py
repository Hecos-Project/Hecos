"""
HDCS — Command Executor
Receives a raw slash command string + user context, resolves it via the registry,
enforces role-based access control, and executes it by calling the target plugin
method or builtin handler directly — bypassing the LLM entirely.

Standardized output:
{
  "ok": bool,
  "source": "DIRECT_COMMAND",
  "command": str,           # the resolved alias used
  "output": str,            # text/markdown to show in UI
  "save_to_memory": bool,   # whether to persist in conversation history
  "output_target": str,     # "chat" | "contextual"
  "error": str | None,
}
"""

import logging
import inspect
from typing import Optional

_log = logging.getLogger("HecosCommandExecutor")


class CommandExecutor:
    """Executes HDCS slash commands with RBAC and arg parsing."""

    RESULT_TEMPLATE = {
        "ok": False,
        "source": "DIRECT_COMMAND",
        "command": "",
        "output": "",
        "save_to_memory": True,
        "output_target": "chat",
        "error": None,
    }

    def execute(
        self,
        raw_input: str,
        config=None,
        config_manager=None,
        current_user_role: str = "user",
        current_user_id: str = "admin",
        session_id: Optional[str] = None,
        sender_tab_id: Optional[str] = None,
        page_context: str = "chat",   # "chat" | "flows"
    ) -> dict:
        """
        Main entry point. Parse raw_input, resolve command, check roles, execute.

        Args:
            raw_input:          Full user string, e.g. "/img foto di un gatto"
            config:             Hecos config dict
            config_manager:     Hecos ConfigManager instance
            current_user_role:  "admin" | "user"
            current_user_id:    Username string
            session_id:         Current conversation session id
            sender_tab_id:      Browser tab id for WebUI routing
            page_context:       Page the command was issued from

        Returns:
            Standardized result dict.
        """
        result = dict(self.RESULT_TEMPLATE)
        result["command"] = raw_input.strip()

        if not raw_input.startswith("/"):
            result["error"] = "Not a slash command."
            result["output"] = "❌ Not a slash command."
            return result

        # Resolve from registry
        from .registry import get_registry
        cfg = config or (config_manager.config if config_manager else None)
        registry = get_registry(config=cfg)
        cmd = registry.resolve(raw_input)

        if cmd is None:
            parts = raw_input.strip().split(" ", 1)
            slash = parts[0]
            result["error"] = f"Unknown command: {slash}"
            result["output"] = (
                f"❌ Comando sconosciuto: `{slash}`\n\n"
                f"Digita `/help` per vedere tutti i comandi disponibili."
            )
            result["save_to_memory"] = False
            return result

        # ── RBAC check ────────────────────────────────────────────────────────
        required_role = cmd.get("requires_auth", "any")
        if required_role == "admin" and current_user_role != "admin":
            result["error"] = "Permission denied."
            result["output"] = f"❌ Questo comando richiede i permessi **admin**."
            result["save_to_memory"] = False
            return result

        # ── Parse args from raw_input ─────────────────────────────────────────
        parts = raw_input.strip().split(" ", 1)
        raw_args_str = parts[1].strip() if len(parts) > 1 else ""

        # Resolve output target: contextual → use page_context
        out_target = cmd.get("output_target", "chat")
        if out_target == "contextual":
            result["output_target"] = page_context
        else:
            result["output_target"] = out_target

        # ── Dispatch ──────────────────────────────────────────────────────────
        try:
            output_text = self._dispatch(
                cmd=cmd,
                raw_args_str=raw_args_str,
                config=cfg,
                config_manager=config_manager,
                current_user_id=current_user_id,
                session_id=session_id,
                sender_tab_id=sender_tab_id,
            )
            result["ok"] = True
            result["output"] = output_text
        except TypeError as e:
            # Likely missing required argument
            result["error"] = str(e)
            result["output"] = (
                f"❌ Argomenti errati per `{cmd['aliases'][0]}`\n\n"
                f"**Uso corretto:** `{cmd['usage']}`\n"
                f"**Esempio:** `{cmd['example']}`"
            )
            result["save_to_memory"] = False
        except Exception as e:
            _log.error(f"[HDCS Executor] Error executing {cmd['id']}: {e}", exc_info=True)
            result["error"] = str(e)
            result["output"] = f"❌ Errore durante l'esecuzione di `{cmd['aliases'][0]}`: {e}"

        # ── Save to memory ────────────────────────────────────────────────────
        if result["ok"] and result.get("save_to_memory", True):
            try:
                from hecos.memory import brain_interface
                brain_interface.save_message(
                    "user", raw_input,
                    config=cfg,
                    user_id=current_user_id,
                    session_id=session_id,
                    sender_tab_id=sender_tab_id,
                )
                brain_interface.save_message(
                    "assistant", result["output"],
                    config=cfg,
                    user_id=current_user_id,
                    session_id=session_id,
                    sender_tab_id=sender_tab_id,
                )
            except Exception as mem_e:
                _log.debug(f"[HDCS Executor] Memory save skipped: {mem_e}")

        return result

    # ── Internal dispatch ─────────────────────────────────────────────────────

    def _dispatch(
        self,
        cmd: dict,
        raw_args_str: str,
        config=None,
        config_manager=None,
        current_user_id: str = "admin",
        session_id=None,
        sender_tab_id=None,
    ) -> str:
        """
        Route a resolved command to its handler.
        - plugin_tag present → call plugin method
        - handler key present → call builtin callable
        """
        # Builtin handler (callable stored at registration time)
        handler = cmd.get("_handler")
        if handler and callable(handler):
            return handler(
                raw_args_str=raw_args_str,
                config=config,
                config_manager=config_manager,
                current_user_id=current_user_id,
                session_id=session_id,
                sender_tab_id=sender_tab_id,
            )

        # Plugin method dispatch
        plugin_tag = cmd.get("plugin_tag")
        method_name = cmd.get("method")

        if plugin_tag and method_name:
            from hecos.core.system import module_loader
            plugin_module = module_loader.get_plugin_module(plugin_tag)
            if plugin_module is None:
                raise RuntimeError(f"Plugin '{plugin_tag}' not available.")

            tools_obj = getattr(plugin_module, "tools", plugin_module)
            method = getattr(tools_obj, method_name, None)
            if method is None:
                raise RuntimeError(f"Method '{method_name}' not found on plugin '{plugin_tag}'.")

            # Smart arg injection: inspect the method signature
            kwargs = self._build_kwargs(method, raw_args_str, cmd.get("args_schema", {}))
            return method(**kwargs)

        raise RuntimeError(f"Command '{cmd['id']}' has no handler or plugin_tag/method configured.")

    def _build_kwargs(self, method, raw_args_str: str, args_schema: dict) -> dict:
        """
        Build a kwargs dict for a plugin method given the raw args string.

        Strategy:
        - If args_schema has exactly one required param → pass raw_args_str as that param
        - If args_schema is empty but method takes a param → try passing raw_args_str
        - Otherwise, pass as positional first param or skip
        """
        sig = inspect.signature(method)
        params = [
            (name, param)
            for name, param in sig.parameters.items()
            if name != "self"
        ]

        if not params:
            return {}

        # Single string param (most common): pass the entire raw_args_str
        if len(params) == 1:
            pname, param = params[0]
            # Only pass if the schema allows or there's a string value available
            if raw_args_str:
                return {pname: raw_args_str}
            elif param.default is not inspect.Parameter.empty:
                return {}  # use default
            else:
                raise TypeError(f"Missing required argument '{pname}'")

        # Multi-param: use schema to map
        kwargs = {}
        # Simple case: first required param gets the raw args string
        for pname, param in params:
            schema_type = args_schema.get(pname, "str?")
            is_optional = schema_type.endswith("?")
            if not is_optional and not raw_args_str:
                raise TypeError(f"Missing required argument '{pname}'")
            if raw_args_str:
                kwargs[pname] = raw_args_str
                break  # Only fill first explicitly; others use defaults

        return kwargs


# ── Module-level convenience function ─────────────────────────────────────────

_executor_instance: Optional[CommandExecutor] = None


def get_executor() -> CommandExecutor:
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = CommandExecutor()
    return _executor_instance
