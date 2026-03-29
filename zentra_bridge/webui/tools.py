"""
MODULE: zentra_bridge/webui/tools.py
DESCRIPTION: Loads Zentra plugins, builds OpenAI-compatible JSON schema list, and
             executes tool calls returned by the LLM (both native JSON tool-calls
             and legacy tag-based commands handled by the tag executor).
"""

import os
import json
import inspect
import logging
import importlib
from typing import Any, Dict, List, Optional

bridge_logger = logging.getLogger("WebUI_Bridge")

# ---------------------------------------------------------------------------
# Plugin loading helpers
# ---------------------------------------------------------------------------

_PLUGIN_MODULE_MAP: Dict[str, str] = {
    "DASHBOARD":    "plugins.dashboard.main",
    "DOMOTICA":     "plugins.domotica.main",
    "EXECUTOR":     "plugins.executor.main",
    "FILE_MANAGER": "plugins.file_manager.main",
    "HELP":         "plugins.help.main",
    "MEDIA":        "plugins.media.main",
    "MEMORY":       "plugins.memory.main",
    "MODELS":       "plugins.models.main",
    "ROLEPLAY":     "plugins.roleplay.main",
    "WEBCAM":       "plugins.webcam.main",
}

# Cached instances of loaded plugin objects
_plugin_instances: Dict[str, Any] = {}


def _load_plugin(tag: str) -> Optional[Any]:
    """Lazily loads and caches the plugin class instance for a given tag."""
    if tag in _plugin_instances:
        return _plugin_instances[tag]

    module_path = _PLUGIN_MODULE_MAP.get(tag)
    if not module_path:
        return None

    try:
        mod = importlib.import_module(module_path)
        # The plugin exposes a module-level ``tools`` instance
        instance = getattr(mod, "tools", None)
        if instance is not None:
            _plugin_instances[tag] = instance
            bridge_logger.info(f"[TOOLS] Loaded plugin: {tag}")
            return instance
    except Exception as exc:
        bridge_logger.warning(f"[TOOLS] Cannot load plugin '{tag}': {exc}")

    return None


# ---------------------------------------------------------------------------
# Schema building (OpenAI function-calling format)
# ---------------------------------------------------------------------------

def _python_type_to_json(annotation) -> str:
    """Maps Python type annotations to JSON Schema type strings."""
    if annotation in (int,):
        return "integer"
    if annotation in (float,):
        return "number"
    if annotation in (bool,):
        return "boolean"
    return "string"  # default


def _build_function_schema(tag: str, method_name: str, method) -> Dict:
    """Generates a single OpenAI-compatible function schema from a plugin method."""
    # Description: prefer docstring, fall back to registry description
    doc = inspect.getdoc(method) or f"Executes {tag}.{method_name}"
    first_line = doc.split("\n")[0].strip()

    sig = inspect.signature(method)
    properties: Dict[str, Dict] = {}
    required: List[str] = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = "string"
        if param.annotation != inspect.Parameter.empty:
            param_type = _python_type_to_json(param.annotation)

        # Derive description from docstring :param <name>: lines
        param_doc = ""
        for line in doc.split("\n"):
            if f":param {param_name}:" in line:
                param_doc = line.split(":", 2)[-1].strip()
                break

        properties[param_name] = {
            "type": param_type,
            "description": param_doc or param_name,
        }

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": f"{tag}__{method_name}",   # double-underscore namespace separator
            "description": first_line,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def build_tool_schemas(registry_path: str) -> List[Dict]:
    """
    Reads the core registry and builds the full OpenAI-compatible ``tools`` list.
    Only class-based plugins are exposed (legacy tag plugins are excluded).

    Args:
        registry_path: Absolute path to ``core/registry.json``.

    Returns:
        A list of function-schema dicts suitable for the ``tools=`` parameter.
    """
    if not os.path.exists(registry_path):
        bridge_logger.warning(f"[TOOLS] Registry not found: {registry_path}")
        return []

    try:
        with open(registry_path, "r", encoding="utf-8") as fh:
            registry: Dict = json.load(fh)
    except Exception as exc:
        bridge_logger.error(f"[TOOLS] Cannot read registry: {exc}")
        return []

    schemas: List[Dict] = []

    for tag, info in registry.items():
        if not info.get("is_class_based"):
            continue  # Skip legacy plugins

        instance = _load_plugin(tag)
        if instance is None:
            continue

        for method_name in info.get("commands", {}).keys():
            method = getattr(instance, method_name, None)
            if method is None or not callable(method):
                continue
            try:
                schema = _build_function_schema(tag, method_name, method)
                schemas.append(schema)
            except Exception as exc:
                bridge_logger.warning(
                    f"[TOOLS] Schema build failed for {tag}.{method_name}: {exc}"
                )

    bridge_logger.info(f"[TOOLS] Built {len(schemas)} tool schemas.")
    return schemas


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def execute_tool_call(tool_name: str, arguments: Dict) -> str:
    """
    Dispatches a single tool call to the correct plugin method and returns
    the result as a JSON string.

    ``tool_name`` uses the double-underscore namespace format: "TAG__method".

    Args:
        tool_name:  The function name as returned by the LLM (e.g. "EXECUTOR__execute_shell").
        arguments:  Dict of keyword arguments to pass to the method.

    Returns:
        A JSON string containing either the result or an error description.
    """
    try:
        tag, method_name = tool_name.split("__", 1)
    except ValueError:
        return json.dumps({"error": f"Invalid tool name format: '{tool_name}'"})

    instance = _load_plugin(tag)
    if instance is None:
        return json.dumps({"error": f"Plugin '{tag}' not available."})

    method = getattr(instance, method_name, None)
    if method is None or not callable(method):
        return json.dumps({"error": f"Method '{method_name}' not found in plugin '{tag}'."})

    try:
        result = method(**arguments)
        # Ensure result is serialisable
        if isinstance(result, str):
            return json.dumps({"result": result})
        return json.dumps({"result": str(result)})
    except Exception as exc:
        bridge_logger.error(f"[TOOLS] Execution error for {tool_name}: {exc}")
        return json.dumps({"error": str(exc)})
