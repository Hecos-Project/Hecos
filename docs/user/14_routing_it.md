# 🧭 14. Routing delle Istruzioni IA (3 Livelli)

Hecos utilizza un sistema di routing a tre livelli per decidere come l'IA deve rispondere a ogni comando.

1.  **Defaults di Plugin**: Le istruzioni base fornite dallo sviluppatore del plugin.
2.  **Override Utente**: Le tue personalizzazioni salvate nel file `routing_overrides.yaml`. Queste hanno la precedenza sui default.
3.  **Core Fallback**: Le regole di sistema che garantiscono stabilità e sicurezza.

- **Editor Integrato**: Nella scheda "Routing" della WebUI, puoi modificare queste regole senza toccare il codice, aggiungendo istruzioni specifiche per ogni plugin.
- **Flessibilità Totale**: Puoi cambiare il comportamento di qualsiasi comando dell'IA con un semplice clic.
