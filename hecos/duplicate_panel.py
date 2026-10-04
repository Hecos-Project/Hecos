import os

src_html = r'c:\Hecos\hecos\modules\web_ui\templates\modules\chat_global_presets.html'
dst_html = r'c:\Hecos\hecos\modules\web_ui\templates\modules\chat_session_overrides.html'
with open(src_html, 'r', encoding='utf-8') as f:
    html_content = f.read()

html_content = html_content.replace('id="sf-', 'id="so-')
html_content = html_content.replace('for="sf-', 'for="so-')
html_content = html_content.replace('window.sf', 'window.so')
html_content = html_content.replace('soul-forge-panel', 'session-overrides-panel')
html_content = html_content.replace('soul-forge-overlay', 'session-overrides-overlay')

with open(dst_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

src_dir = r'c:\Hecos\hecos\modules\web_ui\static\js\global_presets'
dst_dir = r'c:\Hecos\hecos\modules\web_ui\static\js\session_overrides'
os.makedirs(dst_dir, exist_ok=True)

for file in os.listdir(src_dir):
    if file.endswith('.js'):
        with open(os.path.join(src_dir, file), 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('window.sf', 'window.so')
        content = content.replace("'sf-", "'so-")
        content = content.replace('"sf-', '"so-')
        content = content.replace('soul-forge-panel', 'session-overrides-panel')
        content = content.replace('soul-forge-overlay', 'session-overrides-overlay')
        content = content.replace('Global Defaults', 'Chat Overrides')
        
        new_file = file.replace('gp_', 'so_')
        with open(os.path.join(dst_dir, new_file), 'w', encoding='utf-8') as f:
            f.write(content)

print('Duplication complete.')
