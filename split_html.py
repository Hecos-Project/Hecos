import os

src = r'c:\Hecos\hecos\modules\web_ui\templates\modules\config_browser.html'
dst = r'c:\Hecos-Packages\browser_automation_src\web\templates\config_panel.html'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

js_start = content.find('<script>')
if js_start != -1:
    js_content = content[js_start+8:content.find('</script>', js_start)]
    content = content[:js_start]
    
    headers = '''
<link rel="stylesheet" href="/hpm_plugin/browser_automation/web/static/css/browser_automation.css">
<script src="/hpm_plugin/browser_automation/web/static/js/browser_panel.js"></script>
'''
    content = headers + content
    
    js_dst = r'c:\Hecos-Packages\browser_automation_src\web\static\js\browser_panel.js'
    os.makedirs(os.path.dirname(js_dst), exist_ok=True)
    with open(js_dst, 'w', encoding='utf-8') as f:
        f.write(js_content)

css_dst = r'c:\Hecos-Packages\browser_automation_src\web\static\css\browser_automation.css'
os.makedirs(os.path.dirname(css_dst), exist_ok=True)
with open(css_dst, 'w', encoding='utf-8') as f:
    f.write('/* browser automation css */\n')

os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, 'w', encoding='utf-8') as f:
    f.write(content)
