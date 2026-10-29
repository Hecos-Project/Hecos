import os, sys, json
sys.path.insert(0, r"c:\Hecos")
import sqlite3

# Test 1: PackageRegistry inspection
from hecos.core.package_manager.registry import PackageRegistry
reg = PackageRegistry(r"c:\Hecos\hecos\data")

ba = reg.get("browser_automation")
assert ba is not None, "browser_automation missing from registry"
assert ba["name"] == "Browser Automation", f"Expected 'Browser Automation', got '{ba['name']}'"
snap_ba = ba.get("manifest_snapshot")
if isinstance(snap_ba, str): snap_ba = json.loads(snap_ba)
assert snap_ba.get("name") == "Browser Automation", f"Snapshot name mismatch: {snap_ba.get('name')}"
print("PASS: browser_automation is named 'Browser Automation'")

ns = reg.get("net_search")
assert ns is not None, "net_search missing from registry"
assert ns["name"] == "Net Search"
snap_ns = ns.get("manifest_snapshot")
if isinstance(snap_ns, str): snap_ns = json.loads(snap_ns)
assert snap_ns.get("icon") == "fa-satellite-dish", f"Expected 'fa-satellite-dish', got {snap_ns.get('icon')}"
assert snap_ns.get("icon_url"), "icon_url must not be empty"
print("PASS: net_search icon and icon_url are present")

# Test 2: Net search endpoints logic
from hecos.modules.net_search.search.config import get_endpoints, update_endpoints, reset_endpoints_to_defaults
endpoints = get_endpoints()
assert "searxng" in endpoints, "searxng missing from endpoints"
assert "dark_ahmia" in endpoints, "dark_ahmia missing from endpoints"
assert "dark_torch" in endpoints, "dark_torch missing from endpoints"
assert len(endpoints["searxng"].get("fallbacks", [])) > 0, "SearXNG fallbacks empty"
print(f"PASS: endpoints loaded successfully ({len(endpoints['searxng']['fallbacks'])} SearXNG fallbacks, {len(endpoints)} total engines)")

# Test 3: config_netsearch.html content verification
cfg_html_path = r"c:\Hecos\hecos\modules\net_search\web\templates\config_netsearch.html"
with open(cfg_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

assert "endp-searxng-local-wrap" in html_content, "Missing SearXNG local wrap in html"
assert "endp-searxng-fallbacks-wrap" in html_content, "Missing SearXNG fallbacks wrap in html"
assert "endp-tor-engines-wrap" in html_content, "Missing Tor engines wrap in html"
assert "endp-custom-nodes-wrap" in html_content, "Missing Custom nodes wrap in html"
assert "window.saveEndpointsFromUI" in html_content, "Missing saveEndpointsFromUI in html"
assert "window.resetEndpointsFromUI" in html_content, "Missing resetEndpointsFromUI in html"
assert "search_endpoints.js" in html_content, "Missing search_endpoints.js script tag in html"
assert "Loading endpoints..." not in html_content, "Stale 'Loading endpoints...' table placeholder still present"
print("PASS: config_netsearch.html contains full endpoints editor")

# Test 4: netsearch_panel.js verification
js_path = r"c:\Hecos\hecos\modules\net_search\web\static\js\netsearch_panel.js"
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

assert "renderNetSearchEndpointsUI" in js_content, "Missing renderNetSearchEndpointsUI"
assert "saveEndpointsFromUI" in js_content, "Missing saveEndpointsFromUI"
assert "resetEndpointsFromUI" in js_content, "Missing resetEndpointsFromUI"
assert "addSearxngFallbackNode" in js_content, "Missing addSearxngFallbackNode"
assert "addCustomTorEngineNode" in js_content, "Missing addCustomTorEngineNode"
assert "addCustomSearchNode" in js_content, "Missing addCustomSearchNode"
print("PASS: netsearch_panel.js contains all endpoint actions and loaders")

print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
