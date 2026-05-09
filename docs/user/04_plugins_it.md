# 🔌 4. Sistema Modular / Plugins

Hecos è costruito su un'architettura **Plugin-Native**. Ogni capacità (gestione file, hardware, multimedia) è gestita da un modulo indipendente.

- **Flessibilità**: I plugin possono essere abilitati o disabilitati in tempo reale tramite il Pannello Config.
- **Integrità**: Ogni plugin opera nel proprio spazio isolato, garantendo che un errore in un modulo non blocchi l'intero sistema.
- **Discovery**: Nuovi plugin aggiunti alla cartella `plugins/` vengono rilevati automaticamente all'avvio.

### Gestione tramite WebUI
Nella barra laterale della WebUI, puoi vedere l'elenco dei plugin attivi con i relativi pulsanti macro per inviare comandi rapidi all'IA.

### Plugin e Funzionalità Principali
Hecos include nativamente diversi plugin potenti:
- **Calendario Integrato**: Un modulo calendario completo con tracciamento delle festività e visualizzazione degli eventi direttamente nella WebUI.
- **Promemoria (Reminder)**: Un pianificatore di attività avanzato con interpretazione NLP ("ricordami tra 10 minuti") e notifiche OS attive.
- **Motore Media Player**: Un robusto sistema multimediale (VLC 64-bit + fallback FFplay) che supporta la gestione dello stato, pausa/ripresa e controllo volume.
