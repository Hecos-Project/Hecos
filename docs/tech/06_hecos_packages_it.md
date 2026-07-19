# Anatomia di un Pacchetto Hecos (HPM)

Questa guida spiega in dettaglio come e strutturato un pacchetto Hecos (`.hpkg`), cosa fa ogni file, quali percorsi seguire e come creare un pacchetto funzionante da zero.

---

## Che cos'è un Pacchetto Hecos?

Il termine "Pacchetto" si riferisce al formato di distribuzione (`.hpkg`), ma al suo interno può esserci qualsiasi tipo di **Modulo Hecos**. Hecos è progettato per crescere, e grazie all'Hecos Package Manager (HPM), il sistema è infinitamente espandibile. 

Un pacchetto non è necessariamente un plugin; può essere una qualsiasi di queste categorie:

- **Plugin & Core Modules**: Aggiungono capacità logiche all'agente (automazione PC, generazione immagini, connettività). 
- **Autonomous Apps (App Autonome)**: Vere e proprie applicazioni web complete che girano interamente in locale all'interno dell'ecosistema Hecos (es. calendari, liste, gestori mail). A differenza dei plugin, queste hanno una propria UI indipendente e una forte logica separata.
- **Control Room Widgets**: Strumenti UI miniaturizzati per espandere la dashboard di sistema (telemetria in tempo reale, orologi, ecc).
- **Personas & Themes**: Modificano l'aspetto visivo (CSS/grafica) e l'"anima" (comportamento e prompt) dell'agente.

Indipendentemente dal tipo, tutti i moduli condividono lo stesso formato di distribuzione: un archivio ZIP firmato crittograficamente con estensione `.hpkg`. All'interno, possono combinare uno o più componenti: logica backend, interfacce utente (HTML/JS/CSS) e rotte API.

Una volta installato, il pacchetto viene estratto in:
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

> **⚠️ Approccio Aggiornato (Hecos 0.40+)**  
> Il vecchio sistema basato su `defaults.toml` + codice custom è **deprecato**. Tutti i pacchetti usano ora **`HPMBaseConfigManager` (Pydantic + TOML)**.  
> Leggi la guida completa: **[`07_package_config_system_it.md`](file:///C:/Hecos/docs/tech/07_package_config_system_it.md)**

Ogni pacchetto ha il suo file TOML privato (mai scrivere nel config globale di Hecos). I valori di default sono dichiarati direttamente nel modello Pydantic della classe `Config`. La struttura minima è:

```text
mio_pacchetto_config/
├── __init__.py          # Vuoto
└── config_manager.py   # Schema Pydantic + HPMBaseConfigManager
```

Quick start:

```python
# mio_pacchetto_config/config_manager.py
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager: pass

class MioPkgConfig(BaseModel):
    enabled: bool = True
    provider: str = "default"
    api_key: str = ""
    timeout: int = 30

_CONFIG_FILE = Path(__file__).parent / "mio_pacchetto.toml"
_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(MioPkgConfig, _CONFIG_FILE, "mio_pacchetto")

def get_config() -> dict:
    if _manager: return {"mio_pacchetto": _manager.get().model_dump(mode='json')}
    return {"mio_pacchetto": MioPkgConfig().model_dump(mode='json')}

def save_config(data: dict) -> bool:
    if _manager and "mio_pacchetto" in data:
        obj = MioPkgConfig.model_validate(data["mio_pacchetto"])
        return _manager.save(obj)
    return False

def get_config_obj() -> MioPkgConfig:
    return _manager.get() if _manager else MioPkgConfig()
```

Vedi [`07_package_config_system_it.md`](file:///C:/Hecos/docs/tech/07_package_config_system_it.md) per la guida completa con sub-modelli, pattern merge, checklist e troubleshooting.

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

> [!NOTE]
> **Hot Reloading e Percorso di Installazione**  
> A differenza dei normali plugin backend (che vengono installati nella cartella `hpm/` e richiedono il riavvio del core), i widget sono a tutti gli effetti estensioni della Web UI. Per questo motivo, vengono installati direttamente nella cartella `modules/web_ui/extensions/`. Il server Flask di Hecos monitora automaticamente questa directory ricaricando "a caldo" i widget non appena rilevati. Non è necessario alcun riavvio di sistema per installare, aggiornare o modificare i pacchetti di tipo widget.

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

## Pacchetti v2 Isolated — Moduli con Processo Separato

> **Questo capitolo descrive una funzionalità avanzata.** Per la grande maggioranza dei plugin, la struttura v1 descritta sopra è sufficiente e consigliata. Leggi la sezione [Quando usare v2](#quando-usare-v2-isolated) prima di procedere.

### Che cosa cambia in v2?

In un pacchetto **v1 (shared)**, il codice Python del plugin gira **all'interno del processo principale di Hecos**. Condivide lo stesso interprete Python, le stesse librerie e la stessa memoria.

In un pacchetto **v2 (isolated)**, Hecos avvia un **subprocess Python separato** per quel modulo, con un proprio `venv` privato e una comunicazione via **IPC (socket)**. Il Core e il modulo si parlano inviando messaggi JSON, esattamente come un microservizio.

| | **v1 — Shared** | **v2 — Isolated** |
|---|---|---|
| `pip_isolation` nel TOML | `"shared"` | `"isolated"` |
| Processo di sistema | Stesso di Hecos | Subprocess dedicato |
| Ambiente Python | Condiviso con il core | `venv` privato installato con il pacchetto |
| Overhead RAM | ~0 MB extra | ~30–80 MB per subprocess |
| Latenza per chiamata | ~0 ms | ~5–20 ms (IPC) |
| Crash isolation | No | Sì — un crash nel modulo non abbatte il core |
| Aggiornamento a caldo | No | Sì — riavvia solo il subprocess |
| Dipendenze pip | Installate nel core | Completamente autonome nel `venv` locale |

### Struttura della Cartella Sorgente (v2)

```text
mio_modulo_src/
|-- hpkg_manifest.toml            # Come v1, ma con pip_isolation = "isolated"
|-- manifest.json                 # Manifest runtime per Hecos (uguale a v1)
|-- main.py                       # Entrypoint IPC (usa hecos_sdk, non classe diretta)
|-- README.md
|-- preview.png
|-- routing_override.yaml         # [OPZIONALE] Override istruzioni AI per questo modulo
|
|-- plugin/                       # Logica di business
|   |-- __init__.py
|   |-- core_logic.py
|
|-- web/                          # Routes Flask montate da Hecos
|   |-- routes.py                 # init_plugin_routes() — firma identica a v1
|   |-- static/
|   |   |-- js/
|   |   |-- css/
|   |-- templates/
|       |-- config_panel.html
|
|-- mio_modulo_config/            # Config manager autonomo (identico a v1)
|   |-- __init__.py
|   |-- config_manager.py
```

> Dopo l'installazione, l'HPM crea automaticamente la cartella `venv/` all'interno della directory del pacchetto e vi installa le dipendenze dichiarate in `[dependencies_python]`.

### main.py (v2) — Il Runner IPC

In v2 il `main.py` non espone un oggetto `tools`. Invece, usa `hecos_sdk` per gestire un **loop di ricezione messaggi IPC** dal Core. Il Core chiama i metodi tramite il protocollo interno; il subprocess risponde con il risultato.

```python
"""
Entrypoint per il subprocess isolato di MioModulo.
Usa hecos_sdk.runner per gestire le chiamate IPC dal Hecos Core.
"""
from hecos_sdk import runner, logger
from plugin.core_logic import MiaLogica

def handle_call(method: str, params: dict) -> dict:
    """Dispatcher: riceve una chiamata dal Core e ritorna il risultato."""
    logic = MiaLogica()
    if method == "fai_qualcosa":
        return logic.fai_qualcosa(**params)
    raise ValueError(f"Metodo sconosciuto: {method}")

if __name__ == "__main__":
    logger.info("[MioModulo] Subprocess avviato")
    runner.run(handle_call)
```

> **Nota:** `hecos_sdk` è la libreria installata nel `venv` del modulo v2. Fornisce `runner.run()` per il loop IPC e `logger` per il logging unificato con il core.

### hpkg_manifest.toml (v2) — Differenze chiave

Le uniche differenze rispetto al manifest v1 sono:

```toml
# --- CHIAVE V2 ---
pip_isolation = "isolated"    # ← Questo è tutto ciò che distingue v1 da v2

# --- DIPENDENZE (installate nel venv privato del modulo) ---
[dependencies_python]
packages = [
    "torch>=2.0",
    "diffusers>=0.25",
    "transformers>=4.35",
    "Pillow>=10.0",
    "hecos_sdk",              # Obbligatorio in v2
]
```

> Tutte le altre sezioni (`[config_panel]`, `[tool_schema]`, `[[slash_commands]]`, ecc.) sono **identiche alla v1**.

### web/routes.py (v2)

La firma di `init_plugin_routes()` è **identica alla v1**. Hecos la monta sul server Flask principale, indipendentemente dall'isolamento del subprocess.

```python
from flask import request, jsonify

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os, sys
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)

    from mio_modulo_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/mio_modulo/config", methods=["GET"])
    def get_mio_modulo_config():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/mio_modulo/config", methods=["POST"])
    def post_mio_modulo_config():
        data = request.get_json(force=True)
        ok = save_config(data)
        return jsonify({"ok": ok})
```

### routing_override.yaml — Override AI Autonomo

Un pacchetto v2 può includere un file `routing_override.yaml` nella sua directory principale per sovrascrivere le istruzioni AI **specifiche per quel modulo**, senza toccare la configurazione globale di Hecos (`routing_overrides.yaml`).

```yaml
# routing_override.yaml (nella root del pacchetto installato)
enabled: true
instruction: >
  Genera immagini solo se esplicitamente richiesto. Per foto reali, suggerisci
  di usare la webcam. Per richieste creative o anatomicamente complesse, adotta
  uno stile come 'fotografia artistica', 'anatomia classica' o 'illuminazione
  cinematografica' per garantire un output estetico professionale.
```

> **Nota per l'utente:** Questo file è modificabile direttamente dalla casella **"Brain Routing Override"** nel pannello di configurazione del plugin, senza dover aprire file YAML a mano.

### Fast Reinstall (solo v2)

I pacchetti v2 con dipendenze pesanti supportano il **Fast Reinstall**: trascina il `.hpkg` sul Package Manager e attiva il flag **Fast Reinstall**. Hecos reinstallerà i file del pacchetto saltando la fase `pip install`, usando le dipendenze già presenti nel `venv` locale.

> **Importante:** Il Fast Reinstall funziona **solo se reinstalli senza disinstallare prima**. Se disinstalli, Hecos rimuove il `venv` e le dipendenze devono essere reinstallate da zero.

### Quando usare v2 Isolated

```
Il tuo plugin ha dipendenze pip pesanti o potenzialmente
conflittuali con altre librerie del core di Hecos?
(es. torch, tensorflow, diffusers, opencv con CUDA, ecc.)
         │
         ├─ SÌ ──► Usa v2 Isolated
         │          pip_isolation = "isolated"
         │          Il tuo plugin avrà un subprocess e venv dedicati
         │          Ideale per: Image Gen, modelli AI locali, ML
         │
         └─ NO ──► Usa v1 Shared  ← la scelta giusta nella maggior parte dei casi
                    pip_isolation = "shared"
                    Integrazione diretta, zero overhead
                    Ideale per: Calendar, Reminder, Weather, Webcam,
                    Quick Links, Voice Visualizer, Media Player, ecc.
```

**Esempi pratici:**

| Modulo | Formato | Motivo |
|---|---|---|
| `image_gen` | **v2 Isolated** | torch, diffusers, huggingface — dipendenze enormi |
| `calendar` | **v1 Shared** | Nessuna dipendenza pesante |
| `reminder` | **v1 Shared** | Logica scheduler standard |
| `weather_pro` | **v1 Shared** | Solo `requests` |
| `voice_visualizer` | **v1 Shared** | Widget puro, zero dipendenze |
| `media_player` | **v1 Shared** | Dipendenze audio gestibili nel core |
| Plugin LLM locale | **v2 Isolated** | llama-cpp-python — ambiente separato necessario |

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

---

## Troubleshooting & Common Gotchas

Durante lo sviluppo o l'estrazione di moduli built-in in pacchetti HPM, presta attenzione a queste insidie comuni:

1. **Import Relativi ed Errori di Hot-Reloading**
   Se nel file `routes.py` devi chiamare funzioni di `main.py` (es. `on_load()` dopo il salvataggio della config), **NON** fare un semplice `import main` aggiungendo il path a `sys.path`. Se `main.py` usa import relativi (es. `from .config_manager import ...`), Python lancerà `ImportError: attempted relative import with no known parent package` perché non riconoscerà il modulo come parte di un package.
   **Soluzione:** Usa `importlib` con il percorso assoluto del pacchetto in esecuzione (es. `plugin_main = importlib.import_module("hpm.messenger.main")`).

2. **Array di Oggetti nel Manifest (`[[slash_commands]]`)**
   I comandi diretti (Slash Commands) devono essere dichiarati nell'`hpkg_manifest.toml` come array di table (usando `[[slash_commands]]`). L'installer (da Hecos 0.40+) leggerà questi campi complessi *direttamente dal TOML* (estraendo `hpkg_manifest.toml` dal pacchetto) come meccanismo di fallback qualora la conversione JSON del builder perda i dati strutturati. Assicurati che l'array nel TOML sia formattato correttamente.

3. **Pulizia della Configurazione Built-in (`plugins.yaml`)**
   Quando trasformi un ex modulo built-in in un pacchetto HPM autonomo, ricorda che la vecchia configurazione del modulo potrebbe essere rimasta in `C:\Hecos\hecos\config\data\plugins.yaml`. Il nuovo pacchetto leggerà dal suo TOML privato (`<id>_config.toml`), ma la vecchia entry orfana continuerà a ingombrare il sistema. Elimina i campi in `plugins.yaml` lasciando al massimo `enabled: true` e `lazy_load: true` se necessario (anche se di default Hecos carica i pacchetti installati senza bisogno di elencarli).

4. **Persistenza della Configurazione (Disinstallazione)**
   Durante la rimozione di un pacchetto tramite l'HPM, la cartella del pacchetto (es. `hpm/messenger`) non viene eliminata se contiene file generati a runtime (come il file TOML della configurazione). Questo è un comportamento **voluto** (salvavita) per evitare che gli utenti perdano le proprie impostazioni private ad ogni aggiornamento o reinstallazione del pacchetto.



## Novità Architetturali HPM 0.40.0
A partire da Hecos 0.40.0, il gestore pacchetti include funzionalità avanzate per garantire stabilità e sicurezza:
- **Vincoli di Versione Dipendenze**: `dependencies` e `optional_dependencies` nel manifest supportano vincoli (es. `{"image_gen": ">=1.0.0"}`) valutati tramite la libreria Python `packaging`.
- **Pip Lockfiles**: I `pip_requirements` ora forzano versioni fisse (es. `"requests==2.34.2"`) per evitare conflitti o derive di versione (version drift).
- **Verifica Integrità**: Una nuova API `/verify` ricalcola l'hash SHA-256 di tutti i file installati e lo confronta con il `manifest_snapshot` firmato con Ed25519.
- **Hecos Max Version**: I pacchetti possono ora specificare `hecos_max_version` per prevenire crash silenziosi in caso di breaking changes nelle API di Hecos.
