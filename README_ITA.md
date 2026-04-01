# 🌌 Progetto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo Zentra">
</p>

# Zentra Core - Versione 0.9.9 (Runtime Alpha)
Lingua: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Il tuo Assistente AI Personale Offline (Privato, Modulare, Potente)**

---

> [!WARNING]
> **Stato Runtime Alpha**: Zentra Core è attualmente in una fase iniziale **Alpha**. È in fase di sviluppo attivo e debugging. Le funzionalità possono cambiare e il sistema non è ancora considerato stabile. Usare con cautela.

## 🚀 Panoramica
**Zentra Core** è una piattaforma di assistenza AI local-first che gira interamente sulla tua macchina.
Combina LLM locali, interazione vocale, automazione di sistema e un'architettura a plugin modulari per creare un compagno digitale completamente personalizzabile.

Ora completamente migrato a una **architettura stabile a Plugin Nativi**, Zentra 0.9.9 offre una interfaccia Web dedicata (Chat + Config) e internazionalizzazione completa. Grazie a **LiteLLM**, supporta Ollama, KoboldCpp e i principali provider cloud con streaming in tempo reale e TTS locale.

---

## ✨ Caratteristiche Principali (v0.9.9)
* 🤖 **Agente Cognitivo Autonomo** — Zentra ora ragiona step-by-step (Chain of Thought), sceglie dinamicamente gli strumenti e risolve task complessi in autonomia.
* 🛡️ **Zentra Code Jail (Sandbox AST)** — Un ambiente di esecuzione nativo e isolato che permette all'IA di eseguire calcoli Python, algoritmi e test in totale sicurezza.
* 👁️ **Supporto Visione Nativa** — Capacità AI multimodali per Gemini, OpenAI e Ollama (LLaVA). Analizza immagini, foto e screenshot direttamente in chat.
* 🎨 **Generazione Immagini** — Genera contenuti visivi da prompt testuali tramite server IA esterni (Integrato via Pollinations.ai).
* 🏗️ **Plugin WebUI Nativo** — Migrato da un bridge a un plugin core (`plugins/web_ui/`) per massime prestazioni e stabilità.
* 🌐 **I18N Globale (Multilingua)** — Supporto completo per Inglese (default) e Italiano tra Terminale e WebUI con switch in tempo reale.
* 🧠 **Streaming Multi-Cloud** — Supporto nativo per Groq, OpenAI, Gemini e Anthropic con effetto "macchina da scrivere".
* 🔄 **Live-Sync Config** — Modifica qualsiasi impostazione nel Pannello Web e vedila applicata istantaneamente al core senza riavvii.
* 🎭 **Sincronizzazione Personalità** — Le personalità aggiunte alla cartella `personality/` vengono rilevate automaticamente e sincronizzate con `config.json`.
* 🎙️ **Chat Vocale Integrata** — Interfaccia Chat nativa con integrazione Piper TTS e riproduzione audio automatica.
* 🔌 **Pulsanti Macro Plugin** — L'elenco plugin nel sidebar ora include macro cliccabili per iniettare comandi specializzati istantaneamente.
* 💾 **Memoria Persistente** — Memoria SQLite con contesto condiviso tra WebUI e Terminale.
* 🚀 **Launcher Standalone** — File `run_zentra_web.bat` dedicato per avviare il server Web in modo indipendente.

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
Licenza MIT (rilascio iniziale)

---

## 👥 Crediti e Contatti
Sviluppatore Capo: Antonio Meloni (Tony)
Email Ufficiale: zentra.core.systems@gmail.com

---

## 📚 Documentazione Tecnica
- 🏗️ **[Guida all'Architettura](docs/TECHNICAL_GUIDE.md)**
- 🔌 **[Sviluppo Plugin](docs/PLUGINS_DEV.md)**
- 📁 **[Mappa Struttura](docs/zentra_core_structure_v0.9.9.md)**

---

## 💡 Visione
Zentra Core mira a diventare una piattaforma di assistenza AI locale completamente autonoma: un'alternativa privata ed estensibile ai sistemi AI basati su cloud.