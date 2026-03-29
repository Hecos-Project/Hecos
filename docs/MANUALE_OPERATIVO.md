# 📖 MANUALE OPERATIVO - Zentra Core

*Documentazione di sistema per l'Amministratore (Admin).*
**Versione:** 0.9.7 (Stabile WebUI & I18N)

---

## 🚀 1. Avvio e Controllo Iniziale

Alla pressione dell'eseguibile (o script avvio Python), Zentra avvia la sua sequenza di **Boot Sincronizzato**.

### Diagnostica Pre-Volo
Il sistema di default controlla:
- Integrità delle cartelle vitali (`core/`, `plugins/`, `memory/`, ecc.).
- Stato Hardware (CPU e RAM entro limiti accettabili).
- Stato del Modulo Ascolto e Voce (Soglia d'energia configurata).
- Verifica di risposta backend IA (ping locale a Ollama/Kobold o controllo Cloud).
- Scansione Plugin Attivi/Disattivati indicando per ciascuno `ONLINE` o `DISATTIVATO`.

Durante questa fase di boot è sempre possibile premere **ESC** per bypassare ogni singolo caricamento forzato.

### ⚡ Avvio Rapido (Fast Boot)
Ove l'Admin desideri un avvio fulmineo, è stata implementata la funzionalità **Avvio Rapido (Salta Diagnostica)**. 
- Disabilitando la diagnostica (attivabile dal Pannello di Controllo **F7** sotto la voce `SYSTEM`), Zentra Core ignorerà ogni controllo testuale hardware a schermo.
- Il tempo di caricamento del terminale utile scende a **~0.5 secondi**, riportando l'interazione al prompt fisso immediatamente.

---

## 🖥 2. Interfaccia Utente Fissa (Safe Scrolling UI)

L'interfaccia a terminale di Zentra è costruita su architettura ancorata (`DECSTBM Scrolling Region`):
- **Dashboard (Prima Riga - Plugin Dashboard):** Se abilitato, un plugin hardware residente in background terrà informato l'utente ogni 2 secondi sullo stato della `CPU, RAM, VRAM e STATO GPU`. (Nessun flickering generato).
- **Barra Blu (Terza Riga - Status System):** Mostra dinamicamente le informazioni centrali:
  - **STATO:**
    - 🟢 `PRONTO` -> Zentra è in ascolto o aspetta ordini testuali.
    - 🟡 `PENSANDO...` -> Elaborazione albero neurale tramite LLM.
    - 🔵 `PARLANDO...` -> Riproduzione vocale tramite motore TTS (Piper).
    - 🔴 `ERRORE/OFFLINE` -> Caduta del provider IA o blocco sistema.
  - **MODELLO:** LLM attualmente in uso.
  - **ANIMA:** Modulo del system prompt/personalità attiva (roleplay o assistente).
  - **MIC / VOCE:** Mostra se `ON` o `OFF`.

**Area Chat:** Lo storico dell'iterazione scritta (o delle traduzioni STT) scorre **solo dalla riga 7 in giù**, lasciando il "Cruscotto" hardware e di sistema intoccati.

---

## ⚙️ 3. Configurazione Dinamica O-T-F (On-The-Fly)

Zentra mette a disposizione i Tasti Funzione (F1-F7) per interagire e riparametrizzare il `config.json` a caldo, con memoria permanente.

* **[ F1 ] MANUALE AZIONALE (Aiuto):** Richiama i protocolli "root" esposti dai Plugin, mostrando comandi liberi (es. `list:`, `cmd:`, `apri:`).
* **[ F2 ] CAMBIO MODELLO IA:** Seleziona velocemente il modello di rete neurale (Llama, Gemma, Cloud, ecc.) dalla lista indicizzata dal backend connesso in quel momento (Ollama/Kobold/Cloud).
* **[ F3 ] CARICO ANIMA / PERSONALITÀ:** Cambia il tono e la coscienza di sistema leggendo nuovi contesti testuali (in `/personalita/*.txt`).
* **[ F4 ] TOGGLE ASCOLTO (MIC):** Silenzia temporalmente le recezioni acustiche (On/Off).
* **[ F5 ] TOGGLE VOCE (TTS):** Abilita o silenzia la sintesi vocale di risposta. L'IA continuerà ad elaborare solo tramite chat visiva.

### 🎛️ Il PANNELLO DI CONTROLLO [ F7 ]
Tramite grafica Inquirer Curses-based, offre il controllo granulare sull'Engine Zentra Core.
Navigabile tramite Frecce Direzionali (`Su`, `Giù`, `Destra`, `Sinistra`), permette editing di booleani (Vero/Falso), numeri o stringhe (via inserimento testo `Invio`).

**Logica di Sicurezza del Salvataggio e Cold Reboot:**
- Se l'utente preme `ESC` senza modifiche o richiede specificamente l'Uscita senza Salvataggio (`DISCARD`), non viene riscritto alcun settaggio a configurazione intaccando zero file originari. Pieno silente ritorno a terminale.
- Se una qualsivoglia modifica visiva accade, la pressione del comando `RIAVVIA ZENTRA` o l'uscita confermata via `Invio`, scriverà fisicamente il `config.json` e scatenerà un **Cold Reboot (Arresto Terminato + Riavvio Forzato, id 42)** automatico in 1 secondo. Questo garantisce che cache ed impostazioni globali si allineino millimetricamente ad ogni istante.

---

## 🔌 4. Sistema Modulare / Plugins

Zentra è espandibile all'infinito posizionando cartelle in `plugins/`.
Tutti i plugin rispondono ad interfacce unificate che esportano `comandi shell` e aggiornano la configurazione dinamica di Zentra (Config Syncing).
- **Plugin WebUI Nativo**: L'interfaccia browser (`plugins/web_ui`) è ora un componente nativo del sistema, gestendo chat, configurazione e dati multimodali in tempo reale.
- **Disabilitazione Pulita**: Se un plugin o modulo è difettoso ma in essenza non bloccante, disattivandolo dal F7 (sezione `Plugins`) sposterà il codice nella memory, bypassandolo all'avvio.

---

## 👁️ 5. Visione e Interazione Multimodale (v0.9.7)

Zentra 0.9.7 introduce il **Sistema di Supporto Visione**, permettendo all'AI di "vedere" e analizzare dati visivi.
- **Caricamento Immagini**: Trascina i file direttamente nella chat web o incolla immagini dalla memoria (**Ctrl+V**).
- **AI Multimodale**: I backend supportati (Gemini 1.5/2.0, OpenAI GPT-4o, Ollama LLaVA) possono descrivere, analizzare e leggere testo dalle immagini.
- **Feedback Visivo**: Le miniature vengono renderizzate sia nella bolla del tuo messaggio (inviato) che nella barra degli allegati (pendente).

---

## 🔄 6. Gestione delle Risposte

- **Rigenera Risposta**: Usa il pulsante con la freccia circolare accanto a ogni messaggio dell'AI per chiedere a Zentra di riprovare. Il sistema rimuoverà la risposta precedente e rieseguirà l'inferenza.
- **Messaging Interno**: La rigenerazione non richiede di riscrivere il prompt; la UI usa un canale API diretto per reinviare il prompt precedente con il suo contesto originale.

---

## 🎨 7. Generazione Immagini (v0.9.7)

Zentra può creare contenuti visivi utilizzando il plugin `IMAGE_GEN`.
- **Come usarlo**: Chiedi semplicemente a Zentra di "Generare un'immagine di..." o "Disegna un...".
- **Server Esterni**: Di default utilizza **Pollinations.ai** per una generazione veloce e senza filtri.
- **Interazione**: L'immagine generata apparirà direttamente in chat con opzioni per il download o lo zoom.

## 💻 WebUI Nativa (v0.9.7)
Zentra 0.9.7 include una potente interfaccia web nativa accessibile a `http://localhost:5000` (di default).
- **Chat in Tempo Reale**: Visualizza lo streaming dell'IA direttamente nel browser.
- **Dashboard Config**: Modifica le impostazioni di sistema tramite una GUI moderna con sincronizzazione istantanea al core.
- **Sincro Audio**: Lo stato audio della WebUI è automaticamente sincronizzato con il terminale (stato F4/F5).

---

## 🛡️ 8. Sicurezza e Risoluzione Problemi

1. **Bug dell'interferenza grafica (Dashboard):** L'engine di Zentra unisce asincronamente i thread UI. Ogni compenetrazione di testi è risolta dal blocco totale `(Thread Join)` ad inizio chiamata del menu F7.
2. **Logs:** I Log di Zentra si conservano nella directory `/logs`. Da Config F7 è possibile nascondere il report log dalla chat per favorire leggibilità di testo.
3. **Loop di Innesco Audio:** Regolare il parametro `Soglia Energia` in **F7 → Ascolto** per calibrare i rumori di fondo ambientali.

---
*Fine del rapporto documentale v0.9.7.*
