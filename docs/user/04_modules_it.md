# 🔌 4. Sistema Modulare / Moduli

Hecos è costruito su un'architettura **Module-Native**. Ogni capacità (gestione file, hardware, multimedia) è gestita da un modulo indipendente.

- **Flessibilità**: I moduli possono essere abilitati o disabilitati in tempo reale tramite il Pannello Config.
- **Integrità**: Ogni modulo opera nel proprio spazio isolato, garantendo che un errore non blocchi l'intero sistema.
- **Discovery**: Nuovi pacchetti e moduli aggiunti al sistema vengono rilevati automaticamente.

### Gestione tramite WebUI
Nella barra laterale della WebUI, puoi vedere l'elenco dei moduli attivi con i relativi pulsanti macro per inviare comandi rapidi all'IA.

### Moduli e Funzionalità Principali
Hecos include nativamente diversi moduli potenti:
- **Calendario Integrato**: Un modulo calendario completo con tracciamento delle festività e visualizzazione degli eventi direttamente nella WebUI.
- **Promemoria (Reminder)**: Un pianificatore di attività avanzato con interpretazione NLP ("ricordami tra 10 minuti") e notifiche OS attive.
- **Motore Media Player**: Un robusto sistema multimediale (VLC 64-bit + fallback FFplay) che supporta la gestione dello stato, pausa/ripresa e controllo volume.
- **Browser Automation**: Un modulo per interrogare, interagire e navigare le pagine web.
- **OS Automation**: Un modulo per automatizzare i task del sistema operativo tramite il controllo di mouse e tastiera.

### Tipi di Moduli
Hecos supporta un'architettura a 8 livelli in cui tutto è definito come un modulo:
- **Core Modules**: Funzioni di sistema ed OS integrate e non rimovibili.
- **Plugins**: Strumenti e capacità reattive richiamate dall'IA.
- **Apps**: Mini-applicazioni autonome con la propria UI e ciclo di vita.
- **Widgets**: Componenti frontend interattivi per la dashboard (Control Room).
- **Personas**: Personalità IA e profili comportamentali installabili.
- **Themes**: Pacchetti di styling e CSS personalizzati per la UI.
- **Skill Packs**: Pacchetti di comandi slash aggiuntivi per l'interfaccia chat.
- **MCP Servers**: Bridge per tool esterni universali tramite il Model Context Protocol.

### 📦 Hecos Package Manager (HPM)
Dalla versione 0.35.0, Hecos introduce l'**Hecos Package Manager**, un sistema centralizzato che rende la piattaforma potenzialmente universale. 
- **Pacchetti Standalone (`.hpkg`)**: Puoi installare nuovi moduli core, plugin, estensioni, widget e personalità semplicemente trascinando i file `.hpkg` nel Package Manager all'interno della WebUI.
- **Sicurezza Avanzata**: Tutti i pacchetti di terze parti sono verificati tramite firme digitali crittografiche (Ed25519) per garantire l'assoluta integrità del codice.
- **Isolamento**: I moduli mantengono la propria logica e configurazione isolata in modo autonomo, prevenendo conflitti con il Core System.
