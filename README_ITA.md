# 🌌 Progetto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/zentra/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo Zentra">
</p>

# Zentra Core - Versione 0.18.0 (Runtime Alpha)
Lingua: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Il tuo Assistente AI Personale Offline (Privato, Modulare, Potente)**

---

> [!WARNING]
> **Stato Runtime Alpha**: Zentra Core è attualmente in `v0.18.0`. Questa repository contiene il motore, il backend, i moduli di ragionamento IA e la WebUI nativa principale. Le funzionalità possono cambiare e il sistema non è ancora considerato stabile. Usare con cautela.

## 🚀 Panoramica
**Zentra Core** è una piattaforma di assistenza AI local-first che gira interamente sulla tua macchina.
Il sistema combina LLM locali, interazione vocale, automazione di sistema e un'architettura a plugin modulari per creare un compagno digitale completamente personalizzabile.

Ora completamente migrato a una **architettura stabile a Plugin Nativi**, Zentra 0.18.0 offre una interfaccia Web dedicata (Chat + Config) e internazionalizzazione completa. Grazie a **LiteLLM**, supporta Ollama, KoboldCpp e i principali provider cloud con streaming in tempo reale e TTS locale.

---

## ✨ Caratteristiche Principali (v0.18.0)
* 🛡️ **Architettura Privacy a 3 Livelli** — Gestione unificata delle sessioni con modalità **Normale**, **Auto-Wipe** (memoria solo RAM, cancellata alla chiusura) e **Incognito** (traccia zero). Le sessioni vengono bloccate nella modalità scelta al primo messaggio per garantire coerenza e sicurezza.
* 🔌 **Universal Tool Hub (MCP Bridge)** — Zentra ora supporta nativamente il **Model Context Protocol**. Collegati a migliaia di tool AI esterni (Brave Search, GitHub, Google Maps, ecc.) con un solo click. Scopri e gestisci i tool tramite la nuova dashboard **MCP Bridge** con inventario in tempo reale.
* 🔎 **Multi-Registry MCP Discovery** — Trova e installa nuovi strumenti con facilità direttamente dall'interfaccia. Zentra integra i principali registri MCP:
    - **Smithery.ai**: Il portale principale per i server MCP.
    - **MCPSkills**: Repository di tool e agenti guidato dalla community.
    - **GitHub & Hugging Face**: Installazione diretta dai repository sorgente.
* 👥 **Multi-User & Identity Profiles** — Supporto completo per account multipli con memorie isolate. Ogni utente ha il proprio profilo personale, avatar personalizzato e "Bio Note" private (memorie contestuali) che l'IA usa per identificarti con precisione.
* 💾 **Vault Isolati per Utente** — File personali, avatar e memorie sono archiviati in "Vault" sicuri e separati (`memory/vaults/username`), garantendo la massima privacy in ambienti condivisi.
* 🤖 **Agente Cognitivo Autonomo** — Zentra ora ragiona step-by-step (Chain of Thought), sceglie dinamicamente gli strumenti e risolve task complessi in autonomia.
* 🛡️ **Zentra Code Jail (Sandbox AST)** — Un ambiente di esecuzione nativo e isolato che permette all'IA di eseguire calcoli Python, algoritmi e test in totale sicurezza.
* 👁️ **Supporto Visione Nativa** — Capacità AI multimodali per Gemini, OpenAI e Ollama (LLaVA). Analizza immagini, foto e screenshot direttamente in chat.
* 🏗️ **Plugin WebUI Nativo** — Migrato da un bridge a un plugin core (`plugins/web_ui/`) per massime prestazioni e stabilità.
* 🔒 **Zentra PKI Professionale (HTTPS)** — Zentra ora agisce come la propria **Autorità di Certificazione (Root CA)**. Genera e firma automaticamente certificati specifici per l'host, abilitando il "Lucchetto Verde" su tutti i dispositivi. Questo sblocca le funzioni limitate dal browser come Microfono e Camera in tutta la tua LAN.
* 📱 **UI Responsive Mobile-First** — Un'interfaccia mobile completamente ridisegnata con menu hamburger off-canvas, tab di configurazione scorrevoli e un "Neural Link" ottimizzato per l'accesso ai media su iOS e Android.
* ⚙️ **Configurazione YAML + Pydantic** — Sistema di configurazione robusto, tipizzato, commentato e human-readable.
* 📊 **Token Payload Inspector** — Metriche aggiornate in tempo reale per monitorare i byte esatti consumati in contesto per ciascun singolo Plugin, perfetto per ottimizzare i token.
* 🖥️ **Supporto Nativo Multi-OS** — Architettura profonda OS-agnostic tramite `OSAdapter` (Supporto completo per Windows, Linux e MacOS).
* 🌐 **I18N Globale (Multilingua)** — Supporto completo per Inglese (default) e Italiano tra Terminale e WebUI con switch in tempo reale.
* 🧠 **Streaming Multi-Cloud** — Supporto nativo per Groq, OpenAI, Gemini e Anthropic con effetto "macchina da scrivere".
* 🔄 **Live-Sync Config** — Modifica qualsiasi impostazione nel Pannello Web e vedila applicata istantaneamente al core senza riavvii.
* 🎭 **Sincronizzazione Personalità** — Le personalità aggiunte alla cartella `personality/` vengono rilevate automaticamente e sincronizzate con `config.yaml`.
* 🎙️ **Chat Vocale Integrata** — Interfaccia Chat nativa con integrazione Piper TTS e riproduzione audio automatica.
* 🧩 **Sidebar Plugin Dinamica** — Sidebar semplificata che recupera i metadati dal core centralizzato, fornendo macro di azione rapida con icone coerenti.
* 🗑️ **Wipe Totale Cronologia** — Eliminazione massiva di tutte le sessioni di chat con un solo click direttamente dalla WebUI.
* 💾 **Memoria Persistente** — Memoria SQLite con contesto condiviso tra WebUI e Terminale.
* 👥 **Multi-User & Profile Management** — Supporto completo per account multipli con memorie isolate. Ogni utente ha il proprio profilo personale, avatar personalizzato e "Bio Note" private (memorie contestuali) che l'IA usa per identificarti.
* 💾 **Vault Isolati per Utente** — File personali, avatar e memorie sono archiviati in "Vault" sicuri e separati (`memory/vaults/username`), garantendo la massima privacy in ambienti condivisi.
* 🗂️ **Zentra Drive (File Manager)** — File manager HTTP nativo integrato nella WebUI per caricare, scaricare e organizzare i file di sistema attraverso una comoda interfaccia a doppio pannello.
* 🚀 **Launcher Professionali in Inglese** — Tutti gli script di avvio (`.bat` e `.sh`) sono ora completamente internazionalizzati in inglese, fornendo istruzioni chiare per utenti Windows e Linux.
* ⚡ **Architettura Lazy Loading (Dormant Plugins)** — I plugin ora vengono caricati "al volo" solo quando richiesti dall'IA. Questo azzera l'impatto sul tempo di avvio e riduce drasticamente l'occupazione di memoria RAM/VRAM per i moduli non utilizzati.
* 📸 **Remote Client Camera (Snap dal Telefono)** — Zentra può ora richiedere uno scatto direttamente dal tuo smartphone o browser. Grazie a un sistema di eventi SSE dedicato, appare un pulsante "Tap to Capture" sulla WebUI che sblocca la fotocamera del dispositivo remoto per un upload istantaneo nella chat.
* 🔑 **Advanced Multi-Key Manager (Failover)** — Gestione di pool di chiavi API illimitate con rotazione automatica. Supporto per il caricamento da `.env` con descrizioni in-line e failover intelligente in caso di errori Quota o Invalid Key.

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

## 🧠 Backend AI Supportati

### 🔹 Ollama
Facile da usare, veloce e ottimizzato. Consigliato per la maggior parte degli utenti.

👉 https://ollama.com

### 🔹 KoboldCpp
Supporta modelli GGUF, può eseguire modelli non censurati, più flessibile.

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