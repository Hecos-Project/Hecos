# Anatomy of a Hecos Package (HPM)

This guide explains in detail how a Hecos package (`.hpkg`) is structured, what each file does, which paths to follow, and how to create a working package from scratch — even if you are a beginner.

---

## What Is a Hecos Package?

The term "Package" refers to the distribution format (`.hpkg`), but inside it can be any type of **Hecos Module**. Hecos is designed to grow with you. Thanks to the Hecos Package Manager (HPM), the system is infinitely expandable.

A package is not necessarily just a plugin; it can be any of these categories:

- **Plugins & Core Modules**: Add native integrations like PC/Browser automation, email clients, messenger bridges, and image generation.
- **Autonomous Apps**: Install full web applications that run entirely locally within the Hecos ecosystem (e.g., calendars, lists, mail managers). Unlike plugins, these have their own independent UI and a strong separate logic.
- **Control Room Widgets**: Expand your system dashboard with new real-time monitoring tools and live telemetry.
- **Personas & Themes**: Customize the look, feel, and "soul" (behavior and prompts) of your agent.

Regardless of the type, all modules share the same distribution format: a cryptographically signed ZIP archive with the `.hpkg` extension. Inside, they can combine one or more components: backend logic, user interfaces (HTML/JS/CSS), and API routes.

Once installed via HPM, the package is extracted to:
```
C:\Hecos\hecos\hpm\<package_id>\
```

---

## Standard Source Folder Structure

> By convention, source folders are named `<package_id>_src` and live in `C:\Hecos-Packages\`.

### Basic Package (backend plugin only)

```text
my_package_src/
|-- hpkg_manifest.toml        # [REQUIRED] Main package manifest
|-- main.py                   # [REQUIRED] Entry point -- must expose a `tools` object
|-- README.md                 # [REQUIRED] Package documentation
|-- preview.png               # [OPTIONAL] Preview image for the Store
|-- CHANGELOG.md              # [OPTIONAL] Version history
```

### Full Package (plugin + config panel + API routes)

```text
my_package_src/
|-- hpkg_manifest.toml
|-- main.py                               # Root entry point (re-exports from plugin/)
|-- README.md
|-- preview.png
|
|-- plugin/                               # Backend logic
|   |-- __init__.py
|   |-- main.py                           # Tools class -- LLM tools
|   |-- generator.py                      # Additional logic modules
|   |-- providers/                        # Sub-modules (optional)
|       |-- __init__.py
|       |-- my_provider.py
|
|-- my_package_config/                    # Autonomous package config
|   |-- __init__.py
|   |-- config_manager.py                 # TOML read/write
|   |-- defaults.toml                     # Default values
|
|-- web/                                  # Config Panel frontend
    |-- routes.py                         # Custom Flask routes
    |-- templates/
    |   |-- config_panel.html             # HTML panel fragment
    |-- static/
        |-- css/
        |   |-- my_style.css
        |-- js/
            |-- my_panel.js
```

---

## The Manifest: hpkg_manifest.toml

The manifest is the heart of the package. HPM reads it to know everything about the package.

### Identity Section (required)

```toml
id = "my_package"              # Unique snake_case identifier
name = "My Package"            # Human-readable name for Store/Hub
version = "1.0.0"              # Semantic version (MAJOR.MINOR.PATCH)
hecos_min_version = "0.39.0"   # Minimum required Hecos version
author = "Your Name"
license = "GPL-3.0"
description = "Short, clear description of the package."
icon = "emoji"
category = "PLUGINS"           # PLUGINS | MULTIMEDIA | CONNETTIVITA | UTILITY
type = "plugin"                # plugin | widget | extension
```

### Runtime Section (backend plugin)

```toml
plugin_tag = "MY_PACKAGE"      # Unique UPPERCASE tag
is_class_based = true          # true = Tools class; false = flat module
plugin_dir = "."               # Plugin root folder
lazy_load = true               # true = loaded only when needed
```

### Python Dependencies

```toml
pip_requirements = [
    "requests",
    "httpx",
]
python_requires = ">=3.11"
dependencies = []              # Dependencies on other HPM packages
```

### LLM Routing

```toml
[routing]
instructions = "[MY_PACKAGE: do_something:description] - Use this tool only if..."
```

### Slash Commands

```toml
[[slash_commands]]
id = "my_cmd"
aliases = ["/my", "/cmd"]
description = "Does something useful"
usage = "/my <argument>"
example = "/my practical example"
icon = "emoji"
method = "do_something"        # Method name in the Tools class
requires_args = true
```

### Tool Schema (for LLM)

```toml
[[tool_schema]]
name = "MY_PACKAGE__do_something"
description = "Tool description for the LLM."

[tool_schema.parameters]
type = "object"
required = ["input"]

[tool_schema.parameters.properties.input]
type = "string"
description = "The user input."
```

### Config Panel

```toml
[config_panel]
tab_id = "my_tab"
tab_label = "My Panel"
category = "UTILITY"
tab_icon = "<i class=\"fas fa-cog\"></i>"
template_file = "web/templates/config_panel.html"
js_file = "web/static/js/my_panel.js"
css_file = "web/static/css/my_style.css"
api_routes_file = "web/routes.py"
config_api_get = "/hecos/api/plugins/my_package/config"
config_api_post = "/hecos/api/plugins/my_package/config"
```

### Capabilities

```toml
[capabilities]
llm_tools = ["MY_PACKAGE__do_something"]
slash_commands = ["/my", "/cmd"]
has_widget = false
has_config_panel = true
has_api_routes = true
has_system_calls = false
notes = "Additional notes for users."
```

---

## The Backend: plugin/main.py

```python
"""
MODULE: My Package
"""
from hecos.core.logging import logger

class MypackageTools:
    def __init__(self):
        self.tag = "MY_PACKAGE"

    def status(self) -> str:
        return "Loaded"

    def do_something(self, input: str) -> str:
        logger.info(f"[MY_PACKAGE] Called with: {input}")
        return f"Result for: {input}"

tools = MypackageTools()
```

### Root entry point (root main.py)

```python
"""
Root entry point -- re-exports from plugin/ folder.
The module_scanner looks for the tools object here.
"""
from .plugin.main import tools, status
```

---

## Autonomous Configuration

> **⚠️ Updated Approach (Hecos 0.40+)**  
> The old system based on `defaults.toml` + custom code is **deprecated**. All packages now use **`HPMBaseConfigManager` (Pydantic + TOML)**.  
> Read the full guide: **[`07_package_config_system_en.md`](file:///C:/Hecos/docs/tech/07_package_config_system_en.md)**

Each package has its own private TOML file (never write to Hecos global config). Default values are declared directly in the Pydantic model fields. Minimum structure:

```text
my_package_config/
├── __init__.py          # Empty
└── config_manager.py   # Pydantic schema + HPMBaseConfigManager
```

Quick start:

```python
# my_package_config/config_manager.py
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager: pass

class MyPkgConfig(BaseModel):
    enabled: bool = True
    provider: str = "default"
    api_key: str = ""
    timeout: int = 30

_CONFIG_FILE = Path(__file__).parent / "my_package.toml"
_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(MyPkgConfig, _CONFIG_FILE, "my_package")

def get_config() -> dict:
    if _manager: return {"my_package": _manager.get().model_dump(mode='json')}
    return {"my_package": MyPkgConfig().model_dump(mode='json')}

def save_config(data: dict) -> bool:
    if _manager and "my_package" in data:
        obj = MyPkgConfig.model_validate(data["my_package"])
        return _manager.save(obj)
    return False

def get_config_obj() -> MyPkgConfig:
    return _manager.get() if _manager else MyPkgConfig()
```

See [`07_package_config_system_en.md`](file:///C:/Hecos/docs/tech/07_package_config_system_en.md) for the full guide with nested sub-models, merge pattern, checklists and troubleshooting.

---


## API Routes: web/routes.py

The init function has a mandatory signature:

```python
from flask import request, jsonify

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os, sys

    # Add the package folder to sys.path for relative imports
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)

    from my_package_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/my_package/config", methods=["GET"])
    def get_my_config():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/my_package/config", methods=["POST"])
    def post_my_config():
        data = request.get_json(force=True)
        ok = save_config(data)
        return jsonify({"ok": ok})
```

> All endpoints must follow `/hecos/api/plugins/<package_id>/...`

---

## Frontend: Config Panel

### web/templates/config_panel.html

HTML fragment (no `<html>`, `<head>`, `<body>`):

```html
<div id="tab-my_tab" class="panel module-config-panel">
  <div class="card">
    <!-- Use data-icon-injected="true" if you use display:flex to avoid double icons -->
    <div class="card-title" data-icon-injected="true" style="display:flex; justify-content:space-between; align-items:center;">
        <span><i class="fas fa-cog"></i> Settings</span>
    </div>
    
    <div class="field">
      <label for="my-provider">Provider</label>
      <select id="my-provider" class="config-input">
        <option value="default">Default</option>
      </select>
    </div>
    <button onclick="myPanel.save()" class="btn btn-primary">Save</button>
  </div>
</div>
```

> **UI Best Practices**:
> - Use native Hecos CSS classes: `.card`, `.card-title`, `.field`, `.config-input`, `.btn btn-primary`.
> - **CRITICAL**: Hecos automatically injects an icon into every `.card-title`. If your div uses `display:flex` (e.g., to put buttons on the right), add `data-icon-injected="true"` or the injector will destroy your layout.

### web/static/js/my_panel.js

```javascript
const myPanel = (() => {
  const API_GET  = "/hecos/api/plugins/my_package/config";
  const API_POST = "/hecos/api/plugins/my_package/config";

  async function init() {
    const res = await fetch(API_GET);
    if (!res.ok) return;
    const cfg = await res.json();
    document.getElementById("my-provider").value = cfg.my_package?.provider || "default";
  }

  async function save() {
    const payload = { my_package: { provider: document.getElementById("my-provider").value } };
    const res = await fetch(API_POST, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    // Use native Hecos banners (window.showToast), NEVER window.saveConfig(true)
    if (data.ok) window.showToast("Saved!", "success");
  }

  // HTML is injected dynamically, DOMContentLoaded will not work here.
  // Use a MutationObserver or expose the init function to be called by the Hub.
  const observer = new MutationObserver((mutations) => {
    if (document.getElementById("my-provider")) {
      init();
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  return { init, save };
})();
```

---

## Legacy Compatibility (`config_defaults`)

In older packages, configuration was injected into `system.yaml` via `[config_defaults]`. **This approach is deprecated**. The only allowed use today is to tell the Hub that the plugin is active, if strictly necessary:

```toml
[config_defaults]
enabled = true   # Only this. Nothing else.
```

---

## Static Asset URLs

JS/CSS files are served by Flask via:
```
/hpm_plugin/<package_id>/<relative_path>
```
Example: `/hpm_plugin/image_gen/web/static/js/igen_panel.js`

These URLs are generated automatically by the Hub from the `js_file` and `css_file` fields in the manifest.

---

## Widgets

The widget structure is different from the config panel. Each widget has its own folder with a `manifest.json`:

```text
my_widget/
|-- manifest.json       # Widget JSON manifest
|-- main.py             # Backend logic
|-- __init__.py
|-- templates/
    |-- my_widget.html
```

Declaration in the main TOML manifest:
```toml
[[widgets]]
id = "my_widget"
label = "My Widget"
icon = "fa-star"
extension_path = "my_widget/"
has_room_view = true
```

---

## v2 Isolated Packages — Modules with a Dedicated Process

> **This chapter describes an advanced feature.** For the vast majority of plugins, the v1 structure described above is sufficient and recommended. Read the [When to use v2](#when-to-use-v2-isolated) section before proceeding.

### What changes in v2?

In a **v1 (shared)** package, the plugin's Python code runs **inside the main Hecos process**. It shares the same Python interpreter, libraries, and memory.

In a **v2 (isolated)** package, Hecos launches a **separate Python subprocess** for that module, with its own private `venv` and communication via **IPC (socket)**. The Core and the module communicate by exchanging JSON messages, exactly like a microservice.

| | **v1 — Shared** | **v2 — Isolated** |
|---|---|---|
| `pip_isolation` in TOML | `"shared"` | `"isolated"` |
| System process | Same as Hecos | Dedicated subprocess |
| Python environment | Shared with core | Private `venv` installed with the package |
| RAM overhead | ~0 MB extra | ~30–80 MB per subprocess |
| Latency per call | ~0 ms | ~5–20 ms (IPC) |
| Crash isolation | No | Yes — a crash in the module does not take down the core |
| Hot update | No | Yes — only restarts the subprocess |
| Pip dependencies | Installed in core | Fully autonomous in the local `venv` |

### Source Folder Structure (v2)

```text
my_module_src/
|-- hpkg_manifest.toml            # Like v1, but with pip_isolation = "isolated"
|-- manifest.json                 # Runtime manifest for Hecos (same as v1)
|-- main.py                       # IPC entrypoint (uses hecos_sdk, not a direct class)
|-- README.md
|-- preview.png
|-- routing_override.yaml         # [OPTIONAL] AI instruction override for this module
|
|-- plugin/                       # Business logic
|   |-- __init__.py
|   |-- core_logic.py
|
|-- web/                          # Flask routes mounted by Hecos
|   |-- routes.py                 # init_plugin_routes() — same signature as v1
|   |-- static/
|   |   |-- js/
|   |   |-- css/
|   |-- templates/
|       |-- config_panel.html
|
|-- my_module_config/             # Autonomous config manager (identical to v1)
|   |-- __init__.py
|   |-- config_manager.py
```

> After installation, HPM automatically creates the `venv/` folder inside the package directory and installs the dependencies declared in `[dependencies_python]`.

### main.py (v2) — The IPC Runner

In v2, `main.py` does not expose a `tools` object. Instead, it uses `hecos_sdk` to manage an **IPC message receive loop** from the Core. The Core calls methods through the internal protocol; the subprocess returns the result.

```python
"""
Entrypoint for the isolated subprocess of MyModule.
Uses hecos_sdk.runner to handle IPC calls from Hecos Core.
"""
from hecos_sdk import runner, logger
from plugin.core_logic import MyLogic

def handle_call(method: str, params: dict) -> dict:
    """Dispatcher: receives a call from Core and returns the result."""
    logic = MyLogic()
    if method == "do_something":
        return logic.do_something(**params)
    raise ValueError(f"Unknown method: {method}")

if __name__ == "__main__":
    logger.info("[MyModule] Subprocess started")
    runner.run(handle_call)
```

> **Note:** `hecos_sdk` is the library installed in the v2 module's `venv`. It provides `runner.run()` for the IPC loop and `logger` for unified logging with the core.

### hpkg_manifest.toml (v2) — Key Differences

The only differences from the v1 manifest are:

```toml
# --- V2 KEY ---
pip_isolation = "isolated"    # ← This is all that distinguishes v1 from v2

# --- DEPENDENCIES (installed in the module's private venv) ---
[dependencies_python]
packages = [
    "torch>=2.0",
    "diffusers>=0.25",
    "transformers>=4.35",
    "Pillow>=10.0",
    "hecos_sdk",              # Required in v2
]
```

> All other sections (`[config_panel]`, `[tool_schema]`, `[[slash_commands]]`, etc.) are **identical to v1**.

### web/routes.py (v2)

The `init_plugin_routes()` signature is **identical to v1**. Hecos mounts it on the main Flask server, regardless of subprocess isolation.

```python
from flask import request, jsonify

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os, sys
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)

    from my_module_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/my_module/config", methods=["GET"])
    def get_my_module_config():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/my_module/config", methods=["POST"])
    def post_my_module_config():
        data = request.get_json(force=True)
        ok = save_config(data)
        return jsonify({"ok": ok})
```

### routing_override.yaml — Autonomous AI Override

A v2 package can include a `routing_override.yaml` file in its root directory to override the AI instructions **specific to that module**, without touching the global Hecos configuration (`routing_overrides.yaml`).

```yaml
# routing_override.yaml (in the installed package root)
enabled: true
instruction: >
  Only generate images if explicitly requested. For real-world photos, suggest
  using the camera. For creative or complex anatomical requests, adopt a style
  like 'fine-art photography', 'classic anatomy', or 'cinematic lighting'
  to ensure professional, high-quality aesthetic output.
```

> **User note:** This file can be edited directly from the **"Brain Routing Override"** field in the plugin's config panel, without opening YAML files manually.

### Fast Reinstall (v2 only)

v2 packages with heavy dependencies support **Fast Reinstall**: drag the `.hpkg` onto the Package Manager and enable the **Fast Reinstall** flag. Hecos will reinstall the package files, skipping the `pip install` phase and using the dependencies already present in the local `venv`.

> **Important:** Fast Reinstall works **only if you reinstall without uninstalling first**. If you uninstall, Hecos removes the `venv` and dependencies must be reinstalled from scratch.

### When to use v2 Isolated

```
Does your plugin have heavy or potentially conflicting pip dependencies
with other libraries in the Hecos core?
(e.g. torch, tensorflow, diffusers, opencv with CUDA, etc.)
         │
         ├─ YES ──► Use v2 Isolated
         │           pip_isolation = "isolated"
         │           Your plugin gets a dedicated subprocess and venv
         │           Ideal for: Image Gen, local AI models, ML
         │
         └─ NO  ──► Use v1 Shared  ← the right choice in most cases
                     pip_isolation = "shared"
                     Direct integration, zero overhead
                     Ideal for: Calendar, Reminder, Weather, Webcam,
                     Quick Links, Voice Visualizer, Media Player, etc.
```

**Practical examples:**

| Module | Format | Reason |
|---|---|---|
| `image_gen` | **v2 Isolated** | torch, diffusers, huggingface — huge dependencies |
| `calendar` | **v1 Shared** | No heavy dependencies |
| `reminder` | **v1 Shared** | Standard scheduler logic |
| `weather_pro` | **v1 Shared** | Only `requests` |
| `voice_visualizer` | **v1 Shared** | Pure widget, zero dependencies |
| `media_player` | **v1 Shared** | Audio dependencies manageable in core |
| Local LLM plugin | **v2 Isolated** | llama-cpp-python — separate environment required |

---

## Package Lifecycle

```
1. Development  ->  *_src/ folder with hpkg_manifest.toml
2. Build        ->  HPM Builder creates signed .hpkg (Ed25519)
3. Install      ->  HPM extracts to hecos/hpm/<id>/
4. Boot         ->  LOADER loads the plugin; Flask registers API routes
5. Hub          ->  Reads manifest.json and injects HTML/JS/CSS in browser
```

---

## Runtime Installation Paths

| Resource | Path |
|---|---|
| Full package | `C:\Hecos\hecos\hpm\<id>\` |
| Runtime manifest | `C:\Hecos\hecos\hpm\<id>\manifest.json` |
| Private TOML config | `C:\Hecos\hecos\hpm\<id>\<id>_config\<id>.toml` |
| Config panel HTML | `C:\Hecos\hecos\hpm\<id>\web\templates\` |
| Static JS/CSS | `C:\Hecos\hecos\hpm\<id>\web\static\` |

---

## Conventions and Rules

1. **Package `id`**: always `snake_case` lowercase. E.g.: `image_gen`, `my_weather`.
2. **`plugin_tag`**: always `SCREAMING_SNAKE_CASE`. E.g.: `IMAGE_GEN`, `MY_WEATHER`.
3. **Autonomous config**: never write to the global Hecos config. Use a private TOML in `<id>_config/`.
4. **Imports in routes.py**: always use `sys.path.insert` to add the package folder, since the file is loaded dynamically outside the Python package context.
5. **API endpoints**: always follow the pattern `/hecos/api/plugins/<id>/<resource>`.
6. **No browser popups**: use Hecos native banners for notifications and feedback.
7. **Mandatory signature**: distributed packages must be signed with Ed25519. For local development, "Allow unsigned packages" can be enabled in the Package Manager.

---

## Development Tool: Hecos HPM Builder

```bash
cd C:\Hecos-Packages\Hecos_HPM_Builder
python main.py
```

Available functions:
- **Validate + Build**: validates the manifest and creates the signed `.hpkg`
- **Scaffold New Package**: creates the base structure of a new package (guided)
- **Edit Manifest**: interactive manifest editor
- **Build All**: recompiles all packages in the source folder

> Cryptographic keys: `C:\hpm_private.pem` (private, never commit!) and `C:\Hecos\hecos\data\trusted_keys\hpm_public.pem` (public).

---

## Troubleshooting & Common Gotchas

When developing or extracting built-in modules into standalone HPM packages, beware of these common pitfalls:

1. **Relative Imports and Hot-Reloading Errors**
   If you need to call functions from `main.py` inside `routes.py` (e.g., calling `on_load()` after saving the configuration), **DO NOT** use a simple `import main` while tweaking `sys.path`. If `main.py` uses relative imports (e.g., `from .config_manager import ...`), Python will throw an `ImportError: attempted relative import with no known parent package` because it won't recognize the module as part of a package during the hot-reload.
   **Solution:** Use `importlib` with the absolute package path (e.g., `plugin_main = importlib.import_module("hpm.messenger.main")`).

2. **Arrays of Objects in Manifest (`[[slash_commands]]`)**
   Direct slash commands must be declared in the `hpkg_manifest.toml` as an array of tables (using `[[slash_commands]]`). The installer (Hecos 0.40+) will read these complex fields *directly from the TOML* (extracting `hpkg_manifest.toml` from the package) as a fallback mechanism if the JSON manifest conversion loses structured data. Ensure your array in the TOML file is properly formatted.

3. **Cleaning up Built-in Configuration (`plugins.yaml`)**
   When transforming an old built-in module into an autonomous HPM package, remember that its old configuration might still linger in `C:\Hecos\hecos\config\data\plugins.yaml`. The new package will read from its private TOML (`<id>_config.toml`), but the orphaned legacy entry will clutter the system. Delete the fields in `plugins.yaml`, leaving at most `enabled: true` and `lazy_load: true` (although Hecos natively enables installed packages by default).

4. **Configuration Persistence (Uninstallation)**
   During package removal via HPM, the package folder (e.g., `hpm/messenger`) is not fully deleted if it contains files generated at runtime (such as the TOML configuration file). This is an **intentional** safety feature to prevent users from losing their private settings during every package update or reinstallation.


## HPM 0.40.0 Architecture Upgrades
As of Hecos 0.40.0, the package manager includes several advanced features to ensure system stability and security:
- **Dependency Version Constraints**: `dependencies` and `optional_dependencies` in the manifest can now specify constraints (e.g. `{"image_gen": ">=1.0.0"}`) evaluated using the Python `packaging` library.
- **Pip Lockfiles**: `pip_requirements` now enforce strict versions (e.g., `"requests==2.34.2"`) to prevent version drift between installations.
- **Integrity Verification**: A new `/verify` API calculates the SHA-256 of all installed files and compares them to the Ed25519-signed `manifest_snapshot`.
- **Hecos Max Version**: Packages can specify `hecos_max_version` to prevent silent breakage when Hecos introduces breaking API changes.
