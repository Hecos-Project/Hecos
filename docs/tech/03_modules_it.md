# 📁 3. Moduli Core

Hecos è suddiviso in pacchetti logici distinti:

- `hecos.core.agent`: Gestisce il ciclo di ragionamento e l'interazione con LiteLLM.
- `hecos.core.config`: Gestisce il caricamento e la validazione dei file YAML (Pydantic v2).
- `hecos.core.memory`: Database SQLite e gestione della persistenza dell'architettura.
- `hecos.core.security`: Motore PKI per HTTPS e Sandbox AST per l'esecuzione sicura del codice.
- `hecos.plugins`: Directory radice per tutte le estensioni e le capacità del sistema.
- `hecos.core.package_manager`: Gestore dei pacchetti (HPM), installazione e validazione firme (Ed25519) per moduli e plugin.

---

## Strumento di Sviluppo HPM (Hecos Package Manager)

Il sistema include uno strumento CLI per gli sviluppatori di terze parti per pacchettizzare e firmare i moduli, situato in `scripts/hpm_cli.py`. Questo strumento garantisce che nessun pacchetto possa essere modificato dopo la pubblicazione.

### 1. Generazione delle Chiavi (Ed25519)
Per firmare i pacchetti, hai bisogno di una coppia di chiavi.
```bash
python scripts/hpm_cli.py keygen --out-dir keys
```
- **`private.pem`**: Da mantenere segreta. Serve per firmare.
- **`public.pem`**: Da condividere. Copia questa chiave in `hecos/data/trusted_keys/` affinché Hecos si fidi dei pacchetti firmati da te.

### 2. Creazione del Pacchetto (Pack & Sign)
Prepara la cartella del tuo modulo (es. `mio_modulo/`) assicurandoti che contenga il file `hpkg_manifest.json`.
```bash
python scripts/hpm_cli.py pack --src mio_modulo/ --key keys/private.pem --out mio_modulo_v1.hpkg
```
Lo script calcolerà l'hash (SHA-256) di ogni file all'interno della cartella, firmerà il manifest usando la chiave privata e creerà un archivio `.hpkg` pronto per la distribuzione.

> **Nota**: Durante lo sviluppo locale, puoi bypassare la verifica della firma spuntando la casella "Allow unsigned packages" nella WebUI del Package Manager.
