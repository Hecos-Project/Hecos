# Sistema di Configurazione dei Pacchetti HPM
## Pydantic + TOML — Guida per Sviluppatori

> **Versione introdotta:** Hecos 0.40.0
> **Si applica a:** Tutti i pacchetti in `C:\Hecos-Packages\*_src`

---

## Il Problema (e la Soluzione)

Prima di Hecos 0.40, ogni pacchetto gestiva la propria configurazione in modo artigianale: un `defaults.toml` con i valori di default, un file `.toml` utente, e codice custom di lettura/scrittura in ogni `config_manager.py`.

Questo causava:
- Logica duplicata in ogni pacchetto
- Nessuna validazione dei tipi (una stringa poteva finire in un campo `int`)
- Nessun fallback automatico se il file era corrotto
- Schema implicito e non leggibile a macchina

**La soluzione e' `HPMBaseConfigManager`** - una classe generica che centralizza tutta questa logica, lasciando al pacchetto solo la dichiarazione dello schema dei dati tramite **Pydantic**.

---

## Il Core: `HPMBaseConfigManager`

**File:** `C:\Hecos\hecos\core\package_manager\config.py`

`python
class HPMBaseConfigManager(Generic[T]):
    def __init__(self, schema_cls: Type[T], config_path: Path | str, root_key: str): ...
    def get(self) -> T: ...       # Legge TOML, valida, ritorna modello (o default se corrotto)
    def save(self, obj: T) -> bool: ... # Serializza Pydantic -> TOML
    def get_schema_json(self) -> dict: ... # JSON Schema Pydantic
`

**Comportamenti garantiti:**
- Se il file non esiste: lo crea con i default dello schema
- Se il TOML e' corrotto: ritorna i default senza crash
- Se mancano campi: usa i default Pydantic
- Preserva chiavi extra gia' presenti nel file

---

## Come Scrivere un Config Manager

### Struttura cartella

`
mio_pacchetto_src/
mio_pacchetto_config/
    __init__.py          # Vuoto - necessario per Python package
    config_manager.py   # Schema Pydantic + HPMBaseConfigManager
`

Non esiste piu' defaults.toml. I default sono nei campi Pydantic.

### Schema Pydantic

`python
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager: pass   # fallback per test isolati

class MioPkgConfig(BaseModel):
    enabled: bool = True
    provider: str = "default"
    api_key: str = ""
    timeout: int = 30
    # IMPORTANTE: usare Field(default_factory=...) per list e dict
    tags: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

_THIS_DIR = Path(__file__).parent.resolve()
_CONFIG_FILE = _THIS_DIR / "mio_pacchetto.toml"

_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(MioPkgConfig, _CONFIG_FILE, "mio_pacchetto")
`

### Tre funzioni pubbliche obbligatorie

`python
def get_config() -> dict:
    if _manager:
        return {"mio_pacchetto": _manager.get().model_dump(mode='json')}
    return {"mio_pacchetto": MioPkgConfig().model_dump(mode='json')}

def save_config(data: dict) -> bool:
    if _manager and "mio_pacchetto" in data:
        try:
            obj = MioPkgConfig.model_validate(data["mio_pacchetto"])
            return _manager.save(obj)
        except Exception:
            return False
    return False

def get_config_obj() -> MioPkgConfig:
    if _manager:
        return _manager.get()
    return MioPkgConfig()
`

---

## Uso nel Backend del Plugin

`python
# plugin/main.py o plugin/generator.py
import sys, os
plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)

from mio_pacchetto_config.config_manager import get_config_obj

def mia_funzione():
    cfg = get_config_obj()   # MioPkgConfig tipizzato, autocompletamento IDE
    timeout = cfg.timeout    # int garantito
    tags = cfg.tags          # list[str] mai None
`

**Non usare get_config() nel backend.** Usa get_config_obj() che restituisce il modello tipizzato.

---

## Uso nelle Rotte Flask

`python
# web/routes.py
def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import sys, os
    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    from mio_pacchetto_config.config_manager import get_config, save_config

    @app.route("/hecos/api/plugins/mio_pacchetto/config", methods=["GET"])
    def get_cfg():
        return jsonify(get_config())

    @app.route("/hecos/api/plugins/mio_pacchetto/config", methods=["POST"])
    def post_cfg():
        data = request.get_json(force=True) or {}
        from mio_pacchetto_config.config_manager import get_config_obj, _manager, MioPkgConfig
        current = get_config_obj().model_dump(mode='json')
        current.update(data.get("mio_pacchetto", {}))
        ok = _manager.save(MioPkgConfig.model_validate(current))
        return jsonify({"ok": ok})
`

---

## Sub-modelli annidati (es. messenger)

`python
class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""

class MessengerConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)

_manager = HPMBaseConfigManager(MessengerConfig, _CONFIG_FILE, "messenger")
`

TOML risultante:
`	oml
[messenger.telegram]
enabled = false
bot_token = ""
`

---

## Salvataggio Parziale (merge)

Quando la UI manda solo alcuni campi, usare il pattern merge:

`python
def save_section(section: dict) -> bool:
    if not _manager: return False
    current = _manager.get().model_dump(mode='json')
    current.update(section)
    obj = MioPkgConfig.model_validate(current)
    return _manager.save(obj)
`

---

## Confronto: Prima vs Dopo

| Aspetto | Prima (defaults.toml) | Dopo (Pydantic) |
|---|---|---|
| Default | File .toml separato | Classe BaseModel |
| Validazione tipi | Nessuna | Automatica |
| File corrotto | Crash | Fallback ai default |
| Campi mancanti | KeyError | Default Pydantic |
| Nested config | Manuale | Field(default_factory) |
| Test isolati | File su disco | Config() in-memory |

---

## Checklist: Nuovo Pacchetto

`
[ ] Crea <id>_config/__init__.py (vuoto)
[ ] Crea <id>_config/config_manager.py con:
    [ ] Classe <Nome>Config(BaseModel) con tutti i campi e default
    [ ] Guard try/except per HPMBaseConfigManager
    [ ] _manager = HPMBaseConfigManager(<Config>, _CONFIG_FILE, "<id>")
    [ ] get_config() -> dict
    [ ] save_config(data) -> bool
    [ ] get_config_obj() -> <Config>
[ ] Nel manifest: nessun [config_defaults] per i valori dati
[ ] plugin/main.py: usa get_config_obj() per leggere
[ ] web/routes.py: usa get_config()/save_config() per le API
[ ] sys.path.insert() in routes.py prima degli import relativi
`

---

## Checklist: Pacchettizzare un Modulo Built-in

`
[ ] Identifica la sezione di config in plugins.yaml o system.yaml
[ ] Crea <Nome>Config(BaseModel) con gli stessi campi
[ ] Rimuovi la sezione da plugins.yaml (lascia solo enabled: true)
[ ] Rimuovi eventuali import in hecos/config/schemas/__init__.py
[ ] Il .toml verra' creato automaticamente al primo avvio
[ ] Testa il fallback: rinomina temporaneamente il .toml e riavvia
`

---

## Troubleshooting

**HPMBaseConfigManager has no attribute 'get'**
Il guard if hasattr(HPMBaseConfigManager, "get") gestisce l'env isolato automaticamente.

**Validation error on save**
Controlla che i tipi corrispondano (es. non mandare "30" per int = 30). Logga e per il dettaglio.

**	omli_w not installed**
Installa: pip install tomli-w. Senza di esso .save() ritorna False silenziosamente.

**Sub-modelli come {} nel TOML**
Usa sempre model_dump(mode='json'), non model_dump(). La modalita' json converte tutti i tipi in primitivi TOML-compatibili.

**Il TOML non viene aggiornato a runtime**
Chiama _manager.get() al momento dell'uso, non al caricamento del modulo. Il manager non fa caching permanente del file.
