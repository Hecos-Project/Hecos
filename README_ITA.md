# 🌌 Progetto Hecos
<p align="center">
  <img src="hecos/assets/Hecos_Logo_Banner.png" width="400" alt="Logo Hecos">
</p>

# Hecos - Versione 0.44.0 (Runtime Alpha)
Lingua: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Hecos
**Helping Companion System (Privato, Rapido, Semplice)**[cite: 1]

---

> **Stato Runtime Alpha**: Hecos è attualmente in `v0.44.0`[cite: 1]. Questo è un Helping Companion System che funge da ponte tra il ragionamento ad alto livello e l'esecuzione di sistema root[cite: 1].

## 🚀 Panoramica
**Hecos** è un **Helping Companion System**: un ecosistema locale progettato per unire fluidamente tecnologia e vita umana, combinando AI reasoning, automazione visiva ed esecuzione di sistema diretta[cite: 1]. Invece di inseguire concetti astratti come la sovranità digitale, Hecos si concentra su un'unica missione pragmatica: **migliorare la vita umana**, trasformando l'hardware locale in uno strumento pratico ed estremamente efficiente per tutti i giorni[cite: 1].

Costruito su tre pilastri fondamentali:
* 🛡️ **Privacy al Primo Posto** — Funzionamento 100% locale, zero dipendenze cloud e architettura privacy a 3 livelli[cite: 1].
* ⚡ **Velocità Estrema** — Architettura nativa ottimizzata e sistema di plugin ad alte prestazioni per una reattività istantanea[cite: 1].
* 🧊 **Semplicità Assoluta** — Dashboard professionale e design modulare che rende intuitiva l'orchestrazione IA avanzata[cite: 1].

Ora completamente migrato a una **architettura stabile a Runtime Alpha**, Hecos 0.44.0 offre una interfaccia Web dedicata (Chat + Config) e internazionalizzazione completa[cite: 1]. Grazie a **LiteLLM**, supporta Ollama, KoboldCpp e i principali provider cloud con streaming in tempo reale e TTS locale[cite: 1].

---

## ✨ Caratteristiche Principali (v0.44.0)
* 🔒 **Hecos SDK (Isolamento Totale)** — Esegui i pacchetti HPM in processi isolati dedicati e ambienti virtuali indipendenti (venv) per evitare conflitti di dipendenze e blocchi del thread principale.
* ⚡ **HDCS (Comandi Diretti)** — Esegui istantaneamente oltre 150 funzioni native saltando il "cervello" dell'IA digitando `/` nella chat o con `Ctrl+Alt+Spazio` ovunque[cite: 1].
* ⚙️ **Motore di Automazione Flows** — Editor visuale a nodi (drag-and-drop) per la creazione di automazioni complesse multi-step, trigger e azioni con integrazione NLP vocale[cite: 1].
* **📅 Calendario Integrato** — Modulo calendario completo con tracciamento delle festività e codifica a colori localizzata per gli eventi[cite: 1].
* **⏰ Modulo Promemoria** — Pianificatore di attività basato su NLP con funzionalità di snooze e notifiche OS attive[cite: 1].
* **💻 Finestra Azioni (Action Window)** — Console pulita in stile terminale direttamente all'interno della UI della chat, per monitorare l'esecuzione nativa del sistema e i processi in background[cite: 1].
* **🎵 Nuovo Media Player** — Backend audio avanzato (VLC 64-bit + fallback FFplay) che supporta uno stato di ripresa/pausa resiliente, calcoli dinamici delle playlist e controllo del volume globale[cite: 1].
* 🎨 **Flux Prompt Studio** — Prompt engineering in tempo reale per Flux.1 con persistenza automatica dei metadati sidecar[cite: 1].
* 🖼️ **Image Metadata Injection** — I risultati dell'IA generativa ora includono sidecar JSON nascosti (.txt) contenenti prompt, seed e info sul sampler per workflow professionali[cite: 1].
* 🎭 **Chat UI Potenziata** — Nuovi header della chat con nomi Utente/Persona visibili, timestamp e posizionamento migliorato delle azioni messaggio (Copia/Modifica/Rigenera)[cite: 1].
* 🔄 **Rigenerazione Corretta** — Risolti i problemi critici di duplicazione della cronologia e mismatch della sessione durante la rigenerazione dei messaggi[cite: 1].
* 🗃️ **Archivio Chat Dual-Mode** — Sistema di archiviazione contestuale con ripristino di singole chat e funzionalità di cancellazione di massa[cite: 1].
* 🧠 **RAG ad Alte Prestazioni (FastEmbed)** — Memoria vettoriale multi-tenant nativa per CPU, con ONNX e LanceDB per un'ingestione istantanea dei documenti[cite: 1].
* 🔐 **Isolamento Vault per Utente** — Architettura di memoria consolidata che garantisce l'assoluta separazione della privacy per i dati semantici e la cronologia per ciascun profilo[cite: 1].
* 🛡️ **Architettura Privacy a 3 Livelli** — Gestione sessioni unificata con le modalità **Normale**, **Auto-Wipe** (RAM-only, cancellazione all'uscita) e **Incognito** (modalità fantasma)[cite: 1].
* 📦 **Hecos Package Manager (HPM)** — Il tassello definitivo per l'estensibilità universale. Un installatore centralizzato e dinamico che supporta pacchetti standalone `.hpkg`. Installa facilmente plugin di terze parti, widget e pannelli di configurazione con drag-and-drop, configurazioni isolate e firme digitali Ed25519[cite: 1].
* 🔌 **Universal Tool Hub (MCP Bridge)** — Supporto nativo per il **Model Context Protocol**. Collegati a migliaia di tool AI esterni con un solo click[cite: 1].
* 🔭 **Deep MCP Discovery** — Explorer avanzato con ricerca multi-registry (Smithery, MCPSkills, GitHub) e installazione immediata[cite: 1].
* 🔒 **Hecos PKI Professionale (HTTPS)** — Certificazione Root CA self-signed integrata per un'esperienza "Green Lock" (lucchetto verde) di sicurezza su tutti i dispositivi della LAN[cite: 1].
* 🏗️ **Plugin WebUI Nativo** — Interfaccia ad alte prestazioni ottimizzata per desktop e dispositivi mobile[cite: 1].
* 🎛️ **Control Room e Widget** — Una dashboard personalizzabile in stile masonry per i widget in tempo reale e la telemetria dell'OS[cite: 1].
* 🌐 **Browser Automation** — Plugin nativo per l'interazione semantica web e lo scraping[cite: 1].
* ⌨️ **OS Automation** — Plugin nativo per il controllo programmatico di mouse e tastiera[cite: 1].
* 💾 **Hecos Drive (File Manager)** — Gestione file e editor integrato con interfaccia a doppio pannello[cite: 1].

---

## 🧠 Come Funziona
Hecos è costruito attorno a una struttura altamente modulare a 8 livelli. Tutto è un **modulo**[cite: 1]:
* **Core Modules** → Funzioni di sistema e OS integrate non rimovibili[cite: 1].
* **Plugins** → Strumenti reattivi e capacità chiamate dall'IA (sistema, web, media, ecc.)[cite: 1].
* **Apps** → Mini-applicazioni autonome con UI e ciclo di vita indipendenti[cite: 1].
* **Personas** → Profili comportamentali e personalità IA installabili[cite: 1].
* **Widgets** → Componenti frontend interattivi per la dashboard della Control Room[cite: 1].
* **Themes** → Pacchetti CSS personalizzati per lo stile dell'interfaccia[cite: 1].
* **Skill Packs** → Pacchetti aggiuntivi di comandi slash (`/`) per la chat[cite: 1].
* **MCP Servers** → Bridge universali per tool esterni tramite il Model Context Protocol[cite: 1].

L'AI genera comandi strutturati che vengono interpretati ed eseguiti attraverso il sistema di plugin[cite: 1].

---

### 🎭 L'Anima della Macchina: Persona Native

Una capacità fondamentale di Hecos è il cambio nativo della Personalità (**Personality Switching**). Hecos non è un assistente freddo e rigido: adatta il suo comportamento, il tono e il carattere in base alla persona caricata. Ogni personalità è programmata per agire in modo diverso e ricoprire un ruolo unico nella tua vita quotidiana[cite: 1].

<p align="center">
  <img src="https://raw.githubusercontent.com/Hecos-Project/hecos/main/hecos/assets/Urania_9800_Logo.png" width="400">
  <br>
  <em>Urania 9800, la mascotte ufficiale di Hecos e la tua amica fidata di tutti i giorni.</em>[cite: 1]
</p>

Pronte all'uso, Hecos include diverse personalità preconfigurate:
* **Hecos System Soul** — Il sistema centrale neutro, rigido e distaccato. Perfetto per l'automazione pura e compiti di precisione[cite: 1].
* **Urania 9800** — La mascotte vivace. Una vera amica di tutti i giorni, progettata per interazioni empatiche, allegre e informali[cite: 1].
* **Sebastian Pro** — Il maggiordomo perfetto e altamente professionale. Educato, efficiente e pronto a servire[cite: 1].
* **Atlas** — L'imponente e autorevole custode digitale[cite: 1].
* **Nova X-01** — Un'entità robotica precisa e analitica per chi preferisce interazioni puramente logiche[cite: 1].

Puoi scambiare al volo queste personalità in qualsiasi momento, cambiando non solo la voce e il tono, ma l'anima stessa del sistema[cite: 1].

---

## ⚡ Avvio Rapido (Installazione One-Click)
Il modo più semplice per installare e configurare Hecos da zero è utilizzare il **Wizard di Setup Universale**[cite: 1].

### 1. Clona il repository
```bash
git clone [https://github.com/Hecos-Project/Hecos.git](https://github.com/Hecos-Project/Hecos.git)
cd Hecos
```[cite: 1]

### 2. Lancia il Setup Wizard
Esegui lo script di bootstrap per la tua piattaforma. Questo controllerà automaticamente Python, installerà le dipendenze e avvierà il wizard di configurazione nel tuo browser[cite: 1].

**Windows:**
```powershell
.\START_SETUP_HERE_WIN.bat
```[cite: 1]

**Linux:**
```bash
bash START_SETUP_HERE_LINUX.sh
```[cite: 1]

### 3. Componenti Manuali e Script di Utilità
Se preferisci gestire i componenti singolarmente o eseguire manutenzione manuale, usa questi script dedicati[cite: 1]:

| Piattaforma | Script | Descrizione |
| :--- | :--- | :--- |
| **Tutte** | `main.py` | Avvia il sistema completo (Tray + WebUI + Backend) |
| **Windows** | `RESTART_TRAY_ICON_WIN.bat` | Ripristina l'icona tray se è stata chiusa |
| **Linux** | `RESTART_TRAY_ICON_LINUX.sh` | Ripristina l'icona tray se è stata chiusa |
| **Windows** | `scripts\windows\run\HECOS_WEB_RUN_WIN.bat` | Avvia SOLO l'interfaccia Web e il Server |
| **Linux** | `scripts/linux/run/hecos_web_run.sh` | Avvia SOLO l'interfaccia Web e il Server |
| **Windows** | `scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat` | Avvia SOLO la Console Terminale (TUI) |
| **Linux** | `scripts/linux/run/HECOS_CONSOLE_RUN.sh` | Avvia SOLO la Console Terminale (TUI) |
| **Windows** | `scripts\windows\setup\INSTALL_HECOS_WIN.bat` | Installazione manuale dipendenze e Piper |
| **Linux** | `scripts/linux/setup/INSTALL_HECOS_LINUX.sh` | Installazione manuale dipendenze e Piper |[cite: 1]

### 4. Configurazione e Primo Avvio
Hecos è progettato per un'esperienza professionale "scarica e gioca"[cite: 1].
- Al primo avvio, il sistema rileverà l'assenza di `system.yaml` e `routing_overrides.yaml`[cite: 1].
- **Genererà automaticamente** questi file copiando i modelli da `hecos/config/data/*.example`[cite: 1].
- Troverai la tua configurazione personale in `hecos/config/data/system.yaml` (impostazioni principali) e `routing_overrides.yaml` (regole di instradamento AI)[cite: 1].
- **Consiglio da esperto**: Usa il [Routing Editor] integrato nella WebUI per modificare in sicurezza queste regole senza toccare il codice[cite: 1].

### 🔐 Login & Autenticazione
Hecos richiede l'autenticazione obbligatoria[cite: 1]. Il login predefinito al primo avvio è:
- **Username:** `admin`
- **Password:** `hecos`[cite: 1]

Consigliamo caldamente di modificare la password immediatamente dal pannello **Utenti** all'interno delle impostazioni di configurazione[cite: 1].

**Ripristino Password:**
Se rimani chiuso fuori, esegui `python scripts/reset_admin.py` dal terminale per forzare una nuova password, oppure elimina manualmente il file `memory/users.db` per ripristinare i valori predefiniti di sistema[cite: 1].

### 🛡️ Modalità Stealth (Senza Finestre)
Se desideri che Hecos giri completamente in background senza alcuna finestra di terminale visibile[cite: 1]:
1. **Usa l'Icona Tray**: Avvia Hecos tramite l'icona nella barra di sistema. Gestirà i componenti di sistema in modo invisibile in background[cite: 1].
2. **Avvio Silenzioso**: Usa `START_HECOS_SILENT_WIN.vbs` per un avvio al 100% invisibile (senza finestre di console)[cite: 1].
3. **Recupero Manuale**: Se chiudi l'icona per errore, usa `START_HECOS_TRAY_WIN.bat`[cite: 1].

---

## 💻 Compatibilità di Piattaforma e Sistemi Operativi

Nonostante molti pacchetti di estensione dell'ecosistema Hecos (come **Browser Automation**, **Messenger**, **Calendar**, **Weather Pro**, **Mail**, **Image Gen**, **Reminder**, **Lists**, **Maps** e **Quick Links**) siano totalmente multipiattaforma e progettati per funzionare su Linux e macOS, **il sistema core di Hecos, al momento, è stato testato unicamente su Windows 10 e 11**.

Eseguire il sistema core su Linux o macOS è possibile, ma potrebbe richiedere aggiustamenti manuali, e alcune funzionalità native avanzate (come l'ispezione della UI nel pacchetto PC Automation) sono progettate specificamente per Windows.

---

## 🛠️ Requisiti di Sistema Essenziali (Windows)
Se hai appena reinstallato Windows o stai configurando Hecos per la prima volta, devi installare questi pacchetti di sistema **fondamentali** affinché tutti i moduli funzionino correttamente[cite: 1]:

1. ⚙️ **Microsoft Visual C++ Redistributable (Obbligatorio)**
   - *A cosa serve*: Richiesto dal motore di Memoria RAG (ONNX/FastEmbed). Senza questo pacchetto riceverai errori relativi a DLL mancanti e la ricerca sui documenti non funzionerà[cite: 1].
   - *Download*: 👉 [Scarica VC++ Redist x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)[cite: 1]

2. 🎵 **VLC Media Player 64-bit (Obbligatorio)**
   - *A cosa serve*: Il motore Audio e il Media Player integrato di Hecos utilizzano le librerie di VLC in background per riprodurre musica, allarmi e l'output vocale TTS[cite: 1].
   - *Download*: 👉 [Scarica VLC 64-bit](https://www.videolan.org/vlc/download-windows.html)[cite: 1]

3. 👁️ **Tesseract OCR (Consigliato per la Visione)**
   - *A cosa serve*: Necessario per le capacità visive avanzate e per leggere il testo sullo schermo tramite OCR (`pytesseract`)[cite: 1]. 
   - *Download*: 👉 [Scarica Tesseract OCR per Windows](https://github.com/UB-Mannheim/tesseract/wiki)[cite: 1]

4. 🟢 **Node.js (Consigliato / Richiesto per lo sviluppo e build del Canvas)**
   - *A cosa serve*: Necessario per compilare, buildare e gestire le dipendenze del modulo dell'Editor Visuale dei Flussi (ReactFlow/Vite). Se hai bisogno di compilare il frontend del canvas (`npm run build`), Node.js è richiesto[cite: 1].
   - *Download*: 👉 [Scarica Node.js LTS](https://nodejs.org/)[cite: 1]

---

### 📦 Installazione Offline (Cartella `dependencies`)
Per tua comodità, tutti i pacchetti di installazione necessari sono inclusi offline direttamente all'interno della cartella `dependencies/` alla radice del progetto[cite: 1]:
* `dependencies/VC_redist.x64.exe` -> Microsoft Visual C++ Redistributable (ONNX/RAG)[cite: 1]
* `dependencies/node-v24.16.0-x64.msi` -> Node.js LTS (Canvas / Frontend Build)[cite: 1]
* `dependencies/tesseract-ocr-w64-setup-5.5.0.20241111.exe` -> Tesseract OCR (Visione)[cite: 1]

*Nota: Consigliamo caldamente di installare questi componenti prima di avviare il setup automatico di Hecos.*[cite: 1]

---

## 🧠 Backend AI Supportati (Motori LLM)

Hecos è completamente offline di default e richiede un motore AI locale per elaborare logica e conversazione[cite: 1]. Durante il setup iniziale, devi installare uno dei backend indipendenti qui sotto[cite: 1]. Hecos li rileverà automaticamente[cite: 1].

### 🔹 1. Ollama (Consigliato)
Facile da usare, veloce e ottimizzato. Funge da servizio in background[cite: 1].
- **Download**: 👉 https://ollama.com/download[cite: 1]
- **Setup**: Una volta installato, apri il tuo terminale/prompt dei comandi ed esegui `ollama run llama3.2` per scaricare e testare un modello leggero e veloce[cite: 1]. Hecos lo rileverà istantaneamente[cite: 1].

### 🔹 2. KoboldCpp (Alternativa)
Perfetto per modelli manuali GGUF e hardware più datato senza pesanti installazioni[cite: 1].
- **Download**: 👉 https://github.com/LostRuins/koboldcpp/releases[cite: 1]
- **Setup**: Scarica il file `.exe` (o il binario Linux), fai doppio clic, seleziona qualsiasi modello GGUF scaricato da HuggingFace e avvialo[cite: 1]. Hecos si connetterà automaticamente tramite la porta `5001`[cite: 1].

---

## 🔌 Sistema di Plugin
Hecos utilizza un'architettura dinamica[cite: 1]. Ogni plugin può registrare comandi, eseguire azioni di sistema ed estendere le capacità dell'AI[cite: 1].

Plugin inclusi:
* **Controllo di sistema e Gestione file**[cite: 1]
* **Automazione Web e Dashboard hardware**[cite: 1]
* **Controllo media e Cambio modello**[cite: 1]
* **Gestione della memoria**[cite: 1]

Puoi installare nuovi pacchetti dinamicamente trascinando i file `.hpkg` nel **Package Manager** all'interno della WebUI[cite: 1]. Questi pacchetti standalone contengono la propria logica, pannelli UI e schemi di configurazione[cite: 1]. Tutti i pacchetti sono verificati tramite firme digitali Ed25519 per la massima sicurezza[cite: 1].

---

## 💾 Sistemi di Memoria e Voce

### 🗄️ Sistema di Memoria
Hecos includes un livello di memoria persistente gestito da SQLite per un'archiviazione locale leggera[cite: 1]. Memorizza le conversazioni, mantiene l'identità e salva le preferenze dell'utente[cite: 1].

### 🎙️ Sistema Vocale
* **Input Speech-to-text** (da voce a testo)[cite: 1]
* **Output Text-to-speech** (da testo a voce)[cite: 1]
* **Interazione in tempo reale**[cite: 1]

---

## 🔗 Integrazioni e Privacy

### 🤝 Integrazioni
Hecos può integrarsi con:
* **Open WebUI** (chat + streaming)[cite: 1]
* **Home Assistant** (tramite bridge)[cite: 1]

### 🔐 Privacy al Primo Posto
Hecos è progettato con un focus rigoroso su utilità e discrezione: funziona al 100% localmente, nessun servizio cloud obbligatorio e pieno controllo sui propri dati[cite: 1].

---

## 🛣️ Tabella di Marcia (Roadmap)
- [ ] 📱 Integrazione Telegram (controllo remoto)[cite: 1]
- [ ] 🧠 Sistema di memoria avanzato[cite: 1]
- [ ] 🤖 Architettura multi-agente[cite: 1]
- [ ] 🛒 Marketplace dei plugin[cite: 1]
- [ ] 🎨 UI/UX migliorata[cite: 1]

---

## ⚠️ Esclusione di Responsabilità (Disclaimer)
Hecos può eseguire comandi a livello di sistema e controllare il tuo ambiente[cite: 1]. Usalo responsabilmente[cite: 1]. L'autore non è responsabile per usi impropri o danni[cite: 1].

---

## 📜 Licenza
Licenza GPL-3.0[cite: 1]

---

## 👥 Crediti e Contatti
Sviluppatore Capo: Antonio Meloni (Tony)[cite: 1]
Email Ufficiale: hecos.project@gmail.com[cite: 1]

---

## 📚 Documentazione
Hecos utilizza un sistema di documentazione modulare localizzato in EN, IT e ES[cite: 1].

### Accesso Locale (Modulare)
Le guide dettagliate si trovano nella cartella `docs/`[cite: 1]:
- 📖 **[Guida Unificata (ITA)](docs/GUIDA_UNIFICATA_ITA.md)**: Tutto ciò che devi sapere sulla v0.44.0[cite: 1].
- 🏗️ **[Guida Tecnica](docs/tech/)**: (Admin/Dev) Dettagli sull'architettura di sistema e OOP[cite: 1].

### Accesso Online
La documentazione è inoltre sincronizzata con la **[GitHub Wiki](https://github.com/Hecos-Project/Hecos/wiki)**[cite: 1].

---

## 💡 Visione
Hecos mira a diventare una piattaforma di assistenza AI locale completamente autonoma: un'alternativa privata ed estensibile ai sistemi AI basati su cloud, focalizzata esclusivamente sul servire e migliorare la vita umana[cite: 1].