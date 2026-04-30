# 📁 3. Moduli Core

Hecos è suddiviso in pacchetti logici distinti:

- `hecos.core.agent`: Gestisce il ciclo di ragionamento e l'interazione con LiteLLM.
- `hecos.core.config`: Gestisce il caricamento e la validazione dei file YAML (Pydantic v2).
- `hecos.core.memory`: Database SQLite e gestione della persistenza dell'architettura.
- `hecos.core.security`: Motore PKI per HTTPS e Sandbox AST per l'esecuzione sicura del codice.
- `hecos.plugins`: Directory radice per tutte le estensioni e le capacità del sistema.
