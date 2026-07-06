# Anatomia di un Pacchetto Hecos (HPM)

Questa guida spiega in dettaglio come e strutturato un pacchetto Hecos (`.hpkg`), cosa fa ogni file, quali percorsi seguire e come creare un pacchetto funzionante da zero.

---

## Cos e un Pacchetto Hecos?

Un pacchetto Hecos e un archivio `.hpkg` (internamente un file ZIP firmato) che puo contenere uno o piu dei seguenti componenti:

| Componente | Descrizione |
|---|---|
| **Plugin Backend** | Logica Python, strumenti LLM, comandi slash |
| **Config Panel** | Pannello di configurazione nel Central Hub (HTML/JS/CSS) |
| **Widget** | Componenti UI per la Sidebar o la Control Room |
| **Rotte API** | Endpoint Flask personalizzati per il pacchetto |

Una volta installato tramite HPM, il pacchetto viene estratto in:
```
C:\Hecos\hecos\hpm\<id_pacchetto>\
```

---

## Struttura Standard della Cartella Sorgente

> Per convenzione, le cartelle sorgente si chiamano `<id_pacchetto>_src` e risiedono in `C:\Hecos-Packages\`.

### Pacchetto Base (solo plugin backend)

```text
mio_pacchetto_src/
|-- hpkg_manifest.toml        # [RICHIESTO] Manifest principale del pacchetto
|-- main.py                   # [RICHIESTO] Entry point -- deve esporre un oggetto tools
|-- README.md                 # [RICHIESTO] Documentazione del pacchetto
|-- preview.png               # [OPZIONALE] Immagine di anteprima per lo Store
|-- CHANGELOG.md              # [OPZIONALE] Storico delle versioni
```

### Pacchetto Completo (plugin + config panel + rotte API)

```text
mio_pacchetto_src/
|-- hpkg_manifest.toml
|-- main.py                               # Entry point root (re-esporta da plugin/)
|-- README.md
|-- preview.png
|
|-- plugin/                               # Logica del backend
|   |-- __init__.py
|   |-- main.py                           # Classe Tools -- strumenti LLM
|   |-- generator.py                      # Moduli logici aggiuntivi
|   |-- providers/                        # Sub-moduli (opzionale)
|       |-- __init__.py
|       |-- mio_provider.py
|
|-- mio_pacchetto_config/                 # Config autonoma del pacchetto
|   |-- __init__.py
|   |-- config_manager.py                 # Lettura/scrittura TOML
|   |-- defaults.toml                     # Valori predefiniti
|
|-- web/                                  # Frontend del Config Panel
    |-- routes.py                         # Rotte Flask personalizzate
    |-- templates/
    |   |-- config_panel.html             # HTML del pannello (fragment)
    |-- static/
        |-- css/
        |   |-- mio_stile.css
        |-- js/
            |-- mio_panel.js
```

> **Nota:** I pacchetti con Widget usano invece una cartella `<nome_widget>/` con struttura propria (vedi sezione Widget).

---

## Il Manifest: hpkg_manifest.toml

Il manifest e il cuore del pacchetto. Il sistema HPM lo legge per sapere tutto sul pacchetto.

### Sezione Identita (obbligatoria)

```toml
id = "mio_pacchetto"           # Identificatore univoco snake_case
name = "Il Mio Pacchetto"      # Nome leggibile per lo Store/Hub
version = "1.0.0"              # Versione semantica (MAJOR.MINOR.PATCH)
hecos_min_version = "0.39.0"   # Versione minima di Hecos richiesta
author = "Il Tuo Nome"
license = "GPL-3.0"
description = "Descrizione breve e chiara del pacchetto."
icon = "emoji"
category = "PLUGINS"           # PLUGINS | MULTIMEDIA | CONNETTIVITA | UTILITY
type = "plugin"                # plugin | widget | extension
```

### Sezione Runtime (plugin backend)

```toml
plugin_tag = "MIO_PACCHETTO"   # Tag univoco MAIUSCOLO
is_class_based = true          # true = classe Tools; false = modulo flat
plugin_dir = "."               # Cartella root del plugin
lazy_load = true               # true = caricato solo quando serve
```

### Dipendenze Python

```toml
pip_requirements = [
    "requests",
    "httpx",
]
python_requires = ">=3.11"
dependencies = []              # Dipendenze da altri pacchetti HPM
```

### Routing LLM

```toml
[routing]
instructions = "[MIO_PACCHETTO: fai_qualcosa:descrizione] - Usa questo tool solo se..."
```

### Slash Commands

```toml
[[slash_commands]]
id = "mio_cmd"
aliases = ["/mio", "/cmd"]
description = "Fa qualcosa di utile"
usage = "/mio <argomento>"
example = "/mio esempio pratico"
icon = "emoji"
method = "fai_qualcosa"        # Nome del metodo nella classe Tools
requires_args = true
```

### Tool Schema (per LLM)

```toml
[[tool_schema]]
name = "MIO_PACCHETTO__fai_qualcosa"
description = "Descrizione del tool per l LLM."

[tool_schema.parameters]
type = "object"
required = ["input"]

[tool_schema.parameters.properties.input]
type = "string"
description = "L input dell utente."
```

### Config Panel

```toml
[config_panel]
tab_id = "mio_tab"
tab_label = "Il Mio Pannello"
category = "UTILITY"
tab_icon = "<i class=\"fas fa-cog\"></i>"
template_file = "web/templates/config_panel.html"
js_file = "web/static/js/mio_panel.js"
css_file = "web/static/css/mio_stile.css"
api_routes_file = "web/routes.py"
config_api_get = "/hecos/api/plugins/mio_pacchetto/config"
config_api_post = "/hecos/api/plugins/mio_pacchetto/config"
```

### Capabilities

```toml
[capabilities]
llm_tools = ["MIO_PACCHETTO__fai_qualcosa"]
slash_commands = ["/mio", "/cmd"]
has_widget = false
has_config_panel = true
has_api_routes = true
has_system_calls = false
notes = "Note aggiuntive per gli utenti."
```

---

## Il Backend: plugin/main.py

```python
"""
MODULE: Il Mio Pacchetto
"""
from hecos.core.logging import logger

class MiopacchettoTools:
    def __init__(self):
        self.tag = "MIO_PACCHETTO"

    def status(self) -> str:
        return "Loaded"

    def fai_qualcosa(self, input: str) -> str:
        logger.info(f"[MIO_PACCHETTO] Chiamato con: {input}")
        return f"Risultato per: {input}"

tools = MiopacchettoTools()
```

### Entry point root (main.py nella root)

```python
"""
Entry point root -- re-esporta dalla cartella plugin/.
Il module_scanner cerca tools in questo file.
"""
from .plugin.main import tools, status
```

---

## La Configurazione Autonoma

I pacchetti non devono mai scrivere nel config di Hecos. Ogni pacchetto ha il suo file TOML privato.

### <id>_config/defaults.toml

```toml
[mio_pacchetto]
provider = "default"
api_key = ""
timeout = 30
```

### <id>_config/config_manager.py

```python
from pathlib import Path
try:
    import tomllib
except ImportError:
    import tomli as tomllib
try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

_THIS_DIR = Path(__file__).parent.resolve()
_DEFAULTS_FILE = _THIS_DIR / "defaults.toml"
_CONFIG_FILE   = _THIS_DIR / "mio_pacchetto.toml"

def get_config() -> dict:
    if not _CONFIG_FILE.exists():
        _create_from_defaults()
    try:
        return tomllib.loads(_CONFIG_FILE.read_bytes().decode("utf-8"))
    except Exception:
        return tomllib.loads(_DEFAULTS_FILE.read_bytes().decode("utf-8"))

def save_config(data: dict) -> bool:
    if not _HAS_TOMLI_W:
        return False
    try:
        _CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode("utf-8"))
        return True
    except Exception:
        return False

def _create_from_defaults():
    save_config(tomllib.loads(_DEFAULTS_FILE.read_bytes().decode("utf-8")))
```

---

## Le Rotte API: web/routes.py

La funzione di init ha una firma obbligatoria:

```python
from flask import request, jsonify

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os, sys

    # Aggiungi la cartella del pacchetto al sys.path per import relativi
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)

    from mio_pacchetto_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/mio_pacchetto/config", methods=["GET"])
    def get_mio_config():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/mio_pacchetto/config", methods=["POST"])
    def post_mio_config():
        data = request.get_json(force=True)
        ok = save_config(data)
        return jsonify({"ok": ok})
```

> Tutti gli endpoint devono seguire `/hecos/api/plugins/<id_pacchetto>/...`

---

## Il Frontend: Config Panel

### web/templates/config_panel.html

Fragment HTML (no `<html>`, `<head>`, `<body>`):

```html
<div id="tab-mio_tab" class="panel module-config-panel">
  <div class="card">
    <!-- Usa data-icon-injected="true" se usi display:flex per evitare icone doppie -->
    <div class="card-title" data-icon-injected="true" style="display:flex; justify-content:space-between; align-items:center;">
        <span><i class="fas fa-cog"></i> Impostazioni</span>
    </div>
    
    <div class="field">
      <label for="mio-provider">Provider</label>
      <select id="mio-provider" class="config-input">
        <option value="default">Default</option>
      </select>
    </div>
    <button onclick="mioPanel.save()" class="btn btn-primary">Salva</button>
  </div>
</div>
```

> **Best Practices UI**:
> - Usa le classi CSS native di Hecos: `.card`, `.card-title`, `.field`, `.config-input`, `.btn btn-primary`.
> - **CRITICO**: Hecos inietta automaticamente un'icona in ogni `.card-title`. Se il tuo div usa `display:flex` (es. per mettere bottoni a destra), aggiungi `data-icon-injected="true"` o l'iniettore distruggerà il layout.

### web/static/js/mio_panel.js

```javascript
const mioPanel = (() => {
  const API_GET  = "/hecos/api/plugins/mio_pacchetto/config";
  const API_POST = "/hecos/api/plugins/mio_pacchetto/config";

  async function init() {
    const res = await fetch(API_GET);
    if (!res.ok) return;
    const cfg = await res.json();
    document.getElementById("mio-provider").value = cfg.mio_pacchetto?.provider || "default";
  }

  async function save() {
    const payload = { mio_pacchetto: { provider: document.getElementById("mio-provider").value } };
    const res = await fetch(API_POST, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    // Usa banner nativi Hecos (window.showToast), MAI window.saveConfig(true)
    if (data.ok) window.showToast("Salvato!", "success");
  }

  // L'HTML viene iniettato dinamicamente, DOMContentLoaded non funziona qui.
  // Usa un MutationObserver o esponi la funzione init per farla chiamare dal Hub.
  const observer = new MutationObserver((mutations) => {
    if (document.getElementById("mio-provider")) {
      init();
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  return { init, save };
})();
```

---

## Compatibilità Legacy (`config_defaults`)

Nei vecchi pacchetti si usava iniettare la configurazione in `system.yaml` tramite `[config_defaults]`. **Questo approccio è deprecato**. L'unico uso consentito oggi è per segnalare al Hub che il plugin è attivo, se strettamente necessario:

```toml
[config_defaults]
enabled = true   # Solo questo. Nient'altro.
```

---

## URL degli Asset Statici

I file JS/CSS vengono serviti dal server Flask tramite:
```
/hpm_plugin/<id_pacchetto>/<percorso_relativo>
```
Esempio: `/hpm_plugin/image_gen/web/static/js/igen_panel.js`

Questi URL vengono generati automaticamente dal Hub a partire dai campi `js_file` e `css_file` nel manifest.

---

## I Widget

La struttura di un widget e diversa dal config panel. Ogni widget ha la sua cartella con un proprio `manifest.json`:

```text
mio_widget/
|-- manifest.json       # Manifest JSON del widget
|-- main.py             # Logica backend
|-- __init__.py
|-- templates/
    |-- mio_widget.html
```

Dichiarazione nel manifest TOML principale:
```toml
[[widgets]]
id = "mio_widget"
label = "Il Mio Widget"
icon = "fa-star"
extension_path = "mio_widget/"
has_room_view = true
```

---

## Ciclo di Vita del Pacchetto

```
1. Sviluppo  ->  Cartella *_src/ con hpkg_manifest.toml
2. Build     ->  HPM Builder crea .hpkg firmato con Ed25519
3. Install   ->  HPM estrae in hecos/hpm/<id>/
4. Boot      ->  LOADER carica il plugin; Flask registra le rotte API
5. Hub       ->  Legge manifest.json e inietta HTML/JS/CSS nel browser
```

---

## Percorsi di Installazione (Runtime)

| Risorsa | Percorso |
|---|---|
| Tutto il pacchetto | `C:\Hecos\hecos\hpm\<id>\` |
| Manifest runtime | `C:\Hecos\hecos\hpm\<id>\manifest.json` |
| Config TOML privata | `C:\Hecos\hecos\hpm\<id>\<id>_config\<id>.toml` |
| Config panel HTML | `C:\Hecos\hecos\hpm\<id>\web\templates\` |
| Static JS/CSS | `C:\Hecos\hecos\hpm\<id>\web\static\` |

---

## Convenzioni e Regole

1. **`id` del pacchetto**: sempre `snake_case` minuscolo. Es: `image_gen`, `my_weather`.
2. **`plugin_tag`**: sempre `SCREAMING_SNAKE_CASE`. Es: `IMAGE_GEN`, `MY_WEATHER`.
3. **Config autonoma**: mai scrivere nel config globale di Hecos. Usare un TOML privato nella cartella `<id>_config/`.
4. **Import in routes.py**: usare sempre `sys.path.insert` per aggiungere la cartella del pacchetto, poiche il file viene caricato dinamicamente fuori dal package context.
5. **Endpoint API**: seguire sempre il pattern `/hecos/api/plugins/<id>/<risorsa>`.
6. **Niente popup del browser**: usare i banner nativi di Hecos per notifiche e feedback.
7. **Firma obbligatoria**: i pacchetti distribuiti devono essere firmati Ed25519. Per sviluppo locale si puo abilitare "Allow unsigned packages" nel Package Manager.

---

## Strumento di Sviluppo: Hecos HPM Builder

```bash
cd C:\Hecos-Packages\Hecos_HPM_Builder
python main.py
```

Funzioni disponibili:
- **Validate + Build**: valida il manifest e crea il `.hpkg` firmato
- **Scaffold New Package**: crea la struttura di un nuovo pacchetto (guidata)
- **Edit Manifest**: editor interattivo del manifest
- **Build All**: ricompila tutti i pacchetti nella cartella sorgente

> Chiavi crittografiche: `C:\hpm_private.pem` (privata) e `C:\Hecos\hecos\data\trusted_keys\hpm_public.pem` (pubblica).
