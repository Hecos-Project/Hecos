# 🌌 Progetto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/zentra/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo Zentra">
</p>

# Zentra Core - Versione 0.18.2 (Runtime Alpha)
Lingua: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Sistema Operativo IA Nativo e Modulare (Privato, Veloce, Semplice)**

---

> [!IMPORTANT]
> **Stato Runtime Alpha**: Zentra Core è attualmente in `v0.18.2`. Questo è un Livello Operativo IA locale che funge da ponte tra il ragionamento ad alto livello e l'esecuzione di sistema root.

## 🚀 Panoramica
**Zentra Core** è un **Sistema Operativo IA Nativo e Modulare**: un ecosistema locale che unisce AI reasoning, controllo di sistema root e networking avanzato. Trasforma l'hardware locale in un'entità digitale sovrana attraverso una dashboard professionale stile OS e un'infrastruttura di sicurezza avanzata.

Costruito su tre pilastri fondamentali:
* 🛡️ **Privacy al Primo Posto** — Funzionamento 100% locale, zero dipendenze cloud e architettura privacy a 3 livelli.
* ⚡ **Velocità Estrema** — Architettura nativa ottimizzata e sistema di plugin ad alte prestazioni per una reattività istantanea.
* 🧊 **Semplicità Assoluta** — Dashboard professionale stile OS e design modulare che rende intuitiva l'orchestrazione IA avanzata.

Ora completamente migrato a una **architettura stabile a Runtime Alpha**, Zentra 0.18.2 offre una interfaccia Web dedicata (Chat + Config) e internazionalizzazione completa. Grazie a **LiteLLM**, supporta Ollama, KoboldCpp e i principali provider cloud con streaming in tempo reale e TTS locale.

---

## ✨ Caratteristiche Principali (v0.18.2)
* 🎨 **Flux Prompt Studio** — Prompt engineering in tempo reale per Flux.1 con persistenza automatica dei metadati sidecar.
* 🖼️ **Image Metadata Injection** — I risultati dell'IA generativa ora includono sidecar JSON nascosti (.txt) contenenti prompt, seed e info sul sampler per workflow professionali.
* 🎭 **Chat UI Potenziata** — Nuovi header della chat con nomi Utente/Persona visibili, timestamp e posizionamento migliorato delle azioni messaggio (Copia/Modifica/Rigenera).
* 🔄 **Rigenerazione Corretta** — Risolti i problemi critici di duplicazione della cronologia e mismatch della sessione durante la rigenerazione dei messaggi.
* 🛡️ **Architettura Privacy a 3 Livelli** — Gestione unificata delle sessioni con modalità **Normale**, **Auto-Wipe** (memoria RAM) e **Incognito** (traccia zero).
* 🔌 **Universal Tool Hub (MCP Bridge)** — Supporto nativo per il **Model Context Protocol**. Collegati a migliaia di tool AI esterni con un solo click.
* 🔭 **Deep MCP Discovery** — Explorer avanzato con ricerca multi-registry (Smithery, MCPSkills, GitHub) e installazione immediata.
* 🔒 **Zentra PKI Professionale (HTTPS)** — Certificazione Root CA integrata per abilitare Mic/Camera su tutta la LAN in sicurezza.
* 🏗️ **Plugin WebUI Nativo** — Interfaccia ad alte prestazioni ottimizzata per desktop e dispositivi mobile.
* 🗂️ **Zentra Drive (File Manager)** — Gestione file e editor integrato con interfaccia a doppio pannello.

---

## 🧠 Come Funziona
Zentra Core è costruito attorno a un'architettura modulare:
* **Core** → Instradamento AI, elaborazione, esecuzione.
* **Plugins** → Azioni e capacità (sistema, web, media, ecc.).
* **Memory** → Identità e archiviazione persistente.
* **UI** → Livello di interazione con l'utente.
* **Bridge** → Integrazioni esterne e API.

L'AI genera comandi strutturati che vengono interpretati ed eseguiti attraverso il sistema di plugin.

---

## ⚡ Avvio Rapido

### 1. Clona il repository
```bash
git clone https://github.com/Zentra-Core/zentra-core.github.io.git
cd zentra-core.github.io
```

### 2. Installa le dipendenze
```bash
pip install -r requirements.txt
```

### 3. Avvia Zentra
```bash
python main.py
```

---

## 🧠 Backend AI Supportati (Motori LLM)

Zentra è completamente offline di default e richiede un motore AI locale per elaborare logica e conversazione. Durante il setup iniziale, devi installare uno dei backend indipendenti qui sotto. Zentra li rileverà automaticamente.

### 🔹 1. Ollama (Consigliato)
Facile da usare, veloce e ottimizzato. Funge da servizio in background.
- **Download**: 👉 https://ollama.com/download
- **Setup**: Una volta installato, apri il tuo terminale/prompt dei comandi ed esegui `ollama run llama3.2` per scaricare e testare un modello leggero e veloce. Zentra lo rileverà istantaneamente.

### 🔹 2. KoboldCpp (Alternativa)
Perfetto per modelli manuali GGUF e hardware più datato senza pesanti installazioni.
- **Download**: 👉 https://github.com/LostRuins/koboldcpp/releases
- **Setup**: Scarica il file `.exe` (o il binario Linux), fai doppio clic, seleziona qualsiasi modello GGUF scaricato da HuggingFace e avvialo. Zentra si connetterà automaticamente tramite la porta `5001`.

---

## 🔌 Sistema di Plugin
Zentra utilizza un'architettura dinamica. Ogni plugin può registrare comandi, eseguire azioni di sistema ed estendere le capacità dell'AI.

Plugin inclusi:
* **Controllo di sistema e Gestione file**
* **Automazione Web e Dashboard hardware**
* **Controllo media e Cambio modello**
* **Gestione della memoria**

---

## 💾 Sistemi di Memoria e Voce

### 🗄️ Systema di Memoria
Zentra include un livello di memoria persistente gestito da SQLite per un'archiviazione locale leggera. Memorizza le conversazioni, mantiene l'identità e salva le preferenze dell'utente.

### 🎙️ Sistema Vocale
* **Input Speech-to-text** (da voce a testo)
* **Output Text-to-speech** (da testo a voce)
* **Interazione in tempo reale**

---

## 🔗 Integrazioni e Privacy

### 🤝 Integrazioni
Zentra può integrarsi con:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (tramite bridge)

### 🔐 Privacy al Primo Posto
Zentra è progettato pensando alla privacy: funziona al 100% localmente, nessun servizio cloud obbligatorio e pieno controllo sui propri dati.

---

## 🛣️ Tabella di Marcia (Roadmap)
- [ ] 📱 Integrazione Telegram (controllo remoto)
- [ ] 🧠 Sistema di memoria avanzato
- [ ] 🤖 Architettura multi-agente
- [ ] 🛒 Marketplace dei plugin
- [ ] 🎨 UI/UX migliorata

---

## ⚠️ Esclusione di Responsabilità (Disclaimer)
Zentra può eseguire comandi a livello di sistema e controllare il tuo ambiente. Usalo responsabilmente. L'autore non è responsabile per usi impropri o danni.

---

## 📜 Licenza
Licenza GPL-3.0

---

## 👥 Crediti e Contatti
Sviluppatore Capo: Antonio Meloni (Tony)
Email Ufficiale: zentra.core.systems@gmail.com

---

## 📚 Documentazione
- 📖 **[Guida Unificata (ITA)](docs/GUIDA_UNIFICATA_ITA.md)**: Tutto ciò che devi sapere sulla v0.17.0.
- 🏗️ **[Guida all'Architettura](docs/TECHNICAL_GUIDE.md)**

- 🔌 **[Sviluppo Plugin](docs/PLUGINS_DEV.md)**
- 📁 **[Mappa Struttura](docs/ARCHITECTURE_MAP.md)**

---

## 💡 Visione
Zentra Core mira a diventare una piattaforma di assistenza AI locale completamente autonoma: un'alternativa privata ed estensibile ai sistemi AI basati su cloud.