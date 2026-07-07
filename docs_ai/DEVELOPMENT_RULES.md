# DEVELOPMENT RULES - Hecos

Regole tecniche per lo sviluppo del sistema standalone (Flask-based).

## Standard di Sviluppo

### 1. Registrazione Capabilities
Ogni modulo Python che introduce una nuova interazione deve essere accompagnato da un aggiornamento nei file `capabilities/*.json`.

### 2. Coding & Documentation Language (MANDATORY)
- **English Only:** Tutto il codice sorgente (classi, funzioni, variabili) e TUTTI i commenti nel codice devono essere scritti in inglese.
- **No Translation:** Non tradurre termini tecnici nella lingua della conversazione. Il codebase deve essere internazionalizzato.

### 3. Architettura a Plugin (Flask Blueprints)
Hecos non è più un bridge, ma un ecosistema nativo.
- Le interfacce Web (Chat, Config, Dashboard) devono essere sviluppate come **Flask Blueprints**.
- Ogni plugin deve trovarsi nella cartella `/plugins/` e registrare il proprio `web_bp` (Blueprint) nel sistema.

### 4. Integrità e Sincronizzazione
- Il sistema segue un'architettura dove il nucleo (`main.py`) comunica con i Blueprints.
- Lo stato del sistema (`StateManager`) deve essere sempre sincronizzato tra i diversi moduli web e il core.

### 5. Gestione Errori Web
- Ogni rotta Flask deve includere un blocco `try/except` che restituisca un errore loggato correttamente.
- Non far mai crashare il server principale per un errore in un plugin.

### 6. Configurazione Persistente (YAML + Pydantic)
- Il sistema ha deprecato `config.json` a favore di schemi **Pydantic v2** serializzati in `.yaml` all'interno della cartella `/config/`.
- Le modifiche alla configurazione devono sempre passare per il `ConfigManager`, che si occuperà in automatico della validazione dei tipi e del salvataggio nel giusto file YAML (`system.yaml`, `audio.yaml`, ecc.).
- Nessuna modifica raw va fatta al JSON storico.

### 7. Mobile Responsiveness (MANDATORY)
- Tutte le interfacce WebUI devono essere **Responsive**. Utilizzare media query per garantire il corretto funzionamento su schermi ≤ 768px.
- La navigazione principale su mobile deve passare attraverso il **Menu Hamburger** (off-canvas).

### 8. Internationalized Scripts (I18N)
- Tutti i file di avvio e utility (`.bat`, `.sh`, `.py`) devono mostrare messaggi di log e istruzioni esclusivamente in **Inglese**.
- Questo garantisce la compatibilità cross-platform e l'accessibilità internazionale.

### 9. Secure Contexts (PKI)
- Con l'introduzione di **Hecos PKI**, gran parte del traffico WebUI avviene su HTTPS.
- Utilizzare percorsi assoluti (quando possibile via Flask `url_for`) per gli asset e caricare i file tramite protocolli sicuri per evitare avvisi di "Contenuto Misto" sui browser moderni.

---

> [!WARNING]
> La modifica del `plugin_loader.py` (Kernel) può compromettere l'intero ecosistema. Procedere con test isolati.

### 10. HPM Backup Contract (MANDATORY for packages with persistent data)

Any HPM package that stores user data **must** opt into the Global Backup system by declaring a `[backup]` section in its `hpkg_manifest.toml`.

#### Required fields

```toml
[backup]
enabled            = true
backup_endpoint    = "/api/<package-id>/backup"   # POST → must return { ok: bool, data: any }
restore_endpoint   = "/api/<package-id>/restore"  # POST ← receives { data: any }
icon               = "📦"                         # optional — emoji shown in the UI
```

#### API contract

| Endpoint | Method | Description |
|---|---|---|
| `backup_endpoint` | `POST` | Export all package data. Return `{"ok": true, "data": <serializable>}`. |
| `restore_endpoint` | `POST` | Import data from backup. Receives `{"data": <serializable>}`. Return `{"ok": true}`. |

#### How discovery works

1. `orchestrator.get_backup_fns()` scans every `hpm/<package>/hpkg_manifest.toml` at runtime.
2. Packages with `[backup] enabled = true` and a valid `backup_endpoint` are registered via `_make_hpm_backup_fn()`.
3. `orchestrator.get_backup_metadata()` returns icon + label for each discovered package.
4. `GET /hecos/api/backup/config` exposes `modules_meta` to the frontend.
5. `backup_panel.js → backupLoadConfig()` renders module checkboxes **dynamically** — no hardcoded list needed.

> [!IMPORTANT]
> Never add a new HPM package to the hardcoded arrays in `backup_panel.js` or `api.py`. The discovery system handles it automatically through `hpkg_manifest.toml`.

### 11. HPM Package Extraction (Standalone Modules)

When extracting a legacy built-in module to a standalone HPM package, strictly follow these rules:

1. **Standalone Configuration (`<id>_config.toml`)**:
   HPM packages MUST manage their own configuration via a private `.toml` file. Never write to Hecos core `plugins.yaml`. When extracting a package, ensure you completely remove its legacy configuration block from `config/data/plugins.yaml` to avoid cluttering the system.

2. **Hot-Reloading and Imports**:
   If a package exposes an API route (e.g. `web/routes.py`) that hot-reloads the package logic (`main.py`) after a config change, do **NOT** use relative imports inside `main.py` if you plan to import it directly via `sys.path` hacks. Instead, either use absolute imports across the package, or load `main.py` using `importlib.import_module(f"hpm.{package_id}.main")` to maintain the package context.

3. **Array of Objects in Manifest**:
   Complex manifest properties like `[[slash_commands]]` or `[[tool_schema]]` must be declared as TOML array of tables. The HPM Installer will automatically read them from `hpkg_manifest.toml` inside the package archive.