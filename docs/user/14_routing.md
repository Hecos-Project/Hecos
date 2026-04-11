## 🧭 14. Sistema di Istruzioni AI a Livelli (v0.16.0)

Zentra v0.16.0 introduce un'architettura **Configurazione Ibrida a 3 Livelli** per controllare come l'IA gestisce i comandi plugin-specifici.

### Riepilogo dei Livelli

| Livello | Dove | Scope | Per cosa si usa |
|---|---|---|---|
| **1. Istruzioni Speciali IA** | Config → scheda Persona | Globale | Comportamento generale, tono, stile |
| **2. Routing Overrides (YAML)** | Config → scheda Routing | Per-plugin | Forzare azioni o vincoli specifici per uno strumento |
| **3. Manifest Plugin** | `zentra/core/registry.json` | Default | Comportamenti di fabbrica (impostati dagli sviluppatori) |

> **Nota**: Il Livello 2 (YAML overrides) ha la **priorità massima** per il plugin specifico, sovrascrivendo sia le istruzioni globali che il Manifest.

### Come usare l'Editor Routing (Browser)
1. Apri il Config Panel a `https://localhost:7070/zentra/config/ui`.
2. Clicca sulla scheda **Routing**.
3. In basso vedrai la sezione **Custom Plugin Overrides**.
4. Clicca **+ Add Override** per aggiungere una nuova regola.
