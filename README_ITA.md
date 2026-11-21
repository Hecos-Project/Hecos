# 🌌 Progetto Hecos
<p align="center">
  <img src="hecos/assets/Hecos_Logo_Banner.png" width="400" alt="Logo Hecos">
</p>

# Hecos - Versione 0.55.2 (Fase II: Ghost Fire)
Lingua: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Hecos
**Helping Companion System (Privato, Rapido, Semplice)**

<p align="center">
  <a href="https://github.com/Hecos-Project/Hecos/releases/latest/download/INSTALL_HECOS_WINDOWS.zip">
    <img src="https://img.shields.io/badge/Scarica_Installer-Windows_(ZIP)-00e5ff?style=for-the-badge&logo=windows&logoColor=080a12" alt="Scarica Installer Hecos per Windows">
  </a>
  &nbsp;
  <a href="https://github.com/Hecos-Project/Hecos/releases/latest/download/INSTALL_HECOS_LINUX.zip">
    <img src="https://img.shields.io/badge/Scarica_Installer-Linux_%2F_macOS_(ZIP)-5b7dff?style=for-the-badge&logo=linux&logoColor=white" alt="Scarica Installer Hecos per Linux e macOS">
  </a>
  &nbsp;
  <a href="https://github.com/Hecos-Project/Hecos/wiki/00_introduction_it">
    <img src="https://img.shields.io/badge/Documentazione-Wiki_(IT)-181c2e?style=for-the-badge&logo=bookstack&logoColor=white" alt="Hecos Wiki">
  </a>
</p>

---

> ### ⚡ Motto Fondamentale
> **"Zero moral filters. Zero social bias. Zero political agendas. From the core engine to every single module, Hecos is built on one unshakeable rule: freedom of thought belongs to everyone."**
> 
> *(Zero filtri morali. Zero pregiudizi sociali. Zero agende politiche. Dal motore centrale a ogni singolo modulo, Hecos è costruito su un'unica incrollabile regola: la libertà di pensiero appartiene a tutti.)*

---

> **Stato: Fase II (Ghost Fire)**: Hecos è attualmente in `v0.55.2`. Questo è un Helping Companion System che funge da ponte tra il ragionamento ad alto livello e l'esecuzione di sistema root.
>
> ⚠️ **Avviso Importante**: A partire da questa major release (0.50.0+), lo sviluppo primario e l'ambiente target migrano ufficialmente a **Windows 11**.

## 🚀 Panoramica
**Hecos** è un **Helping Companion System**: un ecosistema locale progettato per unire fluidamente tecnologia e vita umana, combinando AI reasoning, automazione visiva ed esecuzione di sistema diretta. Invece di inseguire concetti astratti come la sovranità digitale, Hecos si concentra su un'unica missione pragmatica: **migliorare la vita umana**, trasformando l'hardware locale in uno strumento pratico ed estremamente efficiente per tutti i giorni.

Costruito sui nostri pilastri fondamentali:
* 🕊️ **Libertà di Pensiero** — Zero filtri morali, zero bias sociali, zero agende politiche.
* 🛡️ **Privacy al Primo Posto** — Funzionamento 100% locale, zero dipendenze cloud e architettura privacy a 3 livelli.
* ⚡ **Velocità Estrema** — Architettura nativa ottimizzata e sistema di plugin ad alte prestazioni per una reattività istantanea.
* 🧊 **Semplicità Assoluta** — Dashboard professionale e design modulare che rende intuitiva l'orchestrazione IA avanzata.

Ora completamente migrato a una **architettura stabile Fase II: Ghost Fire**, Hecos 0.55.2 offre una interfaccia Web dedicata (Chat + Config), un **Installer Grafico Unificato a 5 step** (Core + Tray, senza prerequisiti Python) e internazionalizzazione completa. Grazie a **LiteLLM**, supporta Ollama, Llama.cpp, KoboldCpp e i principali provider cloud con streaming in tempo reale e TTS locale (Kokoro, Piper, Fish Speech ed XTTS).

---

## ✨ Caratteristiche Principali (v0.55.2)
* 🚀 **Installer Grafico Unificato & Setup Resiliente** — Procedura guidata desktop a 5 step (`INSTALL_HECOS_WINDOWS.bat` / `INSTALL_HECOS_LINUX.sh`) che configura automaticamente un Python 3.11 portatile isolato (verificato con SHA256 e completo di `tkinter`), installa versioni testate da `constraints.txt`, supporta cartelle personalizzate tramite `install.toml` e include **Diagnostica (`Doctor`)** e **Quick Repair**.
* 🎙️ **Voice Forge Studio** — Studio avanzato per la creazione e modellazione vocale con analisi acustica in tempo reale (formanti, grafico radar del profilo vocale, spettrogramma) e miscelazione di preset.
* 🐟 **Fish Speech SOTA Zero-Shot TTS** — Motore neurale di sintesi vocale di ultima generazione con clonazione zero-shot immediata in esecuzione locale tramite daemon e server dedicato.
* 🧬 **Clonazione Vocale Kokoro & Voice Manager** — Clonazione vocale integrata per Kokoro TTS con pannello di gestione cloni e ascolto di prova in tempo reale.
* 🎛️ **Architettura Audio Modulare** — Control room audio interamente riprogettata a schede modulari (Fish Speech, Kokoro, Piper, XTTS, routing audio, microfono hardware) con cache TTS unificata ad altissima velocità.
* 📑 **Paginazione & Ricerca nel Config Hub** — Hub centrale dei moduli con paginazione configurabile globale e per singola categoria, ricerca istantanea avanzata ed evidenziazione badge con scadenza automatica a 3 giorni (TTL).
* 📊 **Motore di Progresso Unificato** — Framework standardizzato per il tracciamento dei task asincroni (`hecos.core.progress`) per download, installazioni pip e routine in background sia da CLI che da WebUI.
* 📦 **Motore HPM SemVer & Badge Visivi** — Confronto semantico delle versioni per evitare falsi aggiornamenti e downgrade, arricchito da badge chiari che mostrano la versione installata rispetto a quella dello store.
* 📡 **Presenter & Playbook (Training, Coach, Roleplay)** — Motore interattivo integrato nel Core per annunci di sistema, notifiche e narrazione vocale in tempo reale (con controlli separati di Show/Hide dalla toolbar, apertura header e ON/OFF contesto). Insieme al modulo pacchettizzato **Playbook**, trasforma Hecos in una piattaforma interattiva di coaching, simulazione e apprendimento.
* 🎚️ **Preset Manager & Global Presets (`F3`)** — Pannello unificato ricercabile con contatore totale preset, statistiche di creazione e utilizzo, bozze live immediate, toggle **Enable Thinking** e **Selezione Granulare dei Tool** (con stima token in tempo reale) per combinare modelli IA, Persona, voci TTS e payload.
* 📋 **Multimodal Action Plans** — Motore agnostico di **Pianificazione Architect First (`Plan First` / `/plan`) & Ripresa Esecuzione** per **sviluppo software** (`Hecos Coder`), **shooting fotografici & storyboard sequenziali** (`Hecos Storyboard & Photo Director` + `IMAGE_GEN`), **itinerari di viaggio, ricerche e workflow** (`Hecos Action Planner` + `NETSEARCH`). Include revisione interattiva con versioning (`v1`, `v2`…), **`Esegui Piano`** / **`Prossimo Step`** / spunta manuale, selettore **`Esegui con Preset`**, checkpoint automatici (**`AgentResume`**), pannello ridimensionabile stile Presenter, finestra flottante (**Float**) & **Pop-out** multi-monitor live, salvataggio automatico Markdown in `hecos/media/action_plans/` ed export/import nativo (`.md`, `.html` stampabile lossless, `.yaml`, `.json`).
* 💻 **Hecos Coder & Workspace Runner (`system_app` modulare)** — Pacchetto opzionale per lo sviluppo software (`coder`) con **Workspace Runner** interattivo, **Monaco Workspace Explorer** integrato, **Aider Sidecar** isolato, AST Repo Map (Tree-Sitter), checkpoint Git non distruttivi, Watchdog dei processi OS e CLI Windows native (automaticamente nascosto ai non sviluppatori quando disabilitato).
* 📦 **Architettura HPM 0.40** — Migrazione completa a configurazioni Pydantic+TOML, introducendo vincoli di versione per le dipendenze e `pip_requirements` bloccati.
* 🛠️ **External Dependency Manager (EDM)** — Nuovo sistema che rileva automaticamente le dipendenze principali mancanti (Node, Tesseract, VC++), consentendo download con un clic direttamente dalla WebUI.
* 🛡️ **HPM Integrity Verification** — Nuova API `/verify` e UI della Control Room per convalidare crittograficamente i file dei pacchetti installati rispetto ai loro hash manifest firmati Ed25519.
* 🔒 **Hecos SDK (Isolamento Totale)** — Esegui i pacchetti HPM in processi isolati dedicati e ambienti virtuali indipendenti (venv) per evitare conflitti di dipendenze e blocchi del thread principale.
* ⚡ **HDCS (Comandi Diretti)** — Esegui istantaneamente oltre 150 funzioni native saltando il "cervello" dell'IA digitando `/` nella chat o con `Ctrl+Alt+Spazio` ovunque.
* ⚙️ **Motore di Automazione Flows** — Editor visuale a nodi (drag-and-drop) per la creazione di automazioni complesse multi-step, trigger e azioni con integrazione NLP vocale.
* **📅 Calendario Integrato** — Modulo calendario completo con tracciamento delle festività e codifica a colori localizzata per gli eventi.
* **⏰ Modulo Promemoria** — Pianificatore di attività basato su NLP con funzionalità di snooze e notifiche OS attive.
* **💻 Finestra Azioni (Action Window)** — Console pulita in stile terminale direttamente all'interno della UI della chat, per monitorare l'esecuzione nativa del sistema e i processi in background.
* **🎵 Nuovo Media Player** — Backend audio avanzato (VLC 64-bit + fallback FFplay) che supporta uno stato di ripresa/pausa resiliente, calcoli dinamici delle playlist e controllo del volume globale.
* 🎨 **Flux Prompt Studio** — Prompt engineering in tempo reale per Flux.1 con persistenza automatica dei metadati sidecar.
* 🖼️ **Image Metadata Injection** — I risultati dell'IA generativa ora includono sidecar JSON nascosti (.txt) contenenti prompt, seed e info sul sampler per workflow professionali.
* 🎭 **Chat UI Potenziata** — Nuovi header della chat con nomi Utente/Persona visibili, timestamp e posizionamento migliorato delle azioni messaggio (Copia/Modifica/Rigenera).
* 🔄 **Rigenerazione Corretta** — Risolti i problemi critici di duplicazione della cronologia e mismatch della sessione durante la rigenerazione dei messaggi.
* 🗃️ **Archivio Chat Dual-Mode** — Sistema di archiviazione contestuale con ripristino di singole chat e funzionalità di cancellazione di massa.
* 🧠 **RAG ad Alte Prestazioni (FastEmbed)** — Memoria vettoriale multi-tenant nativa per CPU, con ONNX e LanceDB per un'ingestione istantanea dei documenti.
* 🔐 **Isolamento Vault per Utente** — Architettura di memoria consolidata che garantisce l'assoluta separazione della privacy per i dati semantici e la cronologia per ciascun profilo.
* 🛡️ **Architettura Privacy a 3 Livelli** — Gestione sessioni unificata con le modalità **Normale**, **Auto-Wipe** (RAM-only, cancellazione all'uscita) e **Incognito** (modalità fantasma).
* 📦 **Hecos Module Manager (HPM)** — Centro di controllo unificato per l'estensibilità universale, organizzato in **Package Library**, **Core System**, **Widget Layout** e **Store**. Installa facilmente plugin, System App, widget, persona e pannelli via drag-and-drop con pacchetti `.hpkg` isolati e firmati Ed25519.
* 🔌 **Universal Tool Hub (MCP Bridge)** — Supporto nativo per il **Model Context Protocol**. Collegati a migliaia di tool AI esterni con un solo click.
* 🔭 **Deep MCP Discovery** — Explorer avanzato con ricerca multi-registry (Smithery, MCPSkills, GitHub) e installazione immediata.
* 🔒 **Hecos PKI Professionale (HTTPS)** — Certificazione Root CA self-signed integrata per un'esperienza "Green Lock" (lucchetto verde) di sicurezza su tutti i dispositivi della LAN.
* 🏗️ **Plugin WebUI Nativo** — Interfaccia ad alte prestazioni ottimizzata per desktop e dispositivi mobile.
* 🎛️ **Control Room e Widget** — Una dashboard personalizzabile in stile masonry per i widget in tempo reale e la telemetria dell'OS.
* 🌐 **Browser Automation** — Plugin nativo per l'interazione semantica web e lo scraping.
* ⌨️ **OS Automation** — Plugin nativo per il controllo programmatico di mouse e tastiera.
* 💾 **Hecos Drive (File Manager)** — Gestione file e editor integrato con interfaccia a doppio pannello.

---

## 🧠 Come Funziona
Hecos è costruito attorno a una struttura altamente modulare a 8 livelli. Tutto è un **modulo**:
* **Core Modules** → Funzioni di sistema e OS integrate non rimovibili.
* **Plugins** → Strumenti reattivi e capacità chiamate dall'IA (sistema, web, media, ecc.).
* **Apps** → Mini-applicazioni autonome con UI e ciclo di vita indipendenti.
* **Personas** → Profili comportamentali e personalità IA installabili.
* **Widgets** → Componenti frontend interattivi per la dashboard della Control Room.
* **Themes** → Pacchetti CSS personalizzati per lo stile dell'interfaccia.
* **Skill Packs** → Pacchetti aggiuntivi di comandi slash (`/`) per la chat.
* **MCP Servers** → Bridge universali per tool esterni tramite il Model Context Protocol.

L'AI genera comandi strutturati che vengono interpretati ed eseguiti attraverso il sistema di plugin.

---

### 🎭 L'Anima della Macchina: Persona Native

Una capacità fondamentale di Hecos è il cambio nativo della Personalità (**Personality Switching**). Hecos non è un assistente freddo e rigido: adatta il suo comportamento, il tono e il carattere in base alla persona caricata. Ogni personalità è programmata per agire in modo diverso e ricoprire un ruolo unico nella tua vita quotidiana.

<p align="center">
  <img src="https://raw.githubusercontent.com/Hecos-Project/hecos/main/hecos/assets/Urania_9800_Logo.png" width="400">
  <br>
  <em>Urania 9800, la mascotte ufficiale di Hecos e la tua amica fidata di tutti i giorni.</em>
</p>

Pronte all'uso, Hecos include diverse personalità preconfigurate:
* **Hecos System Soul** — Il sistema centrale neutro, rigido e distaccato. Perfetto per l'automazione pura e compiti di precisione.
* **Urania 9800** — La mascotte vivace. Una vera amica di tutti i giorni, progettata per interazioni empatiche, allegre e informali.
* **Sebastian Pro** — Il maggiordomo perfetto e altamente professionale. Educato, efficiente e pronto a servire.
* **Atlas** — L'imponente e autorevole custode digitale.
* **Nova X-01** — Un'entità robotica precisa e analitica per chi preferisce interazioni puramente logiche.

Puoi scambiare al volo queste personalità in qualsiasi momento, cambiando non solo la voce e il tono, ma l'anima stessa del sistema.

---

### 📢 Presenter & Playbooks: Training, Coaching & Roleplay

Il **Presenter** è un motore integrato nativamente nel Core di Hecos per la gestione di annunci di sistema, notifiche attive e commenti in tempo reale con narrazione vocale.

Grazie all'integrazione con il modulo pacchettizzato **Playbook**, Hecos va oltre il classico assistente e si trasforma in una piattaforma completa di training, coaching e simulazione:
* 🎓 **Sistema di Training & Coaching Interattivo** — Guida l'utente passo-passo attraverso procedure operative, task tecnici complessi o percorsi di studio strutturati.
* 🗣️ **Apprendimento Linguistico** — Esercitati in conversazioni in lingua straniera con correzioni dal vivo, feedback grammaticali e pronuncia guidata.
* 🎭 **Roleplay & Scenari Dinamici** — Simula colloqui di lavoro, negoziazioni commerciali o avventure narrative con personaggi IA governati da direttive e condizioni d'innesco precise.

---

### 📋 Multimodal Action Plans: Codice, Storyboard & Workflow

Il sottosistema **Multimodal Action Plans** collega la **progettazione strutturata** all'**esecuzione autonoma step-by-step** in qualunque dominio creativo, tecnico o operativo:
* 📐 **Modalità Architetto (`Plan First` / `/plan`):** Progetta e revisiona Blueprint Markdown ricchi (`title`, `goal`, specifiche tecniche o *Continuity Bible* fotografiche e step numerati) *prima* di scrivere file o generare immagini.
* 🎯 **Agnostico per Natura + Preset Dedicati:** Abbina qualsiasi piano al Global Preset ideale tramite **`Esegui con Preset`** — `Hecos Coder` per il codice, `Hecos Storyboard & Photo Director` per sequenze `IMAGE_GEN`, o `Hecos Action Planner` per viaggi, ricerche e scalette operative.
* ⏭️ **Controllo Granulare & Ripresa:** Esegui tutto il piano in sequenza (**`Esegui Piano`**), uno scatto/step alla volta (**`Prossimo Step`**) oppure spunta a mano gli step — con protezione anti-interruzioni e ripresa **`AgentResume`**.
* 🪟 **Workspace Staccabile & Salvataggio Automatico:** Ridimensiona con controlli righe stile Presenter, stacca la finestra (**Float**) o aprila su un secondo monitor (**Pop-out** su `/action-plan-viewer`), ritrova tutti i piani salvati in `hecos/media/action_plans/` ed esporta/importa nativamente in **Markdown (`.md`)**, **`.html`** standalone stampabile, **`.yaml`** o **`.json`**.

---

## ⚡ Avvio Rapido (Installazione Ufficiale Unificata)

### 1. Consigliato — Installer Grafico Ufficiale (1 clic, senza Python)

<p align="center">
  <a href="https://github.com/Hecos-Project/Hecos/releases/latest/download/INSTALL_HECOS_WINDOWS.zip">
    <img src="https://img.shields.io/badge/Scarica_Installer-Windows_(ZIP)-00e5ff?style=for-the-badge&logo=windows&logoColor=080a12" alt="Scarica Installer Windows">
  </a>
  &nbsp;
  <a href="https://github.com/Hecos-Project/Hecos/releases/latest/download/INSTALL_HECOS_LINUX.zip">
    <img src="https://img.shields.io/badge/Scarica_Installer-Linux_%2F_macOS_(ZIP)-5b7dff?style=for-the-badge&logo=linux&logoColor=white" alt="Scarica Installer Linux/macOS">
  </a>
</p>

**Non serve avere Python installato prima.** Scarica lo ZIP per il tuo sistema operativo, estrailo e avvia l'installer:

* **Windows:** fai doppio clic su **`INSTALL_HECOS_WINDOWS.bat`** *(se Windows SmartScreen mostra un avviso, clicca **Ulteriori informazioni → Esegui comunque**)*.
* **Linux / macOS:** esegui **`bash INSTALL_HECOS_LINUX.sh`** — oppure direttamente da terminale:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/Hecos-Project/Hecos/main/INSTALL_HECOS_LINUX.sh | bash
  ```

La **finestra guidata a 5 step** ti permette di scegliere **Hecos Completo (Core + Tray — Consigliato)**, **Solo Core** o **Solo Tray**, selezionare **qualsiasi disco o cartella** (evitando spazi, accenti o caratteri speciali), seguire l'avanzamento in tempo reale, verificare tutto con **Doctor** e avviare Hecos subito.

### 2. Sviluppatori / Clone Manuale
```bash
git clone https://github.com/Hecos-Project/Hecos.git
cd Hecos
```
Poi lancia **`INSTALL_HECOS_WINDOWS.bat`** / **`bash INSTALL_HECOS_LINUX.sh`** (per il wizard grafico) oppure **`scripts\windows\setup\HECOS_SETUP_WIZARD.bat`** / **`bash scripts/linux/setup/HECOS_SETUP_WIZARD.sh`** (per il setup CLI, `--unattended` o `--doctor`).

### 3. Launcher, Setup CLI e Script di Utilità

| Piattaforma | Script | Descrizione |
| :--- | :--- | :--- |
| **Windows** | `INSTALL_HECOS_WINDOWS.bat` | **Installer Grafico Unificato Ufficiale** (Core + Tray, finestra a 5 step) |
| **Linux / macOS** | `INSTALL_HECOS_LINUX.sh` | **Installer Grafico Unificato Ufficiale** (supporta `--cli`, `--unattended`, fallback headless) |
| **Windows** | `HECOS GLOBAL LAUNCHER.bat` | Menu da terminale: Setup, WebUI, Console, Coding Studio CLI & **Doctor** |
| **Linux / macOS** | `HECOS GLOBAL LAUNCHER.sh` | Menu da terminale: Setup, WebUI, Console & **Doctor** |
| **Windows** | `scripts\windows\setup\HECOS_SETUP_WIZARD.bat` | Setup & Riparazione CLI (`--unattended`, `--doctor`, `--gui`) |
| **Linux / macOS** | `scripts/linux/setup/HECOS_SETUP_WIZARD.sh` | Setup & Riparazione CLI (`--unattended`, `--doctor`, `--gui`) |
| **Windows** | `HECOS_WEBUI_RUN_WIN.bat` | Avvia SOLO l'interfaccia Web e il Watchdog |
| **Linux / macOS** | `HECOS_WEBUI_RUN_LINUX.sh` | Avvia SOLO l'interfaccia Web e il Watchdog |
| **Windows** | `scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat` | Avvia SOLO la Console Terminale |
| **Linux / macOS** | `scripts/linux/run/HECOS_CONSOLE_RUN.sh` | Avvia SOLO la Console Terminale |
| **Repo Tray** | `START_HECOS_TRAY_WIN.bat` / `START_HECOS_TRAY_LINUX.sh` | Avvia Hecos Tray & Dashboard in background |

### 4. Configurazione e Primo Avvio
Hecos è progettato per un'esperienza professionale "scarica e gioca".
- Al primo avvio, il sistema rileverà l'assenza di `system.yaml` e `routing_overrides.yaml`.
- **Genererà automaticamente** questi file copiando i modelli da `hecos/config/data/*.example`.
- Troverai la tua configurazione personale in `hecos/config/data/system.yaml` (impostazioni principali) e `routing_overrides.yaml` (regole di instradamento AI).
- **Consiglio da esperto**: Usa il [Routing Editor] integrato nella WebUI per modificare in sicurezza queste regole senza toccare il codice.

### 🔐 Login & Autenticazione
Hecos richiede l'autenticazione obbligatoria. Il login predefinito al primo avvio è:
- **Username:** `admin`
- **Password:** `hecos`

Consigliamo caldamente di modificare la password immediatamente dal pannello **Utenti** all'interno delle impostazioni di configurazione.

**Ripristino Password:**
Se rimani chiuso fuori, esegui `python scripts/reset_admin.py` dal terminale per forzare una nuova password, oppure elimina manualmente il file `memory/users.db` per ripristinare i valori predefiniti di sistema.

### 🛡️ Modalità Stealth (Senza Finestre)
Se desideri che Hecos giri completamente in background senza alcuna finestra di terminale visibile:
1. **Usa l'Icona Tray**: Avvia Hecos tramite l'icona nella barra di sistema. Gestirà i componenti di sistema in modo invisibile in background.
2. **Avvio Silenzioso**: Usa `START_HECOS_SILENT_WIN.vbs` per un avvio al 100% invisibile (senza finestre di console).
3. **Recupero Manuale**: Se chiudi l'icona per errore, usa `START_HECOS_TRAY_WIN.bat`.

---

## 💻 Compatibilità di Piattaforma e Sistemi Operativi

Nonostante molti pacchetti di estensione dell'ecosistema Hecos (come **Browser Automation**, **Messenger**, **Calendar**, **Weather Pro**, **Mail**, **Image Gen**, **Reminder**, **Lists**, **Maps** e **Quick Links**) siano totalmente multipiattaforma e progettati per funzionare su Linux e macOS, **il sistema core di Hecos, al momento, è stato testato unicamente su Windows 10 e 11**.

Eseguire il sistema core su Linux o macOS è possibile, ma potrebbe richiedere aggiustamenti manuali, e alcune funzionalità native avanzate (come l'ispezione della UI nel pacchetto PC Automation) sono progettate specificamente per Windows.

---

## 🛠️ Requisiti di Sistema Essenziali (Windows)
Se hai appena reinstallato Windows o stai configurando Hecos per la prima volta, devi assicurarti che questi pacchetti di sistema **fondamentali** siano presenti affinché tutti i moduli funzionino correttamente.

💡 **NOVITÀ (v0.45.0 - EDM)**: Hecos ora integra l'**External Dependency Manager (EDM)**! Se Tesseract, Node.js o VC++ Redistributable non sono installati, l'EDM li rileverà automaticamente e ti permetterà di scaricarli in background tramite un click dalla WebUI attingendo direttamente dal repository GitHub `Hecos-Dependencies`. In alternativa, puoi installarli manualmente:

1. ⚙️ **Microsoft Visual C++ Redistributable (Obbligatorio)**
   - *A cosa serve*: Richiesto dal motore di Memoria RAG (ONNX/FastEmbed). Senza questo pacchetto riceverai errori relativi a DLL mancanti e la ricerca sui documenti non funzionerà.
   - *Download*: 👉 [Scarica VC++ Redist x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)

2. 🎵 **VLC Media Player 64-bit (Obbligatorio)**
   - *A cosa serve*: Il motore Audio e il Media Player integrato di Hecos utilizzano le librerie di VLC in background per riprodurre musica, allarmi e l'output vocale TTS.
   - *Download*: 👉 [Scarica VLC 64-bit](https://www.videolan.org/vlc/download-windows.html)

3. 👁️ **Tesseract OCR (Consigliato per la Visione)**
   - *A cosa serve*: Necessario per le capacità visive avanzate e per leggere il testo sullo schermo tramite OCR (`pytesseract`). 
   - *Download*: 👉 [Scarica Tesseract OCR per Windows](https://github.com/UB-Mannheim/tesseract/wiki)

4. 🟢 **Node.js (Consigliato / Richiesto per lo sviluppo e build del Canvas)**
   - *A cosa serve*: Necessario per compilare, buildare e gestire le dipendenze del modulo dell'Editor Visuale dei Flussi (ReactFlow/Vite). Se hai bisogno di compilare il frontend del canvas (`npm run build`), Node.js è richiesto.
   - *Download*: 👉 [Scarica Node.js LTS](https://nodejs.org/)

---

### 📦 Installazione Offline (Cartella `dependencies`)
Per tua comodità, tutti i pacchetti di installazione necessari sono inclusi offline direttamente all'interno della cartella `dependencies/` alla radice del progetto:
* `dependencies/VC_redist.x64.exe` -> Microsoft Visual C++ Redistributable (ONNX/RAG)
* `dependencies/node-v24.16.0-x64.msi` -> Node.js LTS (Canvas / Frontend Build)
* `dependencies/tesseract-ocr-w64-setup-5.5.0.20241111.exe` -> Tesseract OCR (Visione)

*Nota: Consigliamo caldamente di installare questi componenti prima di avviare il setup automatico di Hecos.*

---

## 🧠 Backend AI Supportati (Motori LLM)

Hecos è completamente offline di default e richiede un motore AI locale per elaborare logica e conversazione. Durante il setup iniziale, devi installare uno dei backend indipendenti qui sotto. Hecos li rileverà automaticamente.

### 🔹 1. Ollama (Consigliato)
Facile da usare, veloce e ottimizzato. Funge da servizio in background.
- **Download**: 👉 https://ollama.com/download
- **Setup**: Una volta installato, apri il tuo terminale/prompt dei comandi ed esegui `ollama run llama3.2` per scaricare e testare un modello leggero e veloce. Hecos lo rileverà istantaneamente.

### 🔹 2. Llama.cpp (Alternativa)
Lo standard di riferimento per eseguire modelli locali grezzi con massima efficienza e personalizzazione.
- **Setup**: Avvia il tuo server `llama.cpp` sulla porta predefinita. Hecos è pienamente compatibile e reindirizzerà le richieste tramite il suo proxy interno.

### 🔹 3. KoboldCpp (Alternativa)
Perfetto per modelli manuali GGUF e hardware più datato senza pesanti installazioni.
- **Download**: 👉 https://github.com/LostRuins/koboldcpp/releases
- **Setup**: Scarica il file `.exe` (o il binario Linux), fai doppio clic, seleziona qualsiasi modello GGUF scaricato da HuggingFace e avvialo. Hecos si connetterà automaticamente tramite la porta `5001`.

---

## 🔌 Sistema di Plugin
Hecos utilizza un'architettura dinamica. Ogni plugin può registrare comandi, eseguire azioni di sistema ed estendere le capacità dell'AI.

Plugin inclusi:
* **Controllo di sistema e Gestione file**
* **Automazione Web e Dashboard hardware**
* **Controllo media e Cambio modello**
* **Gestione della memoria**

Puoi installare nuovi pacchetti dinamicamente trascinando i file `.hpkg` nel **Module Manager** all'interno della WebUI. Questi pacchetti standalone contengono la propria logica, pannelli UI e schemi di configurazione. Tutti i pacchetti sono verificati tramite firme digitali Ed25519 per la massima sicurezza.

---

## 💾 Sistemi di Memoria e Voce

### 🗄️ Sistema di Memoria
Hecos includes un livello di memoria persistente gestito da SQLite per un'archiviazione locale leggera. Memorizza le conversazioni, mantiene l'identità e salva le preferenze dell'utente.

### 🎙️ Sistema Vocale
* **Input Speech-to-text** (da voce a testo)
* **Output Text-to-speech Avanzato** (Dotato sia di Kokoro TTS che di Piper TTS per generare voci locali naturali e ad alta fedeltà)
* **Interazione in tempo reale**

---

## 🔗 Integrazioni e Privacy

### 🤝 Integrazioni
Hecos può integrarsi con:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (tramite bridge)

### 🔐 Privacy al Primo Posto
Hecos è progettato con un focus rigoroso su utilità e discrezione: funziona al 100% localmente, nessun servizio cloud obbligatorio e pieno controllo sui propri dati.

---

## 🛣️ Tabella di Marcia (Roadmap)
- [ ] 📱 Integrazione Telegram (controllo remoto)
- [ ] 🧠 Sistema di memoria avanzato
- [ ] 🤖 Architettura multi-agente
- [ ] 🛒 Marketplace dei plugin
- [ ] 🎨 UI/UX migliorata

---

## ⚠️ Esclusione di Responsabilità (Disclaimer)
Hecos può eseguire comandi a livello di sistema e controllare il tuo ambiente. Usalo responsabilmente. L'autore non è responsabile per usi impropri o danni.

---

## 📜 Licenza
Licenza GPL-3.0

---

## 👥 Crediti e Contatti
Sviluppatore Capo: Antonio Meloni (Tony)
Email Ufficiale: hecos.project@gmail.com

---

## 📚 Documentazione
Hecos utilizza un sistema di documentazione modulare localizzato in EN, IT e ES.

### Accesso Locale (Modulare)
Le guide dettagliate si trovano nella cartella `docs/`:
- 📖 **[Guida Unificata (ITA)](docs/GUIDA_UNIFICATA_ITA.md)**: Tutto ciò che devi sapere sulla v0.44.0.
- 🏗️ **[Guida Tecnica](docs/tech/)**: (Admin/Dev) Dettagli sull'architettura di sistema e OOP.

### Accesso Online
La documentazione è inoltre sincronizzata con la **[GitHub Wiki](https://github.com/Hecos-Project/Hecos/wiki)**.

---

## 💡 Visione
Hecos mira a diventare una piattaforma di assistenza AI locale completamente autonoma: un'alternativa privata ed estensibile ai sistemi AI basati su cloud, focalizzata esclusivamente sul servire e migliorare la vita umana.