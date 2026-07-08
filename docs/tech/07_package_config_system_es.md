# Sistema de Configuracion de Paquetes HPM
## Pydantic + TOML — Guia para Desarrolladores

> **Version introducida:** Hecos 0.40.0
> **Aplica a:** Todos los paquetes en `C:\Hecos-Packages\*_src`

---

## El Problema (y la Solucion)

Antes de Hecos 0.40, cada paquete gestionaba su propia configuracion manualmente: un `defaults.toml` para valores por defecto, un archivo `.toml` de usuario, y codigo custom de lectura/escritura en cada `config_manager.py`.

Esto causaba:
- Logica duplicada en cada paquete
- Sin validacion de tipos (un string podia terminar en un campo `int`)
- Sin fallback automatico si el archivo estaba corrompido
- Esquema implicito sin definicion legible por maquina

**La solucion es `HPMBaseConfigManager`** - una clase generica que centraliza toda esta logica, dejando al paquete solo la declaracion del esquema de datos via **Pydantic**.

---

## El Core: `HPMBaseConfigManager`

**Archivo:** `C:\Hecos\hecos\core\package_manager\config.py`

`python
class HPMBaseConfigManager(Generic[T]):
    def __init__(self, schema_cls: Type[T], config_path: Path | str, root_key: str): ...
    def get(self) -> T: ...       # Lee TOML, valida, retorna modelo (o defaults si esta corrupto)
    def save(self, obj: T) -> bool: ... # Serializa Pydantic -> TOML
    def get_schema_json(self) -> dict: ... # Retorna JSON Schema de Pydantic
`

**Comportamientos garantizados:**
- Si el archivo no existe: lo crea con los defaults del esquema
- Si el TOML esta corrupto: retorna defaults sin crashear
- Si faltan campos: usa los defaults de Pydantic
- Preserva claves extra ya presentes en el archivo

---

## Como Escribir un Config Manager

### Estructura de carpeta

`
mi_paquete_src/
mi_paquete_config/
    __init__.py          # Vacio - necesario para Python package
    config_manager.py   # Esquema Pydantic + HPMBaseConfigManager
`

Ya no existe defaults.toml. Los defaults viven en los campos Pydantic.

### Esquema Pydantic

`python
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager: pass   # fallback para tests aislados

class MiPkgConfig(BaseModel):
    enabled: bool = True
    provider: str = "default"
    api_key: str = ""
    timeout: int = 30
    # IMPORTANTE: usar Field(default_factory=...) para list y dict
    tags: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

_THIS_DIR = Path(__file__).parent.resolve()
_CONFIG_FILE = _THIS_DIR / "mi_paquete.toml"

_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(MiPkgConfig, _CONFIG_FILE, "mi_paquete")
`

### Tres funciones publicas obligatorias

`python
def get_config() -> dict:
    if _manager:
        return {"mi_paquete": _manager.get().model_dump(mode='json')}
    return {"mi_paquete": MiPkgConfig().model_dump(mode='json')}

def save_config(data: dict) -> bool:
    if _manager and "mi_paquete" in data:
        try:
            obj = MiPkgConfig.model_validate(data["mi_paquete"])
            return _manager.save(obj)
        except Exception:
            return False
    return False

def get_config_obj() -> MiPkgConfig:
    if _manager:
        return _manager.get()
    return MiPkgConfig()
`

---

## Uso en el Backend del Plugin

`python
# plugin/main.py o plugin/generator.py
import sys, os
plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)

from mi_paquete_config.config_manager import get_config_obj

def mi_funcion():
    cfg = get_config_obj()   # MiPkgConfig tipado, autocompletado en IDE
    timeout = cfg.timeout    # int garantizado
    tags = cfg.tags          # list[str], nunca None
`

**No usar get_config() en el backend.** Usar get_config_obj() que retorna el modelo tipado.

---

## Uso en Rutas Flask

`python
# web/routes.py
def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import sys, os
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    from mi_paquete_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/mi_paquete/config", methods=["GET"])
    def get_cfg():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/mi_paquete/config", methods=["POST"])
    def post_cfg():
        data = request.get_json(force=True) or {}
        from mi_paquete_config.config_manager import get_config_obj, _manager, MiPkgConfig
        current = get_config_obj().model_dump(mode='json')
        current.update(data.get("mi_paquete", {}))
        ok = _manager.save(MiPkgConfig.model_validate(current))
        return jsonify({"ok": ok})
`

---

## Sub-modelos anidados (ej. messenger)

`python
class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""

class MessengerConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)

_manager = HPMBaseConfigManager(MessengerConfig, _CONFIG_FILE, "messenger")
`

TOML resultante:
`	oml
[messenger.telegram]
enabled = false
bot_token = ""
`

---

## Guardado Parcial (patron merge)

Cuando la UI envia solo algunos campos, usar el patron merge:

`python
def save_section(section: dict) -> bool:
    if not _manager: return False
    current = _manager.get().model_dump(mode='json')
    current.update(section)
    obj = MiPkgConfig.model_validate(current)
    return _manager.save(obj)
`

---

## Antes vs Despues

| Aspecto | Antes (defaults.toml) | Despues (Pydantic) |
|---|---|---|
| Defaults | Archivo .toml separado | Clase BaseModel |
| Validacion tipos | Ninguna | Automatica |
| Archivo corrupto | Crash | Fallback a defaults |
| Campos faltantes | KeyError | Default Pydantic |
| Config anidada | Manual | Field(default_factory) |
| Tests aislados | Requiere archivo en disco | Config() in-memory |

---

## Checklist: Nuevo Paquete desde Cero

`
[ ] Crear <id>_config/__init__.py (vacio)
[ ] Crear <id>_config/config_manager.py con:
    [ ] Clase <Nombre>Config(BaseModel) con todos los campos y defaults
    [ ] Guard try/except para HPMBaseConfigManager
    [ ] _manager = HPMBaseConfigManager(<Config>, _CONFIG_FILE, "<id>")
    [ ] get_config() -> dict
    [ ] save_config(data) -> bool
    [ ] get_config_obj() -> <Config>
[ ] En el manifest: sin [config_defaults] para valores de datos
[ ] plugin/main.py: usar get_config_obj() para leer config
[ ] web/routes.py: usar get_config()/save_config() para APIs
[ ] sys.path.insert() en routes.py antes de imports relativos
`

---

## Checklist: Empaquetar un Modulo Built-in

`
[ ] Identificar la seccion de config en plugins.yaml o system.yaml
[ ] Crear <Nombre>Config(BaseModel) con los mismos campos
[ ] Eliminar la seccion de plugins.yaml (dejar solo enabled: true si es necesario)
[ ] Eliminar imports en hecos/config/schemas/__init__.py
[ ] El .toml se creara automaticamente en el primer arranque
[ ] Probar el fallback: renombrar el .toml temporalmente y reiniciar
`

---

## Troubleshooting

**HPMBaseConfigManager has no attribute 'get'**
El guard if hasattr(HPMBaseConfigManager, "get") maneja entornos aislados automaticamente.

**Validation error on save**
Verificar que los tipos coincidan (ej. no enviar "30" para int = 30). Loguear e para el detalle.

**	omli_w not installed**
Instalar: pip install tomli-w. Sin el, .save() retorna False silenciosamente.

**Sub-modelos aparecen como {} en TOML**
Usar siempre model_dump(mode='json'), no model_dump() simple. El modo json convierte todos los tipos a primitivos compatibles con TOML.

**El TOML no se actualiza en runtime**
Llamar _manager.get() en el momento de uso, no al cargar el modulo. El manager no cachea permanentemente el archivo.
