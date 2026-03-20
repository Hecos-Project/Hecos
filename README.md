# Aura Core Project
![Aura Logo](assets/Aura_Core_Project_001.jpg)

# Aura Core - Version 0.9.4 (In Development)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Aura Core

**Your Personal Offline AI Assistant (Private, Modular, Powerful)**

---

## 🚀 Overview

**Aura Core** is a local-first AI assistant platform that runs entirely on your machine.

It combines local LLMs, voice interaction, system automation, and a modular plugin architecture to create a fully customizable AI companion.

Unlike cloud-based assistants, Aura gives you full control:

* No data collection
* No external dependencies (optional)
* No restrictions on behavior (depending on models used)

---

## ✨ Key Features

* 🧠 **Local AI Processing** — Runs entirely on your hardware
* 🔄 **Dual Backend Support** — Compatible with Ollama and KoboldCpp
* 🎙️ **Voice Interaction** — Speech input and output (TTS/STT)
* ⚙️ **System Control** — Execute commands, open apps, manage files
* 🔌 **Plugin System** — Easily extend functionality
* 💾 **Persistent Memory** — SQLite-based long-term memory
* 🌐 **Web Interaction** — Open websites and perform searches
* 🖥️ **Hardware Monitoring** — CPU, RAM, GPU stats
* 🔗 **Integration Ready** — Works with Open WebUI and Home Assistant

---

## 🧠 How It Works

Aura Core is built around a modular architecture:

* **Core** → AI routing, processing, execution
* **Plugins** → Actions and capabilities (system, web, media, etc.)
* **Memory** → Identity and persistent storage
* **UI** → User interaction layer
* **Bridge** → External integrations and APIs

The AI generates structured commands that are interpreted and executed through the plugin system.

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/aura-core.git
cd aura-core
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Aura

```bash
python main.py
```

---

## 🧠 Supported AI Backends

### 🔹 Ollama

* Easy to use
* Fast and optimized
* Recommended for most users

👉 https://ollama.com

### 🔹 KoboldCpp

* Supports GGUF models
* Can run uncensored models
* More flexible

---

## 🔌 Plugin System

Aura uses a dynamic plugin architecture.

Each plugin can:

* Register commands
* Execute system actions
* Extend AI capabilities

### Included plugins:

* System control
* File manager
* Web automation
* Hardware dashboard
* Media control
* Model switching
* Memory management

---

## 💾 Memory System

Aura includes a persistent memory layer:

* Stores conversations
* Maintains identity
* Saves user preferences

Powered by SQLite for lightweight local storage.

---

## 🎙️ Voice System

* Speech-to-text input
* Text-to-speech output
* Real-time interaction

---

## 🔗 Integrations

Aura can integrate with:

* Open WebUI (chat + streaming)
* Home Assistant (via bridge)

---

## 🔐 Privacy First

Aura is designed with privacy in mind:

* Runs 100% locally
* No mandatory cloud services
* Full control over data

---

## 🛣️ Roadmap

* 📱 Telegram integration (remote control)
* 🧠 Advanced memory system
* 🤖 Multi-agent architecture
* 🛒 Plugin marketplace
* 🎨 Improved UI/UX

---

## ⚠️ Disclaimer

Aura can execute system-level commands and control your environment.

Use responsibly. The author is not responsible for misuse or damage.

---

## 📜 License

MIT License (initial release)

---

## 👤 Author

Antonio Meloni (Tony)

---

## 💡 Vision

Aura Core aims to become a fully autonomous, local AI assistant platform —
a private, extensible alternative to cloud-based AI systems.

---
