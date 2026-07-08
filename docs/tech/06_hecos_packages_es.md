# Anatomía de un Paquete Hecos (HPM)

Esta guía explica en detalle cómo está estructurado un paquete Hecos (`.hpkg`), qué hace cada archivo, qué rutas seguir y cómo crear un paquete funcional desde cero — incluso si eres principiante.

---

## ¿Qué es un Paquete Hecos?

El término "Paquete" se refiere al formato de distribución (`.hpkg`), pero en su interior puede haber cualquier tipo de **Módulo Hecos**. Hecos está diseñado para crecer contigo. Gracias al Hecos Package Manager (HPM), el sistema es infinitamente expansible.

Un paquete no es necesariamente solo un plugin; puede ser de cualquiera de estas categorías:

- **Plugins y Módulos Core**: Añaden integraciones nativas como automatización de PC/Navegador, clientes de correo, puentes de mensajería y generación de imágenes.
- **Apps Autónomas**: Instalan aplicaciones web completas que se ejecutan de forma local dentro del ecosistema Hecos (ej. calendarios, listas, gestores de correo). A diferencia de los plugins, estas tienen su propia interfaz de usuario independiente y una lógica separada.
- **Control Room Widgets**: Expanden el panel de control del sistema con nuevas herramientas de monitorización en tiempo real y telemetría.
- **Personas y Temas**: Personalizan el aspecto, la interfaz y el "alma" (comportamiento y prompts) de tu agente.

Independientemente del tipo, todos los módulos comparten el mismo formato de distribución: un archivo ZIP firmado criptográficamente con la extensión `.hpkg`. En su interior, pueden combinar uno o más componentes: lógica de backend, interfaces de usuario (HTML/JS/CSS) y rutas API.

Una vez instalado a través de HPM, el paquete se extrae en:
```
C:\Hecos\hecos\hpm\<id_paquete>\
```

---

## Estructura Estándar de la Carpeta Fuente

> Por convención, las carpetas fuente se llaman `<id_paquete>_src` y residen en `C:\Hecos-Packages\`.

### Paquete Básico (solo plugin backend)

```text
mi_paquete_src/
|-- hpkg_manifest.toml        # [REQUERIDO] Manifiesto principal del paquete
|-- main.py                   # [REQUERIDO] Punto de entrada -- debe exponer un objeto tools
|-- README.md                 # [REQUERIDO] Documentación del paquete
|-- preview.png               # [OPCIONAL] Imagen de vista previa para la Store
|-- CHANGELOG.md              # [OPCIONAL] Historial de versiones
```

### Paquete Completo (plugin + config panel + rutas API)

```text
mi_paquete_src/
|-- hpkg_manifest.toml
|-- main.py                               # Punto de entrada root (re-exporta de plugin/)
|-- README.md
|-- preview.png
|
|-- plugin/                               # Lógica del backend
|   |-- __init__.py
|   |-- main.py                           # Clase Tools -- herramientas LLM
|   |-- generator.py                      # Módulos lógicos adicionales
|   |-- providers/                        # Submódulos (opcional)
|       |-- __init__.py
|       |-- mi_proveedor.py
|
|-- mi_paquete_config/                    # Configuración autónoma del paquete
|   |-- __init__.py
|   |-- config_manager.py                 # Lectura/escritura TOML
|   |-- defaults.toml                     # Valores predeterminados
|
|-- web/                                  # Frontend del Config Panel
    |-- routes.py                         # Rutas Flask personalizadas
    |-- templates/
    |   |-- config_panel.html             # HTML del panel (fragmento)
    |-- static/
        |-- css/
        |   |-- mi_estilo.css
        |-- js/
            |-- mi_panel.js
```

---

## El Manifiesto: hpkg_manifest.toml

El manifiesto es el corazón del paquete. HPM lo lee para saber todo sobre el paquete.

### Sección de Identidad (obligatoria)

```toml
id = "mi_paquete"              # Identificador único snake_case
name = "Mi Paquete"            # Nombre legible para la Store/Hub
version = "1.0.0"              # Versión semántica (MAJOR.MINOR.PATCH)
hecos_min_version = "0.39.0"   # Versión mínima requerida de Hecos
author = "Tu Nombre"
license = "GPL-3.0"
description = "Descripción breve y clara del paquete."
icon = "emoji"
category = "PLUGINS"           # PLUGINS | MULTIMEDIA | CONNETTIVITA | UTILITY
type = "plugin"                # plugin | widget | extension
```

### Sección Runtime (plugin backend)

```toml
plugin_tag = "MI_PAQUETE"      # Etiqueta única en MAYÚSCULAS
is_class_based = true          # true = clase Tools; false = módulo plano
plugin_dir = "."               # Carpeta raíz del plugin
lazy_load = true               # true = se carga solo cuando es necesario
```

### Dependencias de Python

```toml
pip_requirements = [
    "requests",
    "httpx",
]
python_requires = ">=3.11"
dependencies = []              # Dependencias de otros paquetes HPM
```

### Enrutamiento LLM

```toml
[routing]
instructions = "[MI_PAQUETE: hacer_algo:descripcion] - Usa esta herramienta solo si..."
```

### Comandos Slash

```toml
[[slash_commands]]
id = "mi_cmd"
aliases = ["/mi", "/cmd"]
description = "Hace algo útil"
usage = "/mi <argumento>"
example = "/mi ejemplo práctico"
icon = "emoji"
method = "hacer_algo"          # Nombre del método en la clase Tools
requires_args = true
```

### Tool Schema (para LLM)

```toml
[[tool_schema]]
name = "MI_PAQUETE__hacer_algo"
description = "Descripción de la herramienta para el LLM."

[tool_schema.parameters]
type = "object"
required = ["input"]

[tool_schema.parameters.properties.input]
type = "string"
description = "La entrada del usuario."
```

### Config Panel

```toml
[config_panel]
tab_id = "mi_tab"
tab_label = "Mi Panel"
category = "UTILITY"
tab_icon = "<i class=\"fas fa-cog\"></i>"
template_file = "web/templates/config_panel.html"
js_file = "web/static/js/mi_panel.js"
css_file = "web/static/css/mi_estilo.css"
api_routes_file = "web/routes.py"
config_api_get = "/hecos/api/plugins/mi_paquete/config"
config_api_post = "/hecos/api/plugins/mi_paquete/config"
```

### Capacidades (Capabilities)

```toml
[capabilities]
llm_tools = ["MI_PAQUETE__hacer_algo"]
slash_commands = ["/mi", "/cmd"]
has_widget = false
has_config_panel = true
has_api_routes = true
has_system_calls = false
notes = "Notas adicionales para los usuarios."
```

---

## El Backend: plugin/main.py

```python
"""
MODULE: Mi Paquete
"""
from hecos.core.logging import logger

class MipaqueteTools:
    def __init__(self):
        self.tag = "MI_PAQUETE"

    def status(self) -> str:
        return "Loaded"

    def hacer_algo(self, input: str) -> str:
        logger.info(f"[MI_PAQUETE] Llamado con: {input}")
        return f"Resultado para: {input}"

tools = MipaqueteTools()
```

### Root entry point (main.py en la raíz)

```python
"""
Punto de entrada root -- reexporta desde la carpeta plugin/.
El module_scanner busca el objeto tools en este archivo.
"""
from .plugin.main import tools, status
```

---

## Configuración Autónoma

> **⚠️ Enfoque Actualizado (Hecos 0.40+)**  
> El antiguo sistema basado en `defaults.toml` + código custom está **deprecado**. Todos los paquetes usan ahora **`HPMBaseConfigManager` (Pydantic + TOML)**.  
> Lee la guía completa: **[`07_package_config_system_es.md`](file:///C:/Hecos/docs/tech/07_package_config_system_es.md)**

Cada paquete tiene su propio archivo TOML privado (nunca escribir en el config global de Hecos). Los valores por defecto se declaran directamente en los campos del modelo Pydantic. Estructura mínima:

```text
mi_paquete_config/
├── __init__.py          # Vacío
└── config_manager.py   # Esquema Pydantic + HPMBaseConfigManager
```

Quick start:

```python
# mi_paquete_config/config_manager.py
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager: pass

class MiPkgConfig(BaseModel):
    enabled: bool = True
    provider: str = "default"
    api_key: str = ""
    timeout: int = 30

_CONFIG_FILE = Path(__file__).parent / "mi_paquete.toml"
_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(MiPkgConfig, _CONFIG_FILE, "mi_paquete")

def get_config() -> dict:
    if _manager: return {"mi_paquete": _manager.get().model_dump(mode='json')}
    return {"mi_paquete": MiPkgConfig().model_dump(mode='json')}

def save_config(data: dict) -> bool:
    if _manager and "mi_paquete" in data:
        obj = MiPkgConfig.model_validate(data["mi_paquete"])
        return _manager.save(obj)
    return False

def get_config_obj() -> MiPkgConfig:
    return _manager.get() if _manager else MiPkgConfig()
```

Ver [`07_package_config_system_es.md`](file:///C:/Hecos/docs/tech/07_package_config_system_es.md) para la guía completa con sub-modelos anidados, patrón merge, checklists y troubleshooting.

---


## Rutas API: web/routes.py

```python
from flask import request, jsonify

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os, sys

    # Agregar la carpeta del paquete al sys.path
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)

    from mi_paquete_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/mi_paquete/config", methods=["GET"])
    def get_mi_config():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/mi_paquete/config", methods=["POST"])
    def post_mi_config():
        data = request.get_json(force=True)
        ok = save_config(data)
        return jsonify({"ok": ok})
```

> Todos los endpoints deben seguir `/hecos/api/plugins/<id_paquete>/...`

---

## Frontend: Config Panel

### web/templates/config_panel.html

Fragmento HTML (sin `<html>`, `<head>`, `<body>`):

```html
<div id="tab-mi_tab" class="panel module-config-panel">
  <div class="card">
    <!-- Usa data-icon-injected="true" si usas display:flex para evitar iconos dobles -->
    <div class="card-title" data-icon-injected="true" style="display:flex; justify-content:space-between; align-items:center;">
        <span><i class="fas fa-cog"></i> Ajustes</span>
    </div>
    
    <div class="field">
      <label for="mi-provider">Proveedor</label>
      <select id="mi-provider" class="config-input">
        <option value="default">Default</option>
      </select>
    </div>
    <button onclick="miPanel.save()" class="btn btn-primary">Guardar</button>
  </div>
</div>
```

> **Mejores Prácticas de UI**:
> - Usa las clases CSS nativas de Hecos: `.card`, `.card-title`, `.field`, `.config-input`, `.btn btn-primary`.
> - **CRÍTICO**: Hecos inyecta automáticamente un icono en cada `.card-title`. Si tu div usa `display:flex` (ej. para poner botones a la derecha), añade `data-icon-injected="true"` o el inyector destruirá tu diseño.

### web/static/js/mi_panel.js

```javascript
const miPanel = (() => {
  const API_GET  = "/hecos/api/plugins/mi_paquete/config";
  const API_POST = "/hecos/api/plugins/mi_paquete/config";

  async function init() {
    const res = await fetch(API_GET);
    if (!res.ok) return;
    const cfg = await res.json();
    document.getElementById("mi-provider").value = cfg.mi_paquete?.provider || "default";
  }

  async function save() {
    const payload = { mi_paquete: { provider: document.getElementById("mi-provider").value } };
    const res = await fetch(API_POST, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    // Usa banners nativos de Hecos (window.showToast), NUNCA window.saveConfig(true)
    if (data.ok) window.showToast("Guardado!", "success");
  }

  // El HTML se inyecta dinámicamente, DOMContentLoaded no funcionará aquí.
  // Usa un MutationObserver o expón la función init para que el Hub la llame.
  const observer = new MutationObserver((mutations) => {
    if (document.getElementById("mi-provider")) {
      init();
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  return { init, save };
})();
```

---

## Compatibilidad Legacy (`config_defaults`)

En los paquetes más antiguos, la configuración se inyectaba en `system.yaml` mediante `[config_defaults]`. **Este enfoque está obsoleto**. El único uso permitido hoy en día es para indicarle al Hub que el plugin está activo, si es estrictamente necesario:

```toml
[config_defaults]
enabled = true   # Solo esto. Nada más.
```

---

## URLs de Archivos Estáticos

Los archivos JS/CSS son servidos por Flask a través de:
```
/hpm_plugin/<id_paquete>/<ruta_relativa>
```
Ejemplo: `/hpm_plugin/image_gen/web/static/js/igen_panel.js`

Estas URLs se generan automáticamente por el Hub a partir de los campos `js_file` y `css_file` en el manifiesto.

---

## Widgets

La estructura del widget es diferente a la del config panel. Cada widget tiene su propia carpeta con un `manifest.json`:

```text
mi_widget/
|-- manifest.json       # Manifiesto JSON del widget
|-- main.py             # Lógica backend
|-- __init__.py
|-- templates/
    |-- mi_widget.html
```

Declaración en el manifiesto principal TOML:
```toml
[[widgets]]
id = "mi_widget"
label = "Mi Widget"
icon = "fa-star"
extension_path = "mi_widget/"
has_room_view = true
```

---

## Rutas de Instalación (Runtime)

| Recurso | Ruta |
|---|---|
| Paquete completo | `C:\Hecos\hecos\hpm\<id>\` |
| Manifiesto runtime | `C:\Hecos\hecos\hpm\<id>\manifest.json` |
| Config TOML privada | `C:\Hecos\hecos\hpm\<id>\<id>_config\<id>.toml` |
| HTML de Config Panel | `C:\Hecos\hecos\hpm\<id>\web\templates\` |
| Static JS/CSS | `C:\Hecos\hecos\hpm\<id>\web\static\` |

---

## Convenciones y Reglas

1. **`id` del paquete**: siempre en minúsculas y `snake_case`. Ej: `image_gen`, `mi_clima`.
2. **`plugin_tag`**: siempre en MAYÚSCULAS `SCREAMING_SNAKE_CASE`. Ej: `IMAGE_GEN`.
3. **Configuración Autónoma**: nunca escribir en la configuración global de Hecos. Usa un TOML privado.
4. **Imports en routes.py**: usar siempre `sys.path.insert` para agregar la carpeta del paquete, ya que se carga dinámicamente.
5. **Endpoints API**: seguir siempre el patrón `/hecos/api/plugins/<id>/<recurso>`.
6. **Sin popups del navegador**: usar notificaciones nativas de Hecos.
7. **Firma Obligatoria**: los paquetes distribuidos deben firmarse con Ed25519.

---

## Herramienta de Desarrollo: Hecos HPM Builder

```bash
cd C:\Hecos-Packages\Hecos_HPM_Builder
python main.py
```

Funciones disponibles:
- **Validate + Build**: valida el manifiesto y crea el `.hpkg` firmado.
- **Scaffold New Package**: crea la estructura de un nuevo paquete.
- **Edit Manifest**: editor interactivo de manifiestos.
- **Build All**: recompila todos los paquetes de la carpeta fuente.

> Claves criptográficas: `C:\hpm_private.pem` (privada, ¡nunca confirmarla!) y `C:\Hecos\hecos\data\trusted_keys\hpm_public.pem` (pública).

---

## Troubleshooting & Common Gotchas (Solución de problemas)

Al desarrollar o extraer módulos integrados en paquetes HPM independientes, ten cuidado con estos problemas comunes:

1. **Importaciones Relativas y Errores de Hot-Reloading**
   Si necesitas llamar a funciones de `main.py` dentro de `routes.py` (ej. llamar a `on_load()` después de guardar la configuración), **NO** uses un simple `import main` mientras modificas `sys.path`. Si `main.py` utiliza importaciones relativas (ej. `from .config_manager import ...`), Python lanzará un `ImportError: attempted relative import with no known parent package` porque no reconocerá el módulo como parte de un paquete durante la recarga en caliente.
   **Solución:** Usa `importlib` con la ruta absoluta del paquete (ej. `plugin_main = importlib.import_module("hpm.messenger.main")`).

2. **Arrays de Objetos en el Manifiesto (`[[slash_commands]]`)**
   Los comandos directos deben declararse en el `hpkg_manifest.toml` como un array de tablas (usando `[[slash_commands]]`). El instalador (Hecos 0.40+) leerá estos campos complejos *directamente del TOML* (extrayendo `hpkg_manifest.toml` del paquete) como un mecanismo de respaldo si la conversión del manifiesto JSON pierde los datos estructurados. Asegúrate de que el array en el archivo TOML tenga el formato correcto.

3. **Limpieza de la Configuración Integrada (`plugins.yaml`)**
   Al transformar un antiguo módulo integrado en un paquete autónomo, recuerda que su antigua configuración aún podría permanecer en `C:\Hecos\hecos\config\data\plugins.yaml`. El nuevo paquete leerá de su TOML privado (`<id>_config.toml`), pero la entrada heredada huérfana saturará el sistema. Elimina los campos en `plugins.yaml`, dejando como máximo `enabled: true` y `lazy_load: true` (aunque Hecos habilita de forma nativa los paquetes instalados de manera predeterminada).

4. **Persistencia de la Configuración (Desinstalación)**
   Durante la eliminación de un paquete a través de HPM, la carpeta del paquete (ej. `hpm/messenger`) no se elimina por completo si contiene archivos generados en tiempo de ejecución (como el archivo de configuración TOML). Esta es una característica de seguridad **intencional** para evitar que los usuarios pierdan sus ajustes privados durante cada actualización o reinstalación del paquete.
