import json
import uuid
from typing import List, Dict, Any
from hecos.core.logging import logger

from .planner import analyze_goal_and_plan
from .executor import execute_plan
from .behavior_store import list_behaviors, save_behavior

class AutonomousAgentTools:
    """
    Exposes LLM Tools to give Hecos autonomy to act and orchestrate goals.
    """
    
    def __init__(self, config_manager=None, **kwargs):
        self.config_manager = config_manager
        
    def get_tool_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "AUTONOMOUS__plan_and_execute",
                    "description": "Given a high level goal, plans the necessary steps, identifies missing modules, and executes the plan.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {
                                "type": "string",
                                "description": "The goal to achieve (e.g., 'send me a daily weather report')"
                            }
                        },
                        "required": ["goal"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "AUTONOMOUS__schedule_behavior",
                    "description": "Schedules a recurring autonomous behavior (e.g., check emails every hour).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            },
                            "goal": {
                                "type": "string"
                            },
                            "schedule": {
                                "type": "string",
                                "description": "Cron string or description like 'daily', 'hourly'"
                            }
                        },
                        "required": ["name", "goal", "schedule"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "AUTONOMOUS__list_behaviors",
                    "description": "Lists all active autonomous behaviors.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "AUTONOMOUS__reflect",
                    "description": "Reflects on current capabilities and suggests modules that could improve autonomy.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "AUTONOMOUS__check_and_install_runtime",
                    "description": "Checks if a runtime required by an MCP server (e.g. 'node', 'python', 'uvx') is installed on this system. If it is missing, attempts to install it automatically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "runtime": {
                                "type": "string",
                                "description": "The runtime to check/install: 'node', 'python', or 'uvx'"
                            }
                        },
                        "required": ["runtime"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "AUTONOMOUS__install_mcp_server",
                    "description": "Installs and activates an MCP server by writing its configuration to mcp_bridge and triggering a hot-reload. Call AUTONOMOUS__check_and_install_runtime first if you are not sure the runtime is available.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "A unique short name for this server (e.g. 'github', 'sqlite-db')"
                            },
                            "command": {
                                "type": "string",
                                "description": "The executable to run, e.g. 'npx' or 'uvx'"
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Arguments to pass to the command, e.g. ['-y', '@modelcontextprotocol/server-github']"
                            },
                            "env": {
                                "type": "object",
                                "description": "Optional environment variables required by this server (e.g. {\"GITHUB_TOKEN\": \"...\"})"
                            }
                        },
                        "required": ["name", "command", "args"]
                    }
                }
            }
        ]
        
    # --- Tool Implementations ---
    
    def AUTONOMOUS__plan_and_execute(self, goal: str, **kwargs) -> str:
        """Analyzes the goal, checks installed modules, identifies gaps, and produces an actionable plan."""
        logger.info(f"[AutonomousAgent] Planning and executing goal: '{goal}'")
        # 1. Check installed modules via module_awareness
        try:
            from hecos.core.agent.module_awareness.plugin.registry_reader import get_installed_modules
            installed = get_installed_modules()
            installed_ids = [m.get("id", "").lower() for m in installed]
        except Exception:
            installed = []
            installed_ids = []

        # 2. Run the planner
        plan = analyze_goal_and_plan(goal, installed)

        # 3. Build a descriptive status report for the LLM to present to the user
        has_flows = any(i in installed_ids for i in ["flows", "flow_engine", "flow"])
        missing = plan.get("missing_capabilities", [])

        lines = []
        lines.append(f"# Autonomous Agent — Plan Report")
        lines.append(f"**Goal:** {goal}")
        lines.append("")
        
        # Always report installed modules count
        if installed:
            lines.append(f"**Currently installed modules ({len(installed)}):** " +
                         ", ".join(m.get("id", "?") for m in installed[:15]) +
                         ("..." if len(installed) > 15 else ""))
        else:
            lines.append("**Currently installed modules:** none detected yet (module registry may still be loading).")
        lines.append("")

        # Flows check
        if not has_flows:
            lines.append("⚠️ **Missing: `flows` module** — This module is required to schedule and automate multi-step behaviors.")
            lines.append("   → I recommend installing it from the HPM Store: search for 'flows' in the Packages panel.")
            lines.append("   → Once installed, I will be able to create and schedule this behavior automatically.")
            lines.append("")

        # Other missing capabilities
        if missing:
            lines.append(f"⚠️ **Missing capabilities for this goal:** {', '.join(missing)}")
            lines.append("   → Search the HPM Store for modules that provide these capabilities.")
            lines.append("")

        # Trust mode check for auto-install
        trust_mode = self.config_manager.config.get("trust_mode", "ask") if self.config_manager else "ask"
        if trust_mode == "ask":
            lines.append("🔒 **Trust Mode: Ask** — Automatic installation is disabled. Please install required modules manually via the Packages panel, then ask me again to schedule this behavior.")
        elif trust_mode == "trusted_only":
            lines.append("🛡️ **Trust Mode: Trusted Only** — I can auto-install from official stores.")
        elif trust_mode == "allow":
            lines.append("✅ **Trust Mode: Full Autonomy** — I can install and schedule automatically.")
        lines.append("")

        # If everything is in order, schedule it
        if has_flows and not missing:
            result = execute_plan(plan, self.config_manager)
            lines.append(f"✅ **Plan executed:** {result}")
        else:
            lines.append("**Next steps for you:**")
            if not has_flows:
                lines.append("1. Open the **Packages** panel → Store tab → search 'flows' → Install")
            for cap in missing:
                lines.append(f"2. Search the Store for a module that provides: **{cap}**")
            lines.append("3. Once all modules are installed, ask me again and I will schedule the behavior automatically.")

        return "\n".join(lines)

        
    def AUTONOMOUS__schedule_behavior(self, name: str, goal: str, schedule: str, **kwargs) -> str:
        logger.info(f"[AutonomousAgent] Scheduling behavior '{name}' (Schedule: {schedule})")
        behavior = {
            "id": str(uuid.uuid4()),
            "name": name,
            "goal": goal,
            "schedule": schedule,
            "status": "active"
        }
        if save_behavior(behavior):
            return f"Behavior '{name}' scheduled successfully. Goal: {goal}, Schedule: {schedule}."
        return "Failed to save behavior."
        
    def AUTONOMOUS__list_behaviors(self, **kwargs) -> str:
        logger.info("[AutonomousAgent] Listing active behaviors.")
        behaviors = list_behaviors()
        return json.dumps({"active_behaviors": behaviors}, indent=2)
        
    def AUTONOMOUS__reflect(self, **kwargs) -> str:
        logger.info("[AutonomousAgent] Performing self-reflection.")
        return "Reflection: I currently have basic autonomy tools. To improve, I could benefit from more specialized modules like 'web_scraper' or 'calendar_sync' to interact with the outside world more effectively."

    def AUTONOMOUS__check_and_install_runtime(self, runtime: str, **kwargs) -> str:
        """Checks if a runtime (node, python, uvx) is available and installs it if missing."""
        import subprocess, sys, platform
        logger.info(f"[AutonomousAgent] Checking runtime: {runtime}")
        
        runtime = runtime.lower().strip()
        
        def _check(cmd):
            try:
                r = subprocess.run([cmd, "--version"], capture_output=True, timeout=10)
                return r.returncode == 0, r.stdout.decode(errors="ignore").strip()
            except FileNotFoundError:
                return False, None
            except Exception as e:
                return False, str(e)
        
        if runtime in ("node", "nodejs", "npx"):
            ok, ver = _check("node")
            if ok:
                return f"Node.js is already installed: {ver}. 'npx' is included."
            # Try install via winget on Windows, brew on macOS, apt on Linux
            logger.info("[AutonomousAgent] Node.js not found. Attempting installation...")
            os_name = platform.system().lower()
            try:
                if os_name == "windows":
                    subprocess.run(["winget", "install", "OpenJS.NodeJS", "--silent", "--accept-package-agreements", "--accept-source-agreements"], check=True, timeout=180)
                elif os_name == "darwin":
                    subprocess.run(["brew", "install", "node"], check=True, timeout=180)
                else:
                    subprocess.run(["sudo", "apt-get", "install", "-y", "nodejs", "npm"], check=True, timeout=180)
                ok2, ver2 = _check("node")
                if ok2:
                    logger.info(f"[AutonomousAgent] Node.js installed successfully: {ver2}")
                    return f"Node.js installed successfully ({ver2}). You can now use 'npx' to run MCP servers."
                return "Node.js installation command ran but 'node' is still not in PATH. The user may need to restart the terminal or reboot."
            except Exception as e:
                return f"Failed to auto-install Node.js: {e}. Please install Node.js manually from https://nodejs.org."

        elif runtime in ("python", "python3"):
            ok, ver = _check("python")
            if not ok:
                ok, ver = _check("python3")
            if ok:
                return f"Python is already installed: {ver}."
            return "Python is not installed. Please install it from https://www.python.org or your OS package manager. Auto-install of Python is not safe to perform without user confirmation."

        elif runtime == "uvx":
            ok, ver = _check("uvx")
            if ok:
                return f"uvx is already installed: {ver}."
            # uvx comes with uv — install via pip or standalone installer
            logger.info("[AutonomousAgent] uvx not found. Attempting installation via 'pip install uv'...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "uv", "--quiet"], check=True, timeout=60)
                ok2, ver2 = _check("uvx")
                if ok2:
                    return f"uvx installed successfully ({ver2})."
                return "'uv' was installed but 'uvx' is not yet in PATH. Restart may be needed."
            except Exception as e:
                return f"Failed to install uvx: {e}."

        else:
            return f"Unknown runtime '{runtime}'. Supported values: 'node', 'python', 'uvx'."

    def AUTONOMOUS__install_mcp_server(self, name: str, command: str, args: list, env: dict = None, **kwargs) -> str:
        """Adds a new MCP server entry to mcp_bridge config and triggers a hot-reload."""
        logger.info(f"[AutonomousAgent] Installing MCP server '{name}' via '{command} {args}'")
        env = env or {}
        
        try:
            from hecos.core.system.module_loader import get_plugin_module
            mcp_module = get_plugin_module("MCP_BRIDGE", legacy=False)
            if not mcp_module:
                return "Error: mcp_bridge module is not installed or not loaded. Ask the user to install it from the Packages panel first."
            
            cfg_mgr = getattr(mcp_module, "config_manager", None)
            if not cfg_mgr:
                return "Error: mcp_bridge does not expose config_manager. It may need to be updated."
            
            config = cfg_mgr.get_config()
            servers = config.get("servers", {})
            
            servers[name] = {
                "type": "stdio",
                "command": command,
                "args": args,
                "env": env,
                "enabled": True
            }
            config["servers"] = servers
            
            if not cfg_mgr.save_config(config):
                return f"Failed to save mcp_bridge config while adding server '{name}'."
            
            logger.info(f"[AutonomousAgent] MCP server '{name}' saved. Triggering hot-reload...")
            
            # Trigger hot-reload on the bridge
            bridge = getattr(mcp_module, "bridge_instance", None)
            if bridge and hasattr(bridge, "reload_servers"):
                try:
                    bridge.reload_servers()
                    logger.info(f"[AutonomousAgent] MCP bridge hot-reloaded successfully.")
                    return f"MCP server '{name}' installed and activated. Its tools are now available immediately — no restart needed!"
                except Exception as e:
                    logger.warning(f"[AutonomousAgent] Hot-reload failed: {e}")
                    return f"MCP server '{name}' configuration saved but hot-reload failed ({e}). A Hecos restart may be needed to activate it."
            else:
                return f"MCP server '{name}' configuration saved. Hecos restart may be required to activate it (hot-reload endpoint not available on this version of mcp_bridge)."

        except Exception as e:
            logger.error(f"[AutonomousAgent] install_mcp_server error: {e}")
            return f"Failed to install MCP server: {e}"
