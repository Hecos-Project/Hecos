# HPM Package Configuration System
## Pydantic + TOML — Developer Guide

> **Introduced in:** Hecos 0.40.0
> **Applies to:** All packages in `C:\Hecos-Packages\*_src`

---

## The Problem (and Solution)

Before Hecos 0.40, each package managed its own configuration manually: a `defaults.toml` for default values, a user `.toml` file, and custom read/write code in every `config_manager.py`.

This caused:
- Duplicated logic in every package
- No type validation (a string could end up in an `int` field)
- No automatic fallback if the file was corrupted
- Implicit schema with no machine-readable definition

**The solution is `HPMBaseConfigManager`** - a generic class that centralizes all this logic, leaving the package only responsible for declaring its data schema via **Pydantic**.

---

## The Core: `HPMBaseConfigManager`

**File:** `C:\Hecos\hecos\core\package_manager\config.py`

`python
class HPMBaseConfigManager(Generic[T]):
    def __init__(self, schema_cls: Type[T], config_path: Path | str, root_key: str): ...
    def get(self) -> T: ...       # Reads TOML, validates, returns model (or defaults if corrupt)
    def save(self, obj: T) -> bool: ... # Serializes Pydantic -> TOML
    def get_schema_json(self) -> dict: ... # Returns Pydantic JSON Schema
`

**Guaranteed behaviors:**
- If file doesn't exist: creates it with schema defaults
- If TOML is corrupt: returns defaults without crashing
- If fields are missing: uses Pydantic field defaults
- Preserves any extra keys already in the file

---

## How to Write a Config Manager

### Folder structure

`
my_package_src/
my_package_config/
    __init__.py          # Empty - required for Python package
    config_manager.py   # Pydantic schema + HPMBaseConfigManager
`

No more defaults.toml. Defaults live in the Pydantic fields.

### Pydantic Schema

`python
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager: pass   # fallback for isolated testing

class MyPkgConfig(BaseModel):
    enabled: bool = True
    provider: str = "default"
    api_key: str = ""
    timeout: int = 30
    # IMPORTANT: use Field(default_factory=...) for list and dict
    tags: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

_THIS_DIR = Path(__file__).parent.resolve()
_CONFIG_FILE = _THIS_DIR / "my_package.toml"

_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(MyPkgConfig, _CONFIG_FILE, "my_package")
`

### Three mandatory public functions

`python
def get_config() -> dict:
    if _manager:
        return {"my_package": _manager.get().model_dump(mode='json')}
    return {"my_package": MyPkgConfig().model_dump(mode='json')}

def save_config(data: dict) -> bool:
    if _manager and "my_package" in data:
        try:
            obj = MyPkgConfig.model_validate(data["my_package"])
            return _manager.save(obj)
        except Exception:
            return False
    return False

def get_config_obj() -> MyPkgConfig:
    if _manager:
        return _manager.get()
    return MyPkgConfig()
`

---

## Using Config in the Plugin Backend

`python
# plugin/main.py or plugin/generator.py
import sys, os
plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)

from my_package_config.config_manager import get_config_obj

def my_function():
    cfg = get_config_obj()   # MyPkgConfig typed, IDE autocomplete works
    timeout = cfg.timeout    # guaranteed int
    tags = cfg.tags          # list[str], never None
`

**Do not use get_config() in the backend.** Use get_config_obj() which returns the typed model.

---

## Using Config in Flask Routes

`python
# web/routes.py
def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import sys, os
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    from my_package_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/my_package/config", methods=["GET"])
    def get_cfg():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/my_package/config", methods=["POST"])
    def post_cfg():
        data = request.get_json(force=True) or {}
        from my_package_config.config_manager import get_config_obj, _manager, MyPkgConfig
        current = get_config_obj().model_dump(mode='json')
        current.update(data.get("my_package", {}))
        ok = _manager.save(MyPkgConfig.model_validate(current))
        return jsonify({"ok": ok})
`

---

## Nested Sub-models (e.g. messenger)

`python
class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""

class MessengerConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)

_manager = HPMBaseConfigManager(MessengerConfig, _CONFIG_FILE, "messenger")
`

Resulting TOML:
`	oml
[messenger.telegram]
enabled = false
bot_token = ""
`

---

## Partial Save (merge pattern)

When the UI sends only some fields, use the merge pattern:

`python
def save_section(section: dict) -> bool:
    if not _manager: return False
    current = _manager.get().model_dump(mode='json')
    current.update(section)
    obj = MyPkgConfig.model_validate(current)
    return _manager.save(obj)
`

---

## Before vs After

| Aspect | Before (defaults.toml) | After (Pydantic) |
|---|---|---|
| Defaults | Separate .toml file | BaseModel class |
| Type validation | None | Automatic |
| Corrupt file | Crash | Fallback to defaults |
| Missing fields | KeyError | Pydantic default |
| Nested config | Manual | Field(default_factory) |
| Isolated testing | Requires file on disk | Config() in-memory |

---

## Checklist: New Package from Scratch

`
[ ] Create <id>_config/__init__.py (empty)
[ ] Create <id>_config/config_manager.py with:
    [ ] <Name>Config(BaseModel) class with all fields and defaults
    [ ] try/except guard for HPMBaseConfigManager
    [ ] _manager = HPMBaseConfigManager(<Config>, _CONFIG_FILE, "<id>")
    [ ] get_config() -> dict
    [ ] save_config(data) -> bool
    [ ] get_config_obj() -> <Config>
[ ] In manifest: no [config_defaults] for data values
[ ] plugin/main.py: use get_config_obj() to read config
[ ] web/routes.py: use get_config()/save_config() for APIs
[ ] sys.path.insert() in routes.py before relative imports
`

---

## Checklist: Packaging a Built-in Module

`
[ ] Identify the config section in plugins.yaml or system.yaml
[ ] Create <Name>Config(BaseModel) with the same fields
[ ] Remove the section from plugins.yaml (keep only enabled: true if needed)
[ ] Remove any imports from hecos/config/schemas/__init__.py
[ ] The .toml will be created automatically on first package run
[ ] Test the fallback: rename the .toml temporarily and restart
`

---

## Troubleshooting

**HPMBaseConfigManager has no attribute 'get'**
The if hasattr(HPMBaseConfigManager, "get") guard handles isolated environments automatically.

**Validation error on save**
Check that types match (e.g. do not send "30" for int = 30). Log e for detail.

**	omli_w not installed**
Install: pip install tomli-w. Without it, .save() returns False silently.

**Sub-models appear as {} in TOML**
Always use model_dump(mode='json'), not plain model_dump(). The json mode converts all types to TOML-compatible primitives.

**TOML not updated at runtime**
Call _manager.get() at usage time, not at module load time. The manager does not permanently cache the file contents.
