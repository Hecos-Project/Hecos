import json
from typing import List, Dict, Any
from hecos.core.logging import logger

# Import internal helpers
from .registry_reader import get_installed_modules, is_module_installed, get_module_info
from .store_reader import search_store, get_store_module_info
from .web_searcher import search_web_for_module
from .readme_parser import fetch_readme, parse_readme_features

class ModuleAwarenessTools:
    """
    Exposes LLM Tools to give Hecos self-awareness of its module ecosystem.
    """
    
    def __init__(self, config_manager=None, **kwargs):
        self.config_manager = config_manager
        
    def get_tool_schema(self):
        """Returns the LLM tool schemas for this plugin."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "MODULE_AWARENESS__list_installed",
                    "description": "Lists all installed Hecos modules. Returns their ID, name, version, and status.",
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
                    "name": "MODULE_AWARENESS__search_store",
                    "description": "Searches all enabled Hecos stores for modules matching a query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search term (e.g. 'weather', 'planner')"
                            },
                            "type_filter": {
                                "type": "string",
                                "description": "Optional filter by type ('plugin', 'app', etc.)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "MODULE_AWARENESS__describe_module",
                    "description": "Gets detailed info and features of a module (installed or in store), including its README if available.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "module_id": {
                                "type": "string",
                                "description": "The exact ID of the module (e.g. 'flows')"
                            }
                        },
                        "required": ["module_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "MODULE_AWARENESS__find_module_online",
                    "description": "Searches the web for Hecos modules that are not in the configured stores.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search term"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "MODULE_AWARENESS__install_module",
                    "description": "Attempts to install a module from the store or a URL. Subject to trust policies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "module_id_or_url": {
                                "type": "string",
                                "description": "The ID of the module in the store, or a direct URL to a .hpkg"
                            },
                            "user_explicitly_approved": {
                                "type": "boolean",
                                "description": "Set to true ONLY if the user explicitly asked you to install this module in their prompt."
                            }
                        },
                        "required": ["module_id_or_url"]
                    }
                }
            }
            {
                "type": "function",
                "function": {
                    "name": "MODULE_AWARENESS__add_mcp_store",
                    "description": "Adds a new MCP store URL to the system so you can search for new MCP servers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL of the MCP store JSON (e.g. https://example.com/mcp_store.json)"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "MODULE_AWARENESS__search_mcp",
                    "description": "Searches configured MCP stores for a specific Model Context Protocol server (e.g. 'sqlite', 'fetch', 'github').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search term"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
    # --- Tool Implementations ---
    
    def MODULE_AWARENESS__list_installed(self, **kwargs) -> str:
        logger.info("[ModuleAwareness] Listing installed modules.")
        modules = get_installed_modules()
        return json.dumps({"installed": modules}, indent=2)
        
    def MODULE_AWARENESS__search_store(self, query: str, type_filter: str = None, **kwargs) -> str:
        logger.info(f"[ModuleAwareness] Searching store for '{query}' (filter: {type_filter})")
        results = search_store(query, type_filter)
        return json.dumps({"results": results, "count": len(results)}, indent=2)
        
    def MODULE_AWARENESS__describe_module(self, module_id: str, **kwargs) -> str:
        logger.info(f"[ModuleAwareness] Getting description for module '{module_id}'")
        # Check installed first
        info = get_module_info(module_id)
        if not info:
            # Check store
            info = get_store_module_info(module_id)
            
        if not info:
            return json.dumps({"error": f"Module {module_id} not found."})
            
        # Try to fetch readme if url is provided in info
        readme_url = info.get("readme_url") or info.get("repository")
        features = "No readme/features available."
        if readme_url and readme_url.startswith("http"):
            # If repo, try to guess readme URL
            if "github.com" in readme_url and not readme_url.endswith(".md"):
                readme_url = readme_url.replace("github.com", "raw.githubusercontent.com") + "/main/README.md"
            raw_readme = fetch_readme(readme_url)
            features = parse_readme_features(raw_readme)
            
        return json.dumps({
            "info": info,
            "features_summary": features
        }, indent=2)
        
    def MODULE_AWARENESS__find_module_online(self, query: str, **kwargs) -> str:
        logger.info(f"[ModuleAwareness] Searching the web for module '{query}'")
        results = search_web_for_module(query)
        if not results:
            return "No results found online. Consider creating a new flow or module for this functionality."
        return json.dumps({"online_results": results}, indent=2)
        
    def MODULE_AWARENESS__install_module(self, module_id_or_url: str, **kwargs) -> str:
        """
        Installs a module by downloading it from the store or URL and using the HPM installer.
        """
        agent_cfg = self.config_manager.config.get("agent", {}) if self.config_manager else {}
        trust_mode = agent_cfg.get("autonomy_trust_mode", "ask")
        
        user_explicitly_approved = kwargs.get("user_explicitly_approved", False)
        
        if trust_mode == "ask" and not user_explicitly_approved:
            return f"Action blocked: Trust mode is set to 'ask' and user didn't explicitly request installation. Ask the user if they want to install {module_id_or_url}."
            
        try:
            import threading
            import os
            import requests
            import hecos
            
            # Determine download URL
            download_url = module_id_or_url
            if not download_url.startswith("http"):
                from .store_reader import search_store
                results = search_store(module_id_or_url)
                if not results:
                    return f"Error: Module '{module_id_or_url}' not found in any store."
                match = next((r for r in results if r["id"] == module_id_or_url), results[0])
                download_url = match.get("download_url")
                if not download_url:
                    return f"Error: No download URL found for '{module_id_or_url}'."
                    
            logger.info(f"[ModuleAwareness] Queued download: {download_url}")
            
            def _async_install():
                try:
                    logger.info(f"[ModuleAwareness:Async] Downloading {download_url}...")
                    resp = requests.get(download_url, timeout=30)
                    resp.raise_for_status()
                    hpkg_bytes = resp.content
                    
                    # Init HPM components using the official helper
                    hecos_src = os.path.dirname(hecos.__file__)
                    from hecos.modules.web_ui.routes_packages_helpers import _get_hpm_components
                    registry, installer, store_mgr = _get_hpm_components(hecos_src)
                    
                    # Perform install
                    logger.info(f"[ModuleAwareness:Async] Installing package bytes ({len(hpkg_bytes)} bytes) for {module_id_or_url}")
                    result = installer.install_bytes(hpkg_bytes, require_signature=False, skip_dep_check=False)
                    
                    if result.success:
                        logger.info(f"[ModuleAwareness:Async] Successfully installed {module_id_or_url} (ID: {result.package_id})")
                    else:
                        logger.error(f"[ModuleAwareness:Async] Installation failed for {module_id_or_url}: {result.error}")
                        
                except Exception as e:
                    logger.error(f"[ModuleAwareness:Async] Async install error for {module_id_or_url}: {e}")

            # Start thread
            t = threading.Thread(target=_async_install, daemon=True)
            t.start()
            
            return f"Installation of {module_id_or_url} has been queued in the background. It might take a few minutes if there are heavy dependencies. Let the user know you started the process and they can check the UI or ask again later."
            
        except Exception as e:
            logger.error(f"[ModuleAwareness] Install preparation error: {e}")
            return f"Failed to prepare installation: {str(e)}"

    def MODULE_AWARENESS__add_mcp_store(self, url: str, **kwargs) -> str:
        logger.info(f"[ModuleAwareness] Adding new MCP store: {url}")
        try:
            from hecos.core.system.module_loader import get_plugin_module
            mcp_module = get_plugin_module("MCP_BRIDGE", legacy=False)
            if not mcp_module:
                return "Error: mcp_bridge module is not loaded or installed. Install it first to manage MCP stores."
            cfg_mgr = getattr(mcp_module, "config_manager", None)
            if not cfg_mgr:
                return "Error: mcp_bridge does not expose config_manager."
            config = cfg_mgr.get_config()
            stores = config.get("stores", [])
            if url in stores:
                return f"The store '{url}' is already registered."
            stores.append(url)
            config["stores"] = stores
            if cfg_mgr.save_config(config):
                logger.info(f"[ModuleAwareness] MCP store added: {url}")
                return f"Successfully added MCP store: {url}. It will be included in all future MCP searches."
            else:
                return "Failed to save MCP bridge config after adding the store."
        except Exception as e:
            logger.error(f"[ModuleAwareness] add_mcp_store error: {e}")
            return f"Error adding MCP store: {e}"

    def MODULE_AWARENESS__search_mcp(self, query: str, **kwargs) -> str:
        logger.info(f"[ModuleAwareness] Searching MCP stores for '{query}'")
        import requests

        # Default store fallback
        DEFAULT_STORE = "https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/mcp_store.json"
        stores = [DEFAULT_STORE]

        # Try to read configured stores from mcp_bridge if loaded
        try:
            from hecos.core.system.module_loader import get_plugin_module
            mcp_module = get_plugin_module("MCP_BRIDGE", legacy=False)
            if mcp_module:
                cfg_mgr = getattr(mcp_module, "config_manager", None)
                if cfg_mgr:
                    config = cfg_mgr.get_config()
                    configured = config.get("stores", [])
                    if configured:
                        stores = configured
        except Exception as e:
            logger.warning(f"[ModuleAwareness] Could not read mcp_bridge stores, using default: {e}")

        results = []
        for store_url in stores:
            try:
                logger.info(f"[ModuleAwareness] Fetching MCP store: {store_url}")
                resp = requests.get(store_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # Support both `mcp_servers` and a flat list
                    servers = data.get("mcp_servers", data if isinstance(data, list) else [])
                    for srv in servers:
                        if query.lower() in srv.get("id", "").lower() or \
                           query.lower() in srv.get("name", "").lower() or \
                           query.lower() in srv.get("description", "").lower():
                            srv["_source_store"] = store_url
                            results.append(srv)
                else:
                    logger.warning(f"[ModuleAwareness] Store {store_url} returned HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"[ModuleAwareness] Failed to fetch MCP store {store_url}: {e}")

        if not results:
            return f"No MCP servers found matching '{query}' across {len(stores)} store(s). Try MODULE_AWARENESS__add_mcp_store with a new registry URL."

        return json.dumps({"mcp_results": results, "count": len(results), "stores_searched": len(stores)}, indent=2)
