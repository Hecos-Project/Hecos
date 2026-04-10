# 🔌 Plugins Development Guide (v0.15.2)

## 1. Overview
Plugins in Zentra Core are modular extensions located in the `plugins/` directory. Each plugin is a self-contained folder that follows a specific structure and interface.

---

## 2. Plugin Structure
A standard plugin directory should look like this:
```text
plugins/my_plugin/
├── __init__.py
├── main.py        # Core logic
└── config.json    # (Optional) Plugin-specific settings
```

The system automatically scans `plugins/` and registers the capabilities found.

---

## 3. Native Function Calling (Recommended)
Zentra Core uses **LiteLLM Tools** (OpenAI JSON Schema) to allow AI to call Python functions directly.

### Step 1: Define the `Tools` class in `main.py`
```python
class Tools:
    def greet_user(self, name: str):
        """
        Greets the user by name.
        :param name: The name of the person to greet.
        """
        return f"Hello, {name}! I am Zentra."

# Export tool instance
tools = Tools()
```

### Step 2: The system handles registration
The `plugin_loader.py` will automatically extract the function name, its arguments, and its docstring to build the JSON Schema that is sent to the LLM. No manual JSON writing is required if you follow standard docstring formats.

---

## 4. Legacy Pattern (Regex Tags)
If you prefer not to use native function calling, you can use the legacy `esegui` method. Zentra will look for tags like `[MY_PLUGIN: action]` in the AI response.

```python
def esegui(comando: str):
    """
    Standard entry point for legacy tag processing.
    """
    if "greet" in comando:
        return "Hello from legacy plugin!"
    return None
```

---

## 5. Plugin Guidelines
- **Return Type**: Functions should return strings or JSON-serializable objects. 
- **Dependency**: If your plugin requires external libraries, list them in `requirements.txt` at the root.
- **Security**: Never use `eval()` on AI input. Use the provided `executor` plugin for controlled system commands.
- **Config Access**: Plugins can access their own config through the `ConfigManager` or via a local `config.json`.
- **I18N Support**: New plugins should use the `core/i18n` system for any user-facing strings to support English, Italian, and Spanish.

---

## 6. Example: Simple Calculator Plugin
```python
# plugins/calculator/main.py

class Tools:
    def add(self, a: float, b: float):
        """Adds two numbers."""
        return str(a + b)

    def multiply(self, a: float, b: float):
        """Multiplies two numbers."""
        return str(a * b)

tools = Tools()
```
*When activated, the AI will automatically know it can call `tools__add` or `tools__multiply` when math is requested.*

---

## 7. Lazy Loading & Manifest Sync (v0.15.2+)
To improve startup speed, plugins can now be loaded lazily. Instead of importing the Python module at boot, Zentra reads a `manifest.json` file.

### manifest.json structure:
```json
{
    "tag": "MY_PLUGIN",
    "description": "Short description for the AI",
    "lazy_load": true,
    "commands": {
        "my_command": "Description of what it does"
    },
    "tool_schema": [
        {
            "type": "function",
            "function": {
                "name": "MY_PLUGIN__my_command",
                "parameters": { ... JSON Schema ... }
            }
        }
    ]
}
```
**Benefits:**
- **Zero-boot time:** The Python file is only executed when the AI actually calls the tool.
- **Memory efficiency:** Dormant plugins don't consume VRAM or RAM.

---

## 8. Remote Client Redirection (Camera)
Zentra can now trigger actions directly on the user's browser/phone instead of the server hardware.

**Pattern:**
1. Your tool returns a unique token (e.g., `[CAMERA_SNAPSHOT_REQUEST]`).
2. `core/agent/loop.py` intercepts this token and short-circuits the AI reasoning.
3. `routes_chat.py` detects the token and emits a dedicated **SSE Event** (e.g., `camera_request`).
4. The WebUI (via `client_camera.js`) reacts to this event by injecting a visible UI button.
5. The button click triggers a native browser capability (like `camera.capture`).

---

## 9. Extension Architecture (JIT Modules)
In version 0.12.0, Zentra introduced **Extensions**, which are dynamically loaded sub-plugins encapsulated inside specific master plugins (e.g., Code Editor inside the Drive plugin).

### Key Features:
- **JIT Loading**: Extensions are only loaded into memory when specifically requested by the master plugin.
- **Isolated Routing**: Each extension can have its own Flask Blueprint with its own templates and static files.
- **Auto-Config**: Extensions append their settings to the master plugin's configuration block in `system.yaml`.

### Directory Structure:
```text
plugins/drive/
├── extensions/
│   └── editor/
│       ├── manifest.json  # Metadata (parent_plugin, version, config_schema)
│       ├── main.py        # Must define init_routes(app)
│       ├── templates/     # HTML templates for the extension
│       └── static/        # JS/CSS for the extension
```

### Implementation Example (Master Plugin `routes.py`):
```python
from core.system.extension_loader import load_extension_routes, discover_extensions

def init_drive_routes(app, logger):
    # 1. Discover extensions in the master plugin directory
    discover_extensions("DRIVE", os.path.dirname(__file__))
    
    # 2. JIT Load a specific extension
    load_extension_routes(app, "DRIVE", "editor", logger)
```

### Implementation Example (Extension `main.py`):
```python
from flask import Blueprint, render_template

editor_bp = Blueprint("zentra_editor", __name__, 
                      template_folder="templates", 
                      static_folder="static", 
                      static_url_path="/editor_static")

def init_routes(app):
    """Entry point called by extension_loader"""
    if "zentra_editor" not in app.blueprints:
        app.register_blueprint(editor_bp)
```

**Developer Tip:** The `extension_loader` automatically registers the extension module in `sys.modules`. This ensures that Flask can correctly resolve the filesystem location for `template_folder` and `static_folder` even though the module was loaded dynamically via `importlib`.
