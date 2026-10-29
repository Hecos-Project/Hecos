import sqlite3, json

conn = sqlite3.connect(r'c:\Hecos\hecos\data\packages.db')
cur = conn.cursor()

# 1. Update browser_automation
cur.execute("SELECT manifest_snapshot FROM packages WHERE id = 'browser_automation'")
row = cur.fetchone()
if row:
    snap = json.loads(row[0])
    snap['name'] = 'Browser Automation'
    snap['description'] = 'Hecos AI Playwright browser automation engine. Navigate web pages, click elements, fill forms, extract reader DOM and capture screenshots.'
    cur.execute("UPDATE packages SET name = ?, description = ?, manifest_snapshot = ? WHERE id = 'browser_automation'",
                ('Browser Automation', snap['description'], json.dumps(snap)))
    print("Updated browser_automation in packages.db")

# 2. Update net_search
cur.execute("SELECT manifest_snapshot FROM packages WHERE id = 'net_search'")
row = cur.fetchone()
if row:
    snap = json.loads(row[0])
    snap['name'] = 'Net Search'
    snap['icon'] = 'fa-satellite-dish'
    snap['icon_url'] = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview_square.png'
    snap['screenshots'] = ['https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png']
    if 'config_panel' in snap:
        snap['config_panel']['tab_icon'] = 'fa-satellite-dish'
        snap['config_panel']['css_file'] = 'web/static/css/search.css'
        snap['config_panel']['js_files'] = [
            'web/static/js/search/search_endpoints.js',
            'web/static/js/netsearch_panel.js'
        ]
    cur.execute("UPDATE packages SET name = ?, manifest_snapshot = ? WHERE id = 'net_search'",
                ('Net Search', json.dumps(snap)))
    print("Updated net_search in packages.db")

conn.commit()
conn.close()
