# 🌌 Zentra Core Project
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Zentra Logo">
</p>

# Zentra Core - Version 0.9.7 (Runtime Alpha)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Your Personal Offline AI Assistant (Private, Modular, Powerful)**

---

> [!WARNING]
> **Runtime Alpha Status**: Zentra Core is currently in an early **Alpha** stage. It is under active development and debugging. Features may change, and the system is not yet considered stable. Use with caution.

## 🚀 Overview
**Zentra Core** is a local-first AI assistant platform that runs entirely on your machine.
It combines local LLMs, voice interaction, system automation, and a modular plugin architecture to create a fully customizable AI companion.

Now fully migrated to a **stable Native Plugin architecture**, Zentra 0.9.7 offers a dedicated Web Interface (Chat + Config) and complete Internationalization. Powered by **LiteLLM**, it supports Ollama, KoboldCpp, and major cloud providers with real-time streaming and local TTS.

---

## ✨ Key Features (v0.9.7)
* 👁️ **Native Vision Support** — Multimodal AI capabilities for Gemini, OpenAI, and Ollama (LLaVA). Analyze images, photos, and screenshots directly in chat.
* 🎨 **Image Generation Support** — Generate visual content from text prompts using external AI servers (Integrated via Pollinations.ai).
* 🏗️ **Native WebUI Plugin** — Migrated from a bridge to a core plugin (`plugins/web_ui/`) for maximum performance and stability.
* 🌐 **Global I18N (Multilingual)** — Complete support for English (default) and Italian across Terminal and WebUI with real-time switching.
* 🧠 **Multi-Cloud Streaming** — Native support for Groq, OpenAI, Gemini, and Anthropic with real-time "typewriter" effect.
* 🔄 **Live-Sync Config** — Change any setting in the Web Panel and see it applied instantly to the core without restarts.
* 🎙️ **Integrated Voice Chat** — Native Chat UI with Piper TTS integration and automatic audio playback.
* 🔌 **Plugin Macro Buttons** — Sidebar plugin list now features clickable macros to inject specialized commands instantly.
* 💾 **Persistent Memory** — SQLite-based long-term memory with shared context across WebUI and Terminal.
* 🚀 **Standalone Launcher** — Dedicated `run_zentra_web.bat` to start the Web server independently.

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

## 📚 Technical Documentation
Detailed technical guides for developers and advanced users:
- 🏗️ **[Technical Architecture Guide](docs/TECHNICAL_GUIDE.md)**: Deep dive into the OOP structure, data flow, and core engines.
- 🔌 **[Plugin Development Guide](docs/PLUGINS_DEV.md)**: How to create and register new tools using Native Function Calling.
- 📁 **[Project Structure Map](docs/zentra_core_structure_v0.9.7.md)**: Complete file-by-file breakdown of the repository.

---

## 💡 Vision
Zentra Core aims to become a fully autonomous, local AI assistant platform — a private, extensible alternative to cloud-based AI systems.
