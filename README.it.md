# 🤖 Aura Core

**Il tuo assistente AI locale (privato, modulare, potente)**

---

## 🌍 Lingue disponibili

* 🇬🇧 Inglese (principale) → vedi `README.md`
* 🇮🇹 Italiano (questo file)

---

## 🚀 Cos'è Aura Core

**Aura Core** è una piattaforma di assistente AI che gira completamente in locale sul tuo computer.

Unisce modelli linguistici (LLM), automazione di sistema, voce e un sistema a plugin per creare un assistente completamente personalizzabile.

A differenza delle AI cloud:

* 🔒 i tuoi dati restano sul tuo PC
* ⚙️ hai il pieno controllo
* 🧠 puoi scegliere modelli anche senza filtri

---

## ✨ Funzionalità principali

* 🧠 **AI locale** — tutto gira sul tuo hardware
* 🔄 **Supporto dual backend** — compatibile con Ollama e KoboldCpp
* 🎙️ **Interazione vocale** — ascolta e risponde
* ⚙️ **Controllo del sistema** — apre programmi, gestisce file, esegue comandi
* 🔌 **Sistema plugin** — estendi facilmente le funzionalità
* 💾 **Memoria persistente** — salvataggio dati e contesto (SQLite)
* 🌐 **Interazione web** — apre siti e fa ricerche
* 🖥️ **Monitor hardware** — CPU, RAM, GPU
* 🔗 **Integrazioni** — compatibile con Open WebUI e Home Assistant

---

## 🧠 Come funziona

Aura è strutturata in moduli:

* **Core** → gestione AI, logica e orchestrazione
* **Plugins** → azioni e funzionalità
* **Memoria** → identità e dati persistenti
* **UI** → interazione utente
* **Bridge** → integrazioni esterne

L’AI genera comandi strutturati che vengono interpretati ed eseguiti dai plugin.

---

## ⚡ Avvio rapido

### 1. Clona il progetto

```bash id="cl1"
git clone https://github.com/your-username/aura-core.git
cd aura-core
```

### 2. Installa le dipendenze

```bash id="cl2"
pip install -r requirements.txt
```

### 3. Avvia Aura

```bash id="cl3"
python main.py
```

---

## 🧠 Backend AI supportati

### 🔹 Ollama

* semplice da usare
* veloce
* consigliato per iniziare

👉 https://ollama.com

### 🔹 KoboldCpp

* supporto modelli GGUF
* possibilità di modelli uncensored
* più flessibile

---

## 🔌 Sistema Plugin

Aura utilizza un’architettura modulare basata su plugin.

Ogni plugin può:

* aggiungere comandi
* interagire con il sistema
* estendere le capacità dell’AI

### Plugin inclusi:

* sistema (comandi OS)
* file manager
* web
* dashboard hardware
* media
* gestione modelli
* memoria

---

## 💾 Sistema di memoria

Aura include una memoria persistente:

* salva conversazioni
* mantiene identità
* ricorda preferenze utente

Basata su SQLite per leggerezza e semplicità.

---

## 🎙️ Sistema vocale

* input vocale (microfono)
* output vocale (sintesi)
* interazione in tempo reale

---

## 🔗 Integrazioni

Aura può essere collegata a:

* Open WebUI
* Home Assistant

---

## 🔐 Privacy

Aura è progettata per essere **privacy-first**:

* nessun invio dati obbligatorio
* nessun cloud necessario
* controllo totale dell’utente

---

## 🛣️ Roadmap

* 📱 integrazione Telegram (controllo remoto)
* 🧠 memoria avanzata
* 🤖 sistema multi-agente
* 🛒 marketplace plugin
* 🎨 miglioramenti UI

---

## ⚠️ Avvertenze

Aura può eseguire comandi a livello di sistema.

Usala con responsabilità. L’autore non è responsabile per eventuali danni o utilizzi impropri.

---

## 📜 Licenza

MIT (versione iniziale)

---

## 👤 Autore

Antonio Meloni (Tony)

---

## 💡 Visione

Aura Core punta a diventare una piattaforma completa per assistenti AI locali:

un’alternativa privata, modulare e potente alle AI cloud.

---
