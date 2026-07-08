import os

filepath = r"C:\Hecos\hecos_sdk\hecos_sdk\runner.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('plugin_dir = os.path.dirname(os.path.abspath(__file__))', 'plugin_dir = os.getcwd()')
content = content.replace('importlib.import_module("main")', 'importlib.import_module("plugin.main")')
content = content.replace('Usage (launched by ModuleBus):\n    C:\\hecos\\hpm\\image_gen\\venv\\Scripts\\python.exe runner.py', 'Usage (launched by ModuleBus):\n    python -m hecos_sdk.runner')
content = content.replace('hecos/core/ipc/runner.py', 'hecos_sdk/runner.py')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
