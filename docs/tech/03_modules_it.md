# 📁 3. Moduli Core

Zentra Core è suddiviso in pacchetti logici distinti:

- `zentra.core.agent`: Gestisce il ciclo di ragionamento e l'interazione con LiteLLM.
- `zentra.core.config`: Gestisce il caricamento e la validazione dei file YAML (Pydantic v2).
- `zentra.core.memory`: Database SQLite e gestione della persistenza dell'architettura.
- `zentra.core.security`: Motore PKI per HTTPS e Sandbox AST per l'esecuzione sicura del codice.
- `zentra.plugins`: Directory radice per tutte le estensioni e le capacità del sistema.
