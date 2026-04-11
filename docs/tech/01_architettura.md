# 🏗️ 1. Architettura di Sistema (v0.15.2)

Zentra Core è costruito su un'architettura **Modulare Object-Oriented** progettata per alte performance, IA locale-first ed estensibilità.

### Principi di Design:
- **Singleton Pattern**: I manager core (Config, State, I18n) sono singleton per garantire coerenza tra i thread.
- **Esecuzione Asincrona**: I task pesanti (STT, LLM inference, TTS) girano in thread di background dedicati.
- **Backend Agnostic**: Il sistema instrada le richieste tramite un client unificato (`client.py`).
- **Multimodale**: Supporto nativo per la visione tramite adapter specifici.
- **Lazy Loading (JIT)**: I plugin possono incapsulare funzionalità complesse in `extensions/` caricate dinamicamente.
- **Centralizzazione Costanti**: Tutti i percorsi sono centralizzati in `zentra/core/constants.py`.
