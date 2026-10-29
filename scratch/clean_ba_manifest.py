p = r'c:\Hecos\hecos\modules\browser_automation\hpkg_manifest.toml'
with open(p, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update name and description
text = text.replace('name = "Browser Automation & Deep Search"', 'name = "Browser Automation"')
old_desc = 'description = "Hecos AI Playwright browser and Deep Search & Intelligence engine. Multi-engine ClearWeb, Tor DarkWeb (.onion), media and file hunting with dedicated /search dashboard and conversational AI search tools."'
new_desc = 'description = "Hecos AI Playwright browser automation engine. Navigate web pages, click elements, fill forms, extract reader DOM and capture screenshots."'
text = text.replace(old_desc, new_desc)

# 2. Update config_panel label
text = text.replace('tab_label = "AI Browser & Search"', 'tab_label = "AI Browser (Playwright)"')

# 3. Update routing instructions
old_routing = 'instructions = "BROWSER AUTOMATION & SEARCH EXECUTION RULES:\\n\\n1. WEB SEARCH: If the user asks you to search the web, find news, or search anything online, call BROWSER__web_search(query=...). If the query requires finding files (pdf, epub, docx), you can also call BROWSER__web_search with specific file terms or BROWSER__deep_search.\\n2. DARK WEB: If the user asks for Tor, .onion, dark web, or unrestricted search, call BROWSER__dark_search(query=...).\\n3. MEDIA: If the user asks for images, videos or music/audio, call BROWSER__media_search(query=..., media_type=...).\\n4. DEEP SEARCH: If the user asks for extensive / deep search across all clear and dark web sources, call BROWSER__deep_search(query=...).\\n5. READ WEBPAGE: If the user asks to read a specific URL, call BROWSER__fetch_page(url=...).\\n6. BROWSER INTERACTION: If the user asks to open and interact with a live browser (click, type, navigate, watch video), call BROWSER__open_url and follow standard browser automation steps."'
new_routing = 'instructions = "BROWSER AUTOMATION EXECUTION RULES:\\n\\nIf the user asks to open and interact with a live browser (click, type, navigate, watch video, take screenshots), call BROWSER__open_url and follow standard browser automation steps."'
text = text.replace(old_routing, new_routing)

# 4. Remove [ui] section so Net Search owns the pill
ui_block = '''[ui]
pill_label = "Deep Search"
pill_icon = "fas fa-radar"
pill_route = "/search"
pill_order = 45

'''
text = text.replace(ui_block, '')

# 5. Cut off search tools at BROWSER__web_search
cutoff_marker = '[[tool_schema]]\n\n[tool_schema.function]\nname = "BROWSER__web_search"'
cutoff_idx = text.find(cutoff_marker)
if cutoff_idx != -1:
    text = text[:cutoff_idx].rstrip() + '\n'

with open(p, 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated browser_automation/hpkg_manifest.toml successfully.')
