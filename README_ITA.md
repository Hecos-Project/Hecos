# 🌌 Progetto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo Zentra">
</p>

# Zentra Core - Versione 0.9.6 (In Sviluppo Attivo)
Lingua: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Il tuo Assistente AI Personale Offline (Privato, Modulare, Potente)**

---

## 🚀 Panoramica
**Zentra Core** è una piattaforma di assistenza AI local-first che gira interamente sulla tua macchina.
Combina LLM locali, interazione vocale, automazione di sistema e un'architettura a plugin modulari per creare un compagno digitale completamente personalizzabile.

A differenza delle AI cloud:
* 🔒 **I tuoi dati restano sul tuo PC**
* ⚙️ **Hai il pieno controllo**
* 🧠 **Puoi scegliere modelli anche senza filtri**

Grazie all'integrazione con **LiteLLM**, Zentra ora supporta non solo Ollama e KoboldCpp, ma anche i maggiori provider cloud (OpenAI, Anthropic, Gemini, Groq) per la massima flessibilità.

---

## ✨ Caratteristiche Principali
* 🧠 **Elaborazione AI Locale & Cloud** — Supporta Ollama, KoboldCpp e LiteLLM (OpenAI, Groq, ecc.).
* 🔄 **Supporto Multi-Backend** — Passa facilmente tra modelli locali e cloud.
* 🎙️ **Interazione Vocale Multilingua** — Input/Output vocale con selezione automatica della lingua (IT/EN).
* ⚙️ **Controllo di Sistema** — Esegue comandi, apre app, gestisce file.
* 🔌 **Sistema a Plugin** — Funzionalità facilmente estensibili.
* 💾 **Memoria Persistente** — Memoria a lungo termine basata su SQLite.
* 🖥️ **Telemetria Avanzata** — Statistiche hardware (CPU, RAM, GPU) e logging migliorato.
* 🔗 **Pronto per l'Integrazione** — Funziona con Open WebUI e Home Assistant.

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

## 💡 Visione
Zentra Core mira a diventare una piattaforma di assistenza AI locale completamente autonoma: un'alternativa privata ed estensibile ai sistemi AI basati su cloud.