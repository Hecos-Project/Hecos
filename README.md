# 🌌 Zentra Core Project
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Zentra Logo">
</p>

# Zentra Core - Version 0.9.6 (Active Development)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Your Personal Offline AI Assistant (Private, Modular, Powerful)**

---

## 🚀 Overview
**Zentra Core** is a local-first AI assistant platform that runs entirely on your machine.
It combines local LLMs, voice interaction, system automation, and a modular plugin architecture to create a fully customizable AI companion.

Unlike cloud-based assistants, Zentra gives you full control:
* **No data collection**
* **No external dependencies** (optional)
* **No restrictions on behavior** (depending on models used)

Now powered by **LiteLLM**, Zentra supports not only Ollama and KoboldCpp but also major cloud providers (OpenAI, Anthropic, Gemini, Groq) for maximum flexibility.

---

## ✨ Key Features
* 🧠 **Local & Cloud AI Processing** — Supports Ollama, KoboldCpp, and LiteLLM (OpenAI, Groq, etc.).
* 🔄 **Multi-Backend Support** — Seamlessly switch between local and cloud models.
* 🎙️ **Multilingual Voice Interaction** — Dynamic TTS/STT with automatic language selection (EN/IT).
* ⚙️ **System Control** — Execute commands, open apps, manage files.
* 🔌 **Plugin System** — Easily extend functionality.
* 💾 **Persistent Memory** — SQLite-based long-term memory.
* 🖥️ **Advanced Telemetry** — Hardware monitoring (CPU, RAM, GPU) and improved logging.
* 🔗 **Integration Ready** — Works with Open WebUI and Home Assistant.

---

## 🧠 How It Works
Zentra Core is built around a modular architecture:
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
git clone https://github.com/Zentra-Core/zentra-core.github.io.git
cd zentra-core.github.io
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Zentra
```bash
python main.py
```

---

## 🧠 Supported AI Backends

### 🔹 Ollama
Easy to use, fast and optimized. Recommended for most users.

👉 https://ollama.com

### 🔹 KoboldCpp
Supports GGUF models, can run uncensored models, more flexible.

---

## 🔌 Plugin System
Zentra uses a dynamic plugin architecture. Each plugin can register commands, execute system actions, and extend AI capabilities.

Included plugins:
* **System control & File manager**
* **Web automation & Hardware dashboard**
* **Media control & Model switching**
* **Memory management**

---

## 💾 Memory & Voice Systems

### 🗄️ Memory System
Zentra includes a persistent memory layer powered by SQLite for lightweight local storage. It stores conversations, maintains identity, and saves user preferences.

### 🎙️ Voice System
* **Speech-to-text input**
* **Text-to-speech output**
* **Real-time interaction**

---

## 🔗 Integrations & Privacy

### 🤝 Integrations
Zentra can integrate with:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (via bridge)

### 🔐 Privacy First
Zentra is designed with privacy in mind: Runs 100% locally, no mandatory cloud services, and full control over data.

---

## 🛣️ Roadmap
- [ ] 📱 Telegram integration (remote control)
- [ ] 🧠 Advanced memory system
- [ ] 🤖 Multi-agent architecture
- [ ] 🛒 Plugin marketplace
- [ ] 🎨 Improved UI/UX

---

## ⚠️ Disclaimer
Zentra can execute system-level commands and control your environment. Use responsibly. The author is not responsible for misuse or damage.

---

## 📜 License
MIT License (initial release)

---

## 👥 Credits & Contact
Lead Developer: Antonio Meloni (Tony)
Official Email: zentra.core.systems@gmail.com

---

## 💡 Vision
Zentra Core aims to become a fully autonomous, local AI assistant platform — a private, extensible alternative to cloud-based AI systems.