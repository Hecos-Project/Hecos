import sys
sys.path.insert(0, r"c:\Hecos")

print("=== [1] Verifying net_search module ===")
from hecos.modules.net_search import tools as ns_tools
print(f"NetSearch tag: {ns_tools.tag}")
print(f"NetSearch category: {ns_tools.category}")
print(f"NetSearch slash commands: {ns_tools.slash_commands}")
assert ns_tools.tag == "NETSEARCH"
assert hasattr(ns_tools, "web_search")
assert hasattr(ns_tools, "dark_search")
assert hasattr(ns_tools, "deep_search")
assert hasattr(ns_tools, "media_search")
assert hasattr(ns_tools, "fetch_page")
print("NetSearch tools verified OK!")

print("\n=== [2] Verifying browser_automation module ===")
from hecos.modules.browser_automation import tools as ba_tools
print(f"Browser tag: {ba_tools.tag}")
print(f"Browser category: {ba_tools.category}")
print(f"Browser slash commands: {ba_tools.slash_commands}")
assert ba_tools.tag == "BROWSER"
assert hasattr(ba_tools, "open_url")
assert hasattr(ba_tools, "click_element")
assert hasattr(ba_tools, "screenshot")
assert not hasattr(ba_tools, "dark_search"), "dark_search should no longer be on BrowserTools"
print("BrowserTools verified clean OK!")

print("\n=== [3] Verifying PackageRegistry ===")
from hecos.core.package_manager.registry import PackageRegistry
reg = PackageRegistry(r"c:\Hecos\hecos\data")
pkg = reg.get("net_search")
assert pkg is not None
assert pkg["type"] == "system_app"
assert pkg["status"] == "installed"
print(f"Package 'net_search' registered as {pkg['type']} ({pkg['status']})")

print("\n=== [4] Verifying Hub Panel Discovery ===")
from hecos.modules.web_ui.routes_config_ui import _discover_hpm_panel
ns_panel = _discover_hpm_panel("netsearch")
print(f"NetSearch panel template: {ns_panel}")
assert ns_panel is not None and "config_netsearch.html" in ns_panel

print("\n=== [5] Verifying Capabilities Scanner ===")
import hecos.core.system.module_scanner as ms
caps = ms.update_capability_registry()
print(f"Total active capabilities: {len(caps)}")
assert "NETSEARCH" in caps
assert "BROWSER" in caps
print("All verifications PASSED successfully!")
